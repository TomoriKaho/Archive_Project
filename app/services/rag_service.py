"""High level Retrieval-Augmented Generation orchestration."""
from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from functools import lru_cache
from typing import Any, Sequence
import re
from urllib import error, request

from dotenv import find_dotenv, load_dotenv
from sqlalchemy import select, or_
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

CHAT_API_URL = os.getenv(
    "CHAT_API_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
)
"""Base URL of the cloud chat completion endpoint (OpenAI-compatible)."""

CHAT_API_KEY = os.getenv("CHAT_API_KEY", "")
"""API key used to authenticate against the cloud chat provider."""

CHAT_MODEL = os.getenv("CHAT_MODEL", "qwen3-vl-plus")
"""Chat model identifier when querying the cloud provider."""

DEFAULT_TOP_K = int(os.getenv("RAG_TOP_K", "10"))
"""Default number of chunks retrieved when no explicit top_k is provided."""

# 注意：你给的变量名里没带 RAG_ 前缀；这里仍以代码实际读取的 env 为准。
STRING_MATCH_MAX_PER_ID = int(os.getenv("RAG_STRING_MATCH_MAX_PER_ID", "10"))
"""Upper bound of chunks fetched per ID candidate during string search."""

# 合并 OR 查询后，会对 candidate 数量做硬上限，避免 OR 过大导致 DB 计划变差
STRING_MATCH_MAX_CANDIDATES = int(os.getenv("RAG_STRING_MATCH_MAX_CANDIDATES", "6"))
"""Max number of ID/URL candidates used in DB string match per request."""

NEIGHBOR_WINDOW_SIZE = int(os.getenv("RAG_NEIGHBOR_WINDOW_SIZE", "1"))
"""Default window size when expanding chunks with their neighbors."""

NEIGHBOR_MAX_TOTAL_CHUNKS = int(os.getenv("RAG_NEIGHBOR_MAX_TOTAL_CHUNKS", "100"))
"""Safety limit to avoid overlong contexts after neighbor expansion."""

RAG_CHAT_TIMEOUT = int(os.getenv("RAG_CHAT_TIMEOUT", os.getenv("RAG_OLLAMA_TIMEOUT", "60")))
"""HTTP timeout applied to chat requests."""

CHUNK_MEMORY_WINDOW_MULTIPLIER = int(os.getenv("RAG_CHUNK_MEMORY_WINDOW_MULTIPLIER", "3"))
"""Number of historical chunk batches kept in memory, expressed as a multiplier of top_k."""

# === B：上下文体积控制（强烈建议开启） ===
RAG_CHUNK_CHAR_LIMIT = int(os.getenv("RAG_CHUNK_CHAR_LIMIT", "1200"))
"""Max chars kept per chunk when building final LLM context."""

RAG_CONTEXT_MAX_CHARS = int(os.getenv("RAG_CONTEXT_MAX_CHARS", "12000"))
"""Max total chars for all chunks combined in final LLM context."""

RAG_CONTEXT_MAX_CHUNKS = int(os.getenv("RAG_CONTEXT_MAX_CHUNKS", "40"))
"""Hard cap on number of chunks included in final LLM context (after expansion)."""

RAG_HISTORY_MAX_USER_TURNS = int(os.getenv("RAG_HISTORY_MAX_USER_TURNS", "3"))
"""Only keep last N user turns for final answer prompt (reduce token bloat)."""

