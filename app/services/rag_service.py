"""High level Retrieval-Augmented Generation orchestration."""
from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from typing import Sequence
import re
from urllib import error, request
from dotenv import find_dotenv, load_dotenv
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.entities import Chunk, Document
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

STRING_MATCH_MAX_PER_ID = int(os.getenv("RAG_STRING_MATCH_MAX_PER_ID", "20"))
"""Upper bound of chunks fetched per ID candidate during string search."""

NEIGHBOR_WINDOW_SIZE = int(os.getenv("RAG_NEIGHBOR_WINDOW_SIZE", "1"))
"""Default window size when expanding chunks with their neighbors."""

NEIGHBOR_MAX_TOTAL_CHUNKS = int(os.getenv("RAG_NEIGHBOR_MAX_TOTAL_CHUNKS", "100"))
"""Safety limit to avoid overlong contexts after neighbor expansion."""

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


def retrieve(
    question: str,
    top_k: int,
    domain_ids: list[int] | None,
    *,
    db: Session,
    history: Sequence[dict[str, str]] | None = None,
) -> list[Chunk]:
    """Retrieve the most relevant chunks for the given question.

    新增可选参数 history，用于在检索阶段利用会话上下文。
    """
    chunks, _ = retrieve_with_scores(question, top_k, domain_ids, db=db, history=history)
    return chunks


_DIGIT_RUN = re.compile(r"\d{4,}")
_ALNUM_MIXED = re.compile(r"[A-Za-z][A-Za-z0-9\-_]*\d[A-Za-z0-9\-_]{2,}")
_ERA_PREFIX = re.compile(r"(平|昭|令|民国)[^\d]{0,2}\d{1,}")


def extract_id_candidates(query: str) -> list[str]:
    """Extract ID / number-like candidates from a free-form query.

    Embedding models are notoriously weak at retaining the semantics of raw
    numbers or long identifiers. For archive-style questions such as
    "平成12年12345号档案是什么", a pure vector search often misses the exact chunk
    containing the ID. This helper pulls out likely identifiers so we can run a
    lightweight string match in parallel.
    """

    candidates: list[str] = []
    normalized = query.strip()
    for pattern in (_DIGIT_RUN, _ALNUM_MIXED, _ERA_PREFIX):
        for match in pattern.findall(normalized):
            token = match.strip()
            if len(token) < 4:  # ignore trivial short pieces like single years
                continue
            candidates.append(token)

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_candidates: list[str] = []
    for cand in candidates:
        if cand in seen:
            continue
        seen.add(cand)
        unique_candidates.append(cand)
    return unique_candidates


def search_chunks_by_id_candidates(
    db: Session,
    id_candidates: list[str],
    *,
    domain_ids: list[int] | None = None,
    limit_per_id: int = STRING_MATCH_MAX_PER_ID,
) -> list[Chunk]:
    """Perform fuzzy string search for chunks containing any of the IDs.

    For ID-heavy questions, exact string containment is often more reliable
    than embeddings. We still cap results per candidate to keep the context
    manageable.
    """

    if not id_candidates:
        return []

    matched: list[Chunk] = []
    seen_ids: set[int] = set()
    for candidate in id_candidates:
        stmt = select(Chunk).options(joinedload(Chunk.document)).where(
            Chunk.content.ilike(f"%{candidate}%")
        )
        if domain_ids:
            stmt = stmt.join(Chunk.document).where(Document.domain_id.in_(list(domain_ids)))
        if limit_per_id:
            stmt = stmt.limit(limit_per_id)
        rows = db.execute(stmt).scalars().unique().all()
        for chunk in rows:
            if chunk.id in seen_ids:
                continue
            seen_ids.add(chunk.id)
            matched.append(chunk)
    logger.info(
        "string_match candidates=%s matched_chunks=%s", len(id_candidates), len(matched)
    )
    return matched


