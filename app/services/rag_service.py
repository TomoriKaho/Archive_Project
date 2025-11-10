"""High level Retrieval-Augmented Generation orchestration."""
from __future__ import annotations

import json
import logging
import os
from typing import Sequence
from urllib import error, request
from dotenv import find_dotenv, load_dotenv
from sqlalchemy.orm import Session

from app.models.entities import Chunk
from app.repositories.chunk_repo import ChunkRepository
from .embed_service import embed
from .qdrant_service import (
    delete_vectors,
    ensure_collection,
    search_with_scores,
    upsert_vectors,
)
load_dotenv(find_dotenv(), override=False)

logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
"""Base URL of the Ollama service used for chat completion."""

OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "llama3.1:8b")
"""Chat model identifier when querying Ollama."""

DEFAULT_TOP_K = int(os.getenv("RAG_TOP_K", "10"))
"""Default number of chunks retrieved when no explicit top_k is provided."""

RAG_OLLAMA_TIMEOUT = int(os.getenv("RAG_OLLAMA_TIMEOUT", "60"))
"""HTTP timeout applied to Ollama chat requests."""

CHUNK_MEMORY_WINDOW_MULTIPLIER = int(os.getenv("RAG_CHUNK_MEMORY_WINDOW_MULTIPLIER", "3"))
"""Number of historical chunk batches kept in memory, expressed as a multiplier of top_k."""

_NO_CONTEXT_MESSAGE = "当前知识库中没有足够的信息回答该问题。"


def index_chunks(chunks: Sequence[Chunk]) -> int:
    """Embed and persist chunk vectors into Qdrant, returning indexed count."""

    vectors: list[list[float]] = []
    ids: list[int] = []
    payloads: list[dict[str, int]] = []
    for chunk in chunks:
        vector = embed(chunk.content)  # 调用 Ollama 生成向量
        if not vector:
            continue
        vectors.append(vector)
        ids.append(chunk.id)
        payload: dict[str, int] = {"document_id": chunk.document_id}
        if chunk.document and chunk.document.domain_id is not None:
            payload["domain_id"] = chunk.document.domain_id
        payloads.append(payload)
    if not ids:  # 文档可能尚未生成任何 chunk
        return 0
    dim = len(vectors[0])
    if any(len(vec) != dim for vec in vectors):  # 基本防御式校验，避免写入尺寸不一致的数据
        raise RuntimeError("inconsistent embedding dimensions detected")
    ensure_collection(dim)  # 首次写入时按首个向量推断维度
    upsert_vectors(ids, vectors, payloads)  # 使用 chunk.id 作为向量库主键
    return len(ids)


def remove_vectors(chunk_ids: Sequence[int]) -> int:
    """Remove chunk vectors from Qdrant and return the number of deleted items."""

    if not chunk_ids:
        return 0
    unique_ids = [int(chunk_id) for chunk_id in dict.fromkeys(chunk_ids)]
    delete_vectors(unique_ids)
    return len(unique_ids)


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
    search_results = search_with_scores(
        query_vec, limit, domain_ids=domain_ids
    )  # 调用向量库获取候选
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


def chunk_to_memory_text(chunk: Chunk) -> str:
    """Render a single chunk as persisted memory text."""

    domain_id = chunk.document.domain_id if chunk.document else None
    header = f"[chunk#{chunk.id} document#{chunk.document_id} domain#{domain_id}]"
    return f"{header}\n{chunk.content}"


def chat(messages: Sequence[dict[str, str]], stream: bool = False) -> str:
    """Call Ollama's chat API and return the assistant message content."""

    payload = {
        "model": OLLAMA_CHAT_MODEL,
        "messages": list(messages),
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
    history: Sequence[dict[str, str]] | None = None,
    memory_chunks: Sequence[str] | None = None,
) -> tuple[str, list[tuple[int, float]], list[Chunk]]:
    """Run the complete RAG flow and return assistant answer plus references and chunks."""

    limit = top_k or DEFAULT_TOP_K
    chunks, references = retrieve_with_scores(question, limit, domain_ids, db=db)
    if not references:
        return _NO_CONTEXT_MESSAGE, [], []

    context = build_context(chunks)
    system_prompt = """你是一名严谨的档案解读助手，请依据给定资料回答问题。同时我们还会提供会话历史作为参考。
    规则：1.不得凭空捏造, 若缺证据请明确“不确定”；
         2.回答时根据用户问题的语言来使用对应的语言回答；
         3.你只需要回答最后一个问题，不要回答会话历史中的问题。"""
    if memory_chunks:
        window = CHUNK_MEMORY_WINDOW_MULTIPLIER * limit if CHUNK_MEMORY_WINDOW_MULTIPLIER > 0 else 0
        selected_memory = list(memory_chunks)
        if window:
            selected_memory = selected_memory[-window:]
        if selected_memory:
            joined_memory = "\n\n".join(selected_memory)
            system_prompt = (
                f"{system_prompt}\n\n以下是先前检索到的资料片段，请仅在与当前问题相关时引用：\n\n"
                f"{joined_memory}"
            )

    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    if context:
        messages.append(
            {
                "role": "system",
                "content": f"以下是与当前问题相关的资料：\n\n{context}",
            }
        )
    
    history_items = list(history or [])
    if history_items:
        messages.append(
            {
                "role": "system",
                "content": f"以下是会话历史：\n\n",
            }
        )
        for item in history_items:
            role = item.get("role")
            content = (item.get("content") or "").strip()
            if role not in {"user", "assistant", "system"}:
                continue
            if not content:
                continue
            messages.append({"role": role, "content": content})
    if not history_items or (history_items and history_items[-1].get("role") != "user"):
        messages.append(
            {
                "role": "system",
                "content": f"以下是你需要回答的问题，请你根据问题的语言，用对应的语言回答：\n\n",
            }
        )
        messages.append({"role": "user", "content": question})

    answer_text = chat(messages)
    final_text = answer_text.strip() if answer_text else ""
    if not final_text:
        final_text = _NO_CONTEXT_MESSAGE
    return final_text, references, chunks