_FALLBACK_LANGUAGE = "zh"
_PROMPT_TEMPLATES = {
    "zh": {
        "system": (
            "你是一名严谨的档案解读助手，请像一位档案馆工作人员一样，用自然的中文回答用户的问题。\n\n"
            "规则：\n"
            "1. 严格依据检索到的档案资料与对话内容作答，不得凭空捏造；\n"
            "2. 回答时不要说明资料是如何获得的，例如不要使用\n"
            "“根据提供的档案片段”“根据以上资料”“档案中提到”等表述，\n"
            "只需直接陈述档案记载的事实即可；\n"
            "3. 你只需要回答最后一个问题，不要重新回答会话历史中的旧问题；\n"
            "4. 在必要的位置添加换行以提升可读性；\n"
            "5. 当前界面语言为中文，请始终使用中文回答问题。"
        ),
        "context_intro": "以下是与当前问题相关的档案片段，请严格基于这些内容进行回答：\n\n{context}",
        "user_instruction_intro": "以下是用户在创建会话时提供的初始指示，请务必逐条严格遵守：\n{instructions}",
        "memory_intro": "下面是若干档案内容的节选，请在回答问题时仅以这些内容为依据：\n\n{memory}",
        "no_context": "当前知识库中没有足够的信息回答该问题。",
    },
    "en": {
        "system": (
            "You are a meticulous archive assistant. Answer like an archive staff member in natural English.\n\n"
            "Rules:\n"
            "1. Base your reply strictly on the retrieved archive snippets and dialog content; never fabricate information.\n"
            "2. Do not mention how the information was obtained—avoid phrases like \"according to the provided snippets\" or \"the archive says\";\n"
            "   simply state the facts.\n"
            "3. Only answer the latest question; do not revisit earlier ones in the conversation.\n"
            "4. Insert line breaks when helpful for readability.\n"
            "5. The UI language is English; always reply in English."
        ),
        "context_intro": "Here are the archive snippets relevant to the question. Base your answer strictly on them:\n\n{context}",
        "user_instruction_intro": "Initial user instructions for this chat—follow each item strictly:\n{instructions}",
        "memory_intro": "Below are excerpts from archive content. Use only these passages when answering:\n\n{memory}",
        "no_context": "There is not enough information in the knowledge base to answer this question.",
    },
}

_REFERENCE_LABELS = {
    "zh": {"heading": "参考资料", "heading_separator": "：", "url_separator": "："},
    "en": {"heading": "References", "heading_separator": ":", "url_separator": ": "},
}


def resolve_prompt_template(language: str | None) -> tuple[str, dict[str, str]]:
    """Return the normalized language and prompt template with fallback."""
    normalized = normalize_language_code(language)
    template = _PROMPT_TEMPLATES.get(normalized or _FALLBACK_LANGUAGE)
    if not template:
        normalized = _FALLBACK_LANGUAGE
        template = _PROMPT_TEMPLATES[_FALLBACK_LANGUAGE]
    return normalized or _FALLBACK_LANGUAGE, template


def normalize_language_code(language: str | None) -> str | None:
    """Normalize user-provided language code to supported values."""
    if not language:
        return None
    lowered = language.strip().lower()
    if lowered.startswith("en"):
        return "en"
    if lowered.startswith("zh") or lowered.startswith("cn"):
        return "zh"
    return None


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
    if any(len(vec) != dim for vec in vectors):
        raise RuntimeError("inconsistent embedding dimensions detected")
    ensure_collection(dim)
    upsert_vectors(ids, vectors, payloads)
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
    """Retrieve the most relevant chunks for the given question."""
    chunks, _ = retrieve_with_scores(question, top_k, domain_ids, db=db, history=history)
    return chunks


_DIGIT_RUN = re.compile(r"\d{4,}")
_ALNUM_MIXED = re.compile(r"[A-Za-z][A-Za-z0-9\-_]*\d[A-Za-z0-9\-_]{2,}")
_ERA_PREFIX = re.compile(r"(平|昭|令)[^\d]{0,2}\d{1,}")
_URL_PATTERN = re.compile(r"https?://[^\s<>\u3000\"']+", re.IGNORECASE)

# 更宽松的分词：保留中日韩字符片段、字母数字片段
_WORDISH = re.compile(r"[A-Za-z0-9\-_]{2,}|[\u4e00-\u9fff]{2,}|[\u3040-\u30ff]{2,}|[\uac00-\ud7af]{2,}")