def merge_string_and_vector_results(
    string_matches: list[Chunk],
    vector_chunks: list[Chunk],
) -> list[Chunk]:
    """Merge string and vector retrieval results with ID hits prioritized.

    Strategy: return all string matches first (ID recall is most important),
    then append remaining vector hits while keeping unique chunk IDs.
    """

    merged: list[Chunk] = []
    seen_ids: set[int] = set()
    for chunk in string_matches:
        if chunk.id in seen_ids:
            continue
        seen_ids.add(chunk.id)
        merged.append(chunk)
    for chunk in vector_chunks:
        if chunk.id in seen_ids:
            continue
        seen_ids.add(chunk.id)
        merged.append(chunk)
    return merged


def expand_with_neighbor_chunks(
    db: Session,
    chunks: list[Chunk],
    window_size: int = NEIGHBOR_WINDOW_SIZE,
    max_total_chunks: int = NEIGHBOR_MAX_TOTAL_CHUNKS,
) -> list[Chunk]:
    """Expand retrieved chunks by adding their neighbors within the same document.

    多数字段分散在多个 chunk 中，单点命中往往不足以回答跨字段问题。相比
    二次检索或多跳 RAG，直接附加同一文档的前后邻居可以立即让 LLM 看到同一
    档案的关联字段，是一种简单且工程化的折中方案。
    """

    if not chunks:
        return []

    # Always include the seed chunks
    seen_ids: set[int] = {chunk.id for chunk in chunks}
    expanded: list[Chunk] = list(chunks)

    if window_size <= 0:
        return expanded

    targets: defaultdict[int, set[int]] = defaultdict(set)
    for chunk in chunks:
        for offset in range(-window_size, window_size + 1):
            targets[chunk.document_id].add(chunk.ordinal + offset)

    for document_id, ordinals in targets.items():
        stmt = (
            select(Chunk)
            .options(joinedload(Chunk.document))
            .where(Chunk.document_id == document_id)
            .where(Chunk.ordinal.in_(ordinals))
            .order_by(Chunk.ordinal.asc())
        )
        for chunk in db.execute(stmt).scalars().unique().all():
            if chunk.id in seen_ids:
                continue
            seen_ids.add(chunk.id)
            expanded.append(chunk)

    expanded.sort(key=lambda c: (c.document_id, c.ordinal))
    if max_total_chunks and len(expanded) > max_total_chunks:
        expanded = expanded[:max_total_chunks]
    return expanded


def build_retrieval_query_text(
    question: str,
    history: Sequence[dict[str, str]] | None = None,
) -> str:
    """根据当前问题 + 近期会话历史，构造用于向量检索的查询文本。

    这样可以缓解“它 / 这个档案”之类代词导致的语义丢失问题。
    """

    if not history:
        # 没有历史，直接用当前问题
        return question.strip()

    # 只取最近几条会话，避免文本太长（这里取 4 条，可根据需要调）
    tail = list(history)[-4:]

    # 把 user / assistant 的发言简单串起来
    history_lines: list[str] = []
    for msg in tail:
        role = msg.get("role")
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        if role == "user":
            # 用前缀标记角色，帮助嵌入模型区分说话人
            history_lines.append(f"用户：{content}")
        elif role == "assistant":
            history_lines.append(f"助手：{content}")

    history_block = "\n".join(history_lines).strip()

    # 最后明确告诉嵌入模型：下面是当前问题
    if history_block:
        return f"{history_block}\n\n当前问题：{question.strip()}"
    return question.strip()


