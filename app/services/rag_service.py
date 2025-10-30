"""High level Retrieval-Augmented Generation orchestration."""
from __future__ import annotations

import json
import logging
import os
from typing import Sequence
from urllib import error, request

from sqlalchemy.orm import Session
from app.models.entities import Chunk
from app.repositories.chunk_repo import ChunkRepository
from .embed_service import embed
from .qdrant_service import ensure_collection, search_with_scores, upsert_vectors

logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
"""Base URL of the Ollama service used for chat completion."""

OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "llama3.1:8b")
"""Chat model identifier when querying Ollama."""

DEFAULT_TOP_K = int(os.getenv("RAG_TOP_K", "10"))
"""Default number of chunks retrieved when no explicit top_k is provided."""

RAG_OLLAMA_TIMEOUT = int(os.getenv("RAG_OLLAMA_TIMEOUT", "60"))
"""HTTP timeout applied to Ollama chat requests."""

_NO_CONTEXT_MESSAGE = "当前知识库中没有足够的信息回答该问题。"


def index_chunks(chunks: Sequence[Chunk]) -> int:
    """Embed and persist chunk vectors into Qdrant, returning indexed count."""

    vectors: list[list[float]] = []
    ids: list[int] = []
    for chunk in chunks:
        vector = embed(chunk.content)  # 调用 Ollama 生成向量
        if not vector:
            continue
        vectors.append(vector)
        ids.append(chunk.id)
    if not ids:  # 文档可能尚未生成任何 chunk
        return 0
    dim = len(vectors[0])
    if any(len(vec) != dim for vec in vectors):  # 基本防御式校验，避免写入尺寸不一致的数据
        raise RuntimeError("inconsistent embedding dimensions detected")
    ensure_collection(dim)  # 首次写入时按首个向量推断维度
    upsert_vectors(ids, vectors)  # 使用 chunk.id 作为向量库主键
    return len(ids)


def retrieve(question: str, top_k: int, domain_ids: list[int] | None, *, db: Session) -> list[Chunk]:
    """Retrieve the most relevant chunks for the given question."""

    chunks, _ = retrieve_with_scores(question, top_k, domain_ids, db=db)
    return chunks


def retrieve_with_scores(
    question: str,
    top_k: int,
    domain_ids: list[int] | None,
    *,
    db: Session,
) -> tuple[list[Chunk], list[tuple[int, float]]]:
    """Retrieve chunks along with their similarity scores."""

    limit = top_k or DEFAULT_TOP_K
    query_vec = embed(question)  # 将问题编码为向量
    search_results = search_with_scores(query_vec, limit)  # 调用向量库获取候选
    if not search_results:
        return [], []
    chunk_ids = [chunk_id for chunk_id, _ in search_results]
    repo = ChunkRepository(db)
    fetched = repo.get_many(chunk_ids, domain_ids=domain_ids)
    if not fetched:
        return [], []
    chunk_map = {chunk.id: chunk for chunk in fetched}
    filtered_results = [(cid, score) for cid, score in search_results if cid in chunk_map]
    ordered_chunks = [chunk_map[cid] for cid, _ in filtered_results]
    return ordered_chunks, filtered_results


def build_context(chunks: list[Chunk]) -> str:
    """Concatenate retrieved chunks into a single prompt context."""

    if not chunks:
        return ""
    lines: list[str] = []
    for chunk in chunks:
        domain_id = chunk.document.domain_id if chunk.document else None
        header = f"[chunk#{chunk.id} document#{chunk.document_id} domain#{domain_id}]"
        lines.append(f"{header}\n{chunk.content}")
    return "\n\n".join(lines)


def chat(system: str, user: str, stream: bool = False) -> str:
    """Call Ollama's chat API and return the assistant message content."""

    payload = {
        "model": OLLAMA_CHAT_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": stream,
    }
    req = request.Request(
        url=f"{OLLAMA_URL.rstrip('/')}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=RAG_OLLAMA_TIMEOUT) as resp:
            if stream:
                pieces: list[str] = []
                for raw_line in resp:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    message = data.get("message") if isinstance(data, dict) else {}
                    content = message.get("content") if isinstance(message, dict) else ""
                    if content:
                        pieces.append(content)
                return "".join(pieces).strip()
            raw = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", "ignore")
        logger.error("Ollama chat 请求失败: %s", body)
        raise RuntimeError("failed to call Ollama chat API") from exc
    except error.URLError as exc:
        logger.error("无法连接到 Ollama 服务: %s", exc)
        raise RuntimeError("failed to reach Ollama chat API") from exc
    data = json.loads(raw) if raw else {}
    message = data.get("message") if isinstance(data, dict) else {}
    content = message.get("content") if isinstance(message, dict) else ""
    return content.strip() if content else ""


def answer(
    question: str,
    domain_ids: list[int] | None,
    *,
    db: Session,
    top_k: int | None = None,
) -> tuple[str, list[tuple[int, float]]]:
    """Run the complete RAG flow and return assistant answer plus references."""

    limit = top_k or DEFAULT_TOP_K
    chunks, references = retrieve_with_scores(question, limit, domain_ids, db=db)
    if not references:
        return _NO_CONTEXT_MESSAGE, []
    context = build_context(chunks)
    user_prompt = (
        "请结合以下资料回答用户的问题。如果资料不足，请明确说明不知道。\n\n"
        f"资料:\n{context}\n\n问题: {question}\n答复:"
    )
    system_prompt = "你是一名严谨的档案解读助手，只依据给定资料回答问题。"
    answer_text = chat(system_prompt, user_prompt)
    final_text = answer_text.strip() if answer_text else ""
    if not final_text:
        final_text = _NO_CONTEXT_MESSAGE
    return final_text, references