def extract_id_candidates(query: str) -> list[str]:
    """Extract ID / number-like candidates from a free-form query."""
    candidates: list[str] = []
    normalized = query.strip()
    for pattern in (_DIGIT_RUN, _ALNUM_MIXED, _ERA_PREFIX):
        for match in pattern.findall(normalized):
            token = match.strip()
            if len(token) < 4:
                continue
            candidates.append(token)

    seen: set[str] = set()
    unique_candidates: list[str] = []
    for cand in candidates:
        if cand in seen:
            continue
        seen.add(cand)
        unique_candidates.append(cand)
    return unique_candidates


def extract_strict_match_targets(query: str) -> list[str]:
    """Pull out digit runs and URLs that require exact string containment."""
    if not query:
        return []

    normalized = query.strip()
    candidates: list[str] = []

    for match in _URL_PATTERN.findall(normalized):
        token = match.strip()
        if token:
            candidates.append(token)

    for match in _DIGIT_RUN.findall(normalized):
        token = match.strip()
        if token:
            candidates.append(token)

    seen: set[str] = set()
    result: list[str] = []
    for token in candidates:
        if token in seen:
            continue
        seen.add(token)
        result.append(token)
    return result


def _dedupe_preserve_order(items: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for it in items:
        x = (it or "").strip()
        if not x or x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


# === A：检索 query 构造改为纯本地（不再调用云端 chat）===
@lru_cache(maxsize=256)
def _extract_keyword_tokens_local(text: str, *, limit: int = 24) -> tuple[str, ...]:
    """本地抽取关键词，用于向量检索 query（快、稳定、可缓存）。"""
    if not text:
        return tuple()

    normalized = text.strip()
    if not normalized:
        return tuple()

    tokens: list[str] = []
    # 强信号：URL / 长数字 / 混合编号
    tokens.extend(_URL_PATTERN.findall(normalized))
    tokens.extend(_DIGIT_RUN.findall(normalized))
    tokens.extend(_ALNUM_MIXED.findall(normalized))
    tokens.extend(_ERA_PREFIX.findall(normalized))

    # 其他“像词”的片段
    tokens.extend(_WORDISH.findall(normalized))

    # 清洗：去掉特别长的垃圾段，保留相对短、信息密度高的 token
    cleaned: list[str] = []
    for t in tokens:
        s = (t or "").strip()
        if not s:
            continue
        if len(s) > 48:
            continue
        cleaned.append(s)

    unique = _dedupe_preserve_order(cleaned)
    return tuple(unique[:limit])


def build_retrieval_query_text(
    question: str,
    history: Sequence[dict[str, str]] | None = None,
) -> str:
    """根据当前问题 + 近期会话历史，构造用于向量检索的查询文本。

    A：这里不再调用云端 chat 做关键词提取（避免检索阶段多次云端往返）。
    """
    q = (question or "").strip()
    if not q:
        return ""

    # 仅取最近若干条用户问题（不拿 assistant 长回答，避免把向量 query 搞“发胖”）
    user_tail: list[str] = []
    if history:
        for msg in reversed(history):
            if msg.get("role") != "user":
                continue
            content = (msg.get("content") or "").strip()
            if not content:
                continue
            user_tail.append(content)
            if len(user_tail) >= max(1, RAG_HISTORY_MAX_USER_TURNS):
                break
        user_tail.reverse()

    # 把历史和当前问题各自抽 token，然后拼成紧凑 query
    parts: list[str] = []
    for ut in user_tail[-RAG_HISTORY_MAX_USER_TURNS:]:
        toks = _extract_keyword_tokens_local(ut, limit=12)
        if toks:
            parts.append(" ".join(toks))

    q_toks = _extract_keyword_tokens_local(q, limit=24)
    parts.append(" ".join(q_toks) if q_toks else q)

    merged = "\n".join([p for p in parts if p.strip()]).strip()
    return merged or q


# === C：字符串匹配查询合并，减少 DB 往返 ===
def search_chunks_by_id_candidates(
    db: Session,
    id_candidates: list[str],
    *,
    domain_ids: list[int] | None = None,
    limit_per_id: int = STRING_MATCH_MAX_PER_ID,
) -> list[Chunk]:
    """Perform fuzzy string search for chunks containing any of the IDs.

    C：把“每个 candidate 一次查询”改为“少量 candidate 合并 OR 一次查询”，
       显著减少 DB 往返与扫描次数（仍建议 DB 侧加 pg_trgm 索引）。
    """

    if not id_candidates:
        return []

    # 强制去重 + 限制 candidate 数量（URL/长编号优先）
    cands = _dedupe_preserve_order(id_candidates)
    cands.sort(key=lambda s: (0 if s.startswith("http") else 1, -len(s)))
    cands = cands[: max(1, STRING_MATCH_MAX_CANDIDATES)]

    # ⚠️ 强烈建议：Postgres 启用 pg_trgm 并建立索引，否则 ILIKE '%...%' 依旧可能慢：
    #   CREATE EXTENSION IF NOT EXISTS pg_trgm;
    #   CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_chunks_content_trgm
    #     ON chunks USING GIN (content gin_trgm_ops);

    conditions = [Chunk.content.ilike(f"%{cand}%") for cand in cands]
    stmt = select(Chunk).where(or_(*conditions))

    # domain 过滤才 join Document，避免无谓 join
    if domain_ids:
        stmt = stmt.join(Chunk.document).where(Document.domain_id.in_(list(domain_ids)))

    # 近似“每个 candidate 限额”：总量上限 = limit_per_id * candidate_count
    total_limit = max(1, int(limit_per_id)) * len(cands) if limit_per_id else 50
    stmt = stmt.limit(total_limit)

    rows = db.execute(stmt).scalars().unique().all()
    logger.info("string_match cands=%s matched_chunks=%s", len(cands), len(rows))
    return rows


def merge_string_and_vector_results(
    string_matches: list[Chunk],
    vector_chunks: list[Chunk],
    *,
    limit: int | None = None,
) -> list[Chunk]:
    """Merge string and vector retrieval results with ID hits prioritized."""
    merged: list[Chunk] = []
    seen_ids: set[int] = set()
    for chunk in string_matches:
        if chunk.id in seen_ids:
            continue
        seen_ids.add(chunk.id)
        merged.append(chunk)
        if limit and len(merged) >= limit:
            return merged
    for chunk in vector_chunks:
        if chunk.id in seen_ids:
            continue
        seen_ids.add(chunk.id)
        merged.append(chunk)
        if limit and len(merged) >= limit:
            return merged
    return merged


def expand_with_neighbor_chunks(
    db: Session,
    chunks: list[Chunk],
    window_size: int = NEIGHBOR_WINDOW_SIZE,
    max_total_chunks: int = NEIGHBOR_MAX_TOTAL_CHUNKS,
    *,
    score_map: dict[int, float] | None = None,
) -> list[Chunk]:
    """Expand retrieved chunks by adding their neighbors within the same document."""
    if not chunks:
        return []

    seen_ids: set[int] = {chunk.id for chunk in chunks}
    expanded: list[Chunk] = list(chunks)

    if window_size <= 0:
        return expanded

    targets: defaultdict[int, set[int]] = defaultdict(set)
    ordinal_scores: defaultdict[int, dict[int, float]] = defaultdict(dict)
    for chunk in chunks:
        base_score = 0.0 if score_map is None else score_map.get(chunk.id, 0.0)
        for offset in range(-window_size, window_size + 1):
            ordinal = chunk.ordinal + offset
            targets[chunk.document_id].add(ordinal)
            decayed = base_score - abs(offset) * 1e-4
            stored = ordinal_scores[chunk.document_id].get(ordinal, float("-inf"))
            if decayed > stored:
                ordinal_scores[chunk.document_id][ordinal] = decayed

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
            if score_map is not None:
                candidate = ordinal_scores[document_id].get(chunk.ordinal, 0.0)
                if candidate > score_map.get(chunk.id, float("-inf")):
                    score_map[chunk.id] = candidate

    if score_map is not None:
        expanded.sort(
            key=lambda c: (
                score_map.get(c.id, 0.0),
                -(abs(c.ordinal)),
                c.document_id,
                c.id,
            ),
            reverse=True,
        )
    else:
        expanded.sort(key=lambda c: (c.document_id, c.ordinal))

    if max_total_chunks and len(expanded) > max_total_chunks:
        expanded = expanded[:max_total_chunks]
    return expanded


def retrieve_with_scores(
    question: str,
    top_k: int,
    domain_ids: list[int] | None,
    *,
    db: Session,
    history: Sequence[dict[str, str]] | None = None,
) -> tuple[list[Chunk], list[tuple[int, float]]]:
    """Retrieve chunks along with their similarity scores."""
    limit = top_k or DEFAULT_TOP_K

    # 先从原始问题提取编号/URL，用于字符串匹配
    id_candidates = extract_id_candidates(question)
    strict_targets = extract_strict_match_targets(question)

    combined_candidates: list[str] = []
    seen_candidate: set[str] = set()
    for candidate in strict_targets + id_candidates:
        if candidate in seen_candidate:
            continue
        seen_candidate.add(candidate)
        combined_candidates.append(candidate)

    string_matches = search_chunks_by_id_candidates(
        db,
        combined_candidates,
        domain_ids=domain_ids,
        limit_per_id=STRING_MATCH_MAX_PER_ID,
    )

    # A：用本地构造的 query text，而不是云端 LLM 关键词提取
    query_text = build_retrieval_query_text(question, history)
    query_vec = embed(query_text)

    search_results = search_with_scores(
        query_vec,
        limit,
        domain_ids=domain_ids,
    )
    chunk_ids = [chunk_id for chunk_id, _ in search_results]

    repo = ChunkRepository(db)
    fetched = repo.get_many(chunk_ids, domain_ids=domain_ids)
    chunk_map = {chunk.id: chunk for chunk in fetched}
    filtered_results = [(cid, score) for cid, score in search_results if cid in chunk_map]
    ordered_chunks = [chunk_map[cid] for cid, _ in filtered_results]

    merged_chunks = merge_string_and_vector_results(
        string_matches, ordered_chunks, limit=limit
    )

    score_map: dict[int, float] = {cid: score for cid, score in filtered_results}
    if merged_chunks:
        max_score = max(score_map.values(), default=0.0)
        string_score = max_score + 1.0 if string_matches else max_score
        for chunk in string_matches:
            score_map[chunk.id] = max(score_map.get(chunk.id, 0.0), string_score)

    # B：邻居扩展不再被 top_k 砍回去，使用 NEIGHBOR_MAX_TOTAL_CHUNKS 做上限
    expanded_chunks = expand_with_neighbor_chunks(
        db,
        merged_chunks,
        window_size=NEIGHBOR_WINDOW_SIZE,
        max_total_chunks=NEIGHBOR_MAX_TOTAL_CHUNKS,
        score_map=score_map,
    )

    references = [(chunk.id, score_map.get(chunk.id, 0.0)) for chunk in expanded_chunks]
    return expanded_chunks, references


# === B：构造最终上下文时，做 per-chunk 与 total 截断 ===
def build_context(
    chunks: list[Chunk],
    *,
    per_chunk_char_limit: int = RAG_CHUNK_CHAR_LIMIT,
    max_total_chars: int = RAG_CONTEXT_MAX_CHARS,
    max_chunks: int = RAG_CONTEXT_MAX_CHUNKS,
) -> str:
    """把检索到的 chunk 拼成给 LLM 的上下文，只保留正文内容，并控制体积。"""
    if not chunks:
        return ""

    contents: list[str] = []
    total = 0
    used = 0

    for chunk in chunks:
        if max_chunks and used >= max_chunks:
            break

        text = (chunk.content or "").strip()
        if not text:
            continue

        if per_chunk_char_limit and len(text) > per_chunk_char_limit:
            text = text[:per_chunk_char_limit].rstrip() + "…"

        # +2 for separators/newlines safety
        projected = total + len(text) + 2
        if max_total_chars and projected > max_total_chars:
            break

        contents.append(text)
        total = projected
        used += 1

    return "\n\n".join(contents)


def _extract_first_url(value: Any) -> str | None:
    """在任意层级的元数据中寻找首个 URL。"""
    if isinstance(value, str):
        match = _URL_PATTERN.search(value)
        return match.group(0) if match else None

    if isinstance(value, dict):
        for candidate in value.values():
            url = _extract_first_url(candidate)
            if url:
                return url
    elif isinstance(value, (list, tuple, set)):
        for candidate in value:
            url = _extract_first_url(candidate)
            if url:
                return url
    return None


def build_reference_entries(chunks: Sequence[Chunk]) -> list[tuple[str, str | None]]:
    """从命中的 chunk 提取文档标题与可用的链接。"""
    entries: list[tuple[str, str | None]] = []
    seen_documents: set[int] = set()

    for chunk in chunks:
        if not chunk.document or chunk.document_id in seen_documents:
            continue

        seen_documents.add(chunk.document_id)
        title = (chunk.document.title or "").strip() or f"Document {chunk.document_id}"
        metadata = chunk.document.doc_metadata if isinstance(chunk.document.doc_metadata, dict) else {}
        url = _extract_first_url(metadata)
        entries.append((title, url))

    return entries


def format_references(entries: Sequence[tuple[str, str | None]], language: str) -> str:
    """Render references using the requested language, falling back to Chinese."""
    labels = _REFERENCE_LABELS.get(language) or _REFERENCE_LABELS[_FALLBACK_LANGUAGE]
    heading = labels.get("heading", "参考资料")
    heading_separator = labels.get("heading_separator", "：")
    url_separator = labels.get("url_separator", "：")

    lines: list[str] = []
    for index, (title, url) in enumerate(entries, start=1):
        if url:
            lines.append(f"{index}. {title}{url_separator}{url}")
        else:
            lines.append(f"{index}. {title}")

    return f"{heading}{heading_separator}\n" + "\n".join(lines)


def chunk_to_memory_text(chunk: Chunk) -> str:
    """把单个 chunk 渲染成可持久化的“记忆”文本，只保留内容。"""
    return (chunk.content or "").strip()


def compress_chunk_memory(question: str, chunks: Sequence[Chunk]) -> str:
    """Use the chat model to compress retrieved chunks for long-term memory."""
    context = build_context(list(chunks))
    if not context:
        return ""
    prompt = (
        "请把下面与问题相关的档案片段压缩成简洁摘要，保留数字、编号和URL等关键信息，"
        "便于后续多轮对话快速回顾："
    )
    messages = [
        {"role": "system", "content": prompt},
        {
            "role": "user",
            "content": f"问题：{question}\n\n相关片段：\n{context}",
        },
    ]
    try:
        summary = chat(messages)
    except RuntimeError:
        logger.warning("failed to compress chunk memory, fallback to raw context")
        return context[:2000]
    return summary.strip()


def chat(messages: Sequence[dict[str, str]], stream: bool = False) -> str:
    """Call the cloud chat API (OpenAI-compatible) and return the assistant reply."""
    if stream:
        raise RuntimeError("streaming chat is not supported by the current cloud backend")
    if not CHAT_API_KEY:
        raise RuntimeError("CHAT_API_KEY is required to call the cloud chat API")

    payload = {
        "model": CHAT_MODEL,
        "messages": list(messages),
    }
    req = request.Request(
        url=f"{CHAT_API_URL.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {CHAT_API_KEY}",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=RAG_CHAT_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", "ignore")
        logger.error("Cloud chat 请求失败: %s", body)
        raise RuntimeError("failed to call cloud chat API") from exc
    except error.URLError as exc:
        logger.error("无法连接到云端聊天服务: %s", exc)
        raise RuntimeError("failed to reach cloud chat API") from exc

    data = json.loads(raw) if raw else {}
    choices = data.get("choices") if isinstance(data, dict) else None
    if isinstance(choices, list) and choices:
        message = choices[0].get("message") if isinstance(choices[0], dict) else {}
        content = message.get("content") if isinstance(message, dict) else ""
        return content.strip() if content else ""
    logger.error("Unexpected cloud chat response: %s", data)
    return ""


def compress_dialog_history(history: Sequence[dict[str, str]]) -> str:
    """Compress multi-turn chat history so it can be stored compactly per chat."""
    if not history:
        return ""

    normalized: list[str] = []
    for item in history:
        role = item.get("role")
        content = (item.get("content") or "").strip()
        if not content or role not in {"user", "assistant", "system"}:
            continue
        prefix = {"user": "用户", "assistant": "助手", "system": "系统"}.get(role, role)
        normalized.append(f"{prefix}：{content}")

    if not normalized:
        return ""

    system_prompt = (
        "请将以下对话内容压缩成简洁摘要，突出关键信息、意图和约束，"
        "保留数字/编号/URL等细节，便于后续多轮对话继续。"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "\n".join(normalized)},
    ]
    try:
        summary = chat(messages)
    except RuntimeError:
        logger.warning("failed to compress dialog history")
        return ""
    return summary.strip()


def answer(
    question: str,
    domain_ids: list[int] | None,
    *,
    db: Session,
    top_k: int | None = None,
    history: Sequence[dict[str, str]] | None = None,
    memory_chunks: Sequence[str] | None = None,
    preferred_language: str | None = None,
) -> tuple[str, list[tuple[int, float]], list[Chunk]]:
    """Run the complete RAG flow and return assistant answer plus references and chunks."""

    _normalized_language, prompt_template = resolve_prompt_template(preferred_language)
    limit = top_k or DEFAULT_TOP_K

    chunks, references = retrieve_with_scores(
        question,
        limit,
        domain_ids,
        db=db,
        history=history,
    )
    if not references:
        return prompt_template["no_context"], [], []

    # B：上下文拼接做严格截断
    context = build_context(list(chunks))

    system_prompt = prompt_template["system"]

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
            f"{system_prompt}\n\n"
            f"{prompt_template['user_instruction_intro'].format(instructions=joined_user_prompts)}"
        )

    if memory_chunks:
        window = CHUNK_MEMORY_WINDOW_MULTIPLIER * limit if CHUNK_MEMORY_WINDOW_MULTIPLIER > 0 else 0
        selected_memory = list(memory_chunks)
        if window:
            selected_memory = selected_memory[-window:]
        if selected_memory:
            joined_memory = "\n\n".join(selected_memory)
            system_prompt = (
                f"{system_prompt}\n\n"
                f"{prompt_template['memory_intro'].format(memory=joined_memory)}"
            )

    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]

    if context:
        messages.append(
            {"role": "user", "content": prompt_template["context_intro"].format(context=context)}
        )

    # B：最终回答阶段 history 只保留最近 N 条用户提问，避免把 assistant 长回答塞进去拖慢
    if filtered_history:
        user_only = [m for m in filtered_history if m.get("role") == "user"]
        trimmed_user = user_only[-max(0, RAG_HISTORY_MAX_USER_TURNS):] if RAG_HISTORY_MAX_USER_TURNS else []
        if trimmed_user:
            messages.append(
                {"role": "assistant", "content": "下面是此前用户的提问（仅用于理解上下文，不需要逐条回复）："}
            )
            messages.extend(trimmed_user)

    messages.append(
        {
            "role": "user",
            "content": (
                "请阅读上面的档案资料和对话记录，直接用自然语言回答下面这个问题，\n\n"
                f"{question}"
            ),
        }
    )

    answer_text = chat(messages)
    final_text = answer_text.strip() if answer_text else ""
    if not final_text:
        final_text = prompt_template["no_context"]

    reference_entries = build_reference_entries(chunks)
    if reference_entries:
        reference_block = format_references(reference_entries, _normalized_language)
        final_text = f"{final_text}\n\n{reference_block}"

    return final_text, references, chunks