def retrieve_with_scores(
    question: str,
    top_k: int,
    domain_ids: list[int] | None,
    *,
    db: Session,
    history: Sequence[dict[str, str]] | None = None,
) -> tuple[list[Chunk], list[tuple[int, float]]]:
    """Retrieve chunks along with their similarity scores.

    新增参数 history，用于构造更完整的检索文本（包含上下文）。
    """
    limit = top_k or DEFAULT_TOP_K

    # 先根据原始问题提取可能的编号片段，用于字符串匹配检索
    id_candidates = extract_id_candidates(question)
    string_matches = search_chunks_by_id_candidates(
        db, id_candidates, domain_ids=domain_ids, limit_per_id=STRING_MATCH_MAX_PER_ID
    )

    # 利用会话历史构造检索文本，而不是只用当前问题
    query_text = build_retrieval_query_text(question, history)
    query_vec = embed(query_text)  # 将“问题 + 上下文”编码为向量

    search_results = search_with_scores(
        query_vec,
        limit,
        domain_ids=domain_ids,
    )  # 调用向量库获取候选
    chunk_ids = [chunk_id for chunk_id, _ in search_results]
    repo = ChunkRepository(db)
    fetched = repo.get_many(chunk_ids, domain_ids=domain_ids)
    chunk_map = {chunk.id: chunk for chunk in fetched}
    filtered_results = [(cid, score) for cid, score in search_results if cid in chunk_map]
    ordered_chunks = [chunk_map[cid] for cid, _ in filtered_results]

    merged_chunks = merge_string_and_vector_results(string_matches, ordered_chunks)
    expanded_chunks = expand_with_neighbor_chunks(
        db, merged_chunks, window_size=NEIGHBOR_WINDOW_SIZE, max_total_chunks=NEIGHBOR_MAX_TOTAL_CHUNKS
    )

    score_map = {cid: score for cid, score in filtered_results}
    references = [(chunk.id, score_map.get(chunk.id, 0.0)) for chunk in expanded_chunks]
    return expanded_chunks, references


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
    chunks, references = retrieve_with_scores(
        question,
        limit,
        domain_ids,
        db=db,
        history=history,
    )
    if not references:
        return _NO_CONTEXT_MESSAGE, [], []

    context = build_context(chunks)
    system_prompt = """你是一名严谨的档案解读助手，请依据给定资料回答问题。同时我们还会提供会话历史作为参考。
    规则：1.不得凭空捏造, 若缺证据请明确“不确定”；
    2.请替换问题中的代词以确保回答清晰；
    3.你只需要回答最后一个问题，不要回答会话历史中的问题。
    4.答案不要提及chunk片段。
    """
    history_items = list(history or [])
    user_system_prompts: list[str] = []
    filtered_history: list[dict[str, str]] = []
    for item in history_items:
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if role not in {"user", "assistant", "system"}:
            continue
        if not content:
            continue
        if role == "system":
            user_system_prompts.append(content)
            continue
        filtered_history.append({"role": role, "content": content})

    if user_system_prompts:
        joined_user_prompts = "\n".join(user_system_prompts)
        system_prompt = (
            f"{system_prompt}\n\n以下是用户在创建会话时提供的初始指示，请务必逐条严格遵守：\n"
            f"{joined_user_prompts}"
        )
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

        # ... 前面的 system_prompt / history 处理保持不变

    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt}
    ]

    # 先把相关档案片段作为一条 user 消息给出去
    if context:
        messages.append(
            {
                "role": "user",
                "content": (
                    "以下是与当前问题相关的档案片段，请严格基于这些内容进行回答：\n\n"
                    f"{context}"
                ),
            }
        )

    # 会话历史：可以继续附加，但建议只保留最近若干条
    trimmed_history: list[dict[str, str]] = []
    if filtered_history:
        # 例如只取最近 6 条历史记录，避免太长
        trimmed_history = filtered_history[-6:]
        messages.append(
            {
                "role": "assistant",
                "content": "下面是此前的对话记录（供你理解上下文，不需要逐条逐一回复）：",
            }
        )
        messages.extend(trimmed_history)

    # 最后一条，一定是当前用户的问题
    messages.append(
        {
            "role": "user",
            "content": f"请根据上面的档案片段和对话历史，回答这个问题：\n\n{question}",
        }
    )


    answer_text = chat(messages)
    final_text = answer_text.strip() if answer_text else ""
    if not final_text:
        final_text = _NO_CONTEXT_MESSAGE
    return final_text, references, chunks
