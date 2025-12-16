"""High level Retrieval-Augmented Generation orchestration."""
from __future__ import annotations

import json
import logging
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Sequence
from urllib import error, request

from dotenv import find_dotenv, load_dotenv
from sqlalchemy import or_, select
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

RAG_CHAT_TIMEOUT = int(
    os.getenv("RAG_CHAT_TIMEOUT", os.getenv("RAG_OLLAMA_TIMEOUT", "60"))
)
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

# 参考文献：每个 title 最多扫描多少行（防止某个 title 命中太多行）
RAG_REFERENCE_ROWS_PER_TITLE = int(os.getenv("RAG_REFERENCE_ROWS_PER_TITLE", "20"))
"""Row scan limit per title when building reference URLs from DB."""

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
    """根据当前问题 + 近期会话历史，构造用于向量检索的查询文本（不调用云端）。"""
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


# === B：构造最终上下文时，做 per-chunk 与 total 截断，并返回 used_chunks ===
@dataclass(frozen=True)
class ContextBuildResult:
    text: str
    used_chunks: list[Chunk]


def build_context(
    chunks: list[Chunk],
    *,
    per_chunk_char_limit: int = RAG_CHUNK_CHAR_LIMIT,
    max_total_chars: int = RAG_CONTEXT_MAX_CHARS,
    max_chunks: int = RAG_CONTEXT_MAX_CHUNKS,
) -> ContextBuildResult:
    """把检索到的 chunk 拼成给 LLM 的上下文，只保留正文内容，并控制体积。
    同时返回“实际被放进 context 的 chunks”，用于后续严格生成参考文献。
    """
    if not chunks:
        return ContextBuildResult(text="", used_chunks=[])

    contents: list[str] = []
    used_chunks: list[Chunk] = []
    total = 0

    for chunk in chunks:
        if max_chunks and len(used_chunks) >= max_chunks:
            break

        text = (chunk.content or "").strip()
        if not text:
            continue

        if per_chunk_char_limit and len(text) > per_chunk_char_limit:
            text = text[:per_chunk_char_limit].rstrip() + "…"

        projected = total + len(text) + 2
        if max_total_chars and projected > max_total_chars:
            break

        contents.append(text)
        used_chunks.append(chunk)
        total = projected

    return ContextBuildResult(text="\n\n".join(contents), used_chunks=used_chunks)


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


def _extract_chunk_title(text: str | None, chunk_id: int) -> str:
    """从 chunk 正文里提取标题，如果不存在则回退到 chunk ID。"""
    if not text:
        return f"Chunk {chunk_id}"
    head, _, _ = text.partition(":")
    title = head.strip()
    return title or f"Chunk {chunk_id}"


def build_reference_entries(chunks: Sequence[Chunk]) -> list[tuple[str, str | None]]:
    """（旧逻辑）从命中的 chunk 提取去重后的标题与可用的链接。"""
    entries: list[tuple[str, str | None]] = []
    seen_titles: set[str] = set()

    for chunk in chunks:
        title = _extract_chunk_title((chunk.content or "").strip(), chunk.id)
        if title in seen_titles:
            continue

        seen_titles.add(title)
        url = _extract_first_url(chunk.content)
        if not url and chunk.document and isinstance(chunk.document.doc_metadata, dict):
            url = _extract_first_url(chunk.document.doc_metadata)
        entries.append((title, url))

    return entries


def format_references(entries: Sequence[tuple[str, str | None]], language: str) -> str:
    """（旧逻辑）Render references using the requested language, falling back to Chinese."""
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


# === 新参考文献逻辑：只对“实际进 context 的 chunk”做 title 去重，并从 DB 行字段抽 URL ===
def extract_title(text: str) -> str:
    """title 固定是首字段：取第一个 ':' 之前的部分。"""
    head, _, _ = (text or "").partition(":")
    return head.strip()


def _escape_like(value: str) -> str:
    """转义 LIKE 通配符，避免 title 内含 %/_ 时造成误匹配。"""
    return (value or "").replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _extract_urls_from_row(row_text: str) -> list[str]:
    """从一行 content 的字段里抽所有 URL（去重、保序）。"""
    if not row_text:
        return []
    seen: set[str] = set()
    urls: list[str] = []
    for field in row_text.split(","):
        for url in _URL_PATTERN.findall(field):
            if url in seen:
                continue
            seen.add(url)
            urls.append(url)
    return urls

def extract_title(text: str) -> str:
    """title 固定是首字段：取第一个 ':' 或 '：' 之前的部分（并去掉 BOM）。"""
    s = (text or "").lstrip("\ufeff").strip()
    if not s:
        return ""
    # 兼容英文冒号和全角冒号，取最先出现的那个
    idx_ascii = s.find(":")
    idx_full = s.find("：")
    idxs = [i for i in (idx_ascii, idx_full) if i != -1]
    if not idxs:
        return s
    idx = min(idxs)
    return s[:idx].strip()

def _title_prefix_condition(title: str):
    """构造：content 以 title 开头的匹配条件（兼容空格/全角冒号/BOM）。"""
    t = (title or "").lstrip("\ufeff").strip()
    if not t:
        return None

    esc = _escape_like(t)

    # 兼容几种常见写法：冒号前可有空格；冒号可为全角；DB 行首可能带 BOM
    patterns = [
        f"{esc}:%",
        f"{esc} :%",
        f"{esc}：%",
        f"{esc} ：%",
        f"\ufeff{esc}:%",
        f"\ufeff{esc} :%",
        f"\ufeff{esc}：%",
        f"\ufeff{esc} ：%",
    ]
    return or_(*[Chunk.content.like(p, escape="\\") for p in patterns])


def build_reference_entries_from_context(
    db: Session,
    used_chunks: Sequence[Chunk],
    *,
    domain_ids: list[int] | None = None,
    rows_per_title: int = RAG_REFERENCE_ROWS_PER_TITLE,
) -> list[tuple[str, list[str]]]:
    """
    参考文献生成（稳版）：
    - 只对“实际进 context 的 chunks”提 title，并按出现顺序去重
    - 每个 title 单独查 rows_per_title 行（避免全局 LIMIT 挤掉别人的结果）
    - 从这些行的字段里抽所有 URL（可能多个），按 title 聚合
    """
    # 1) 从 used_chunks 提取 title（按出现顺序去重）
    titles: list[str] = []
    seen: set[str] = set()
    for ch in used_chunks:
        t = extract_title((ch.content or "").strip())
        if not t or t in seen:
            continue
        seen.add(t)
        titles.append(t)

    if not titles:
        return []

    per = max(1, int(rows_per_title)) if rows_per_title else 20

    # 2) 逐 title 查，保证“每个 title 都有自己的 LIMIT 配额”
    urls_by_title: dict[str, list[str]] = {t: [] for t in titles}
    seen_url_by_title: dict[str, set[str]] = {t: set() for t in titles}

    for t in titles:
        cond = _title_prefix_condition(t)
        if cond is None:
            continue

        stmt = select(Chunk.content).where(cond)

        if domain_ids:
            stmt = stmt.join(Chunk.document).where(Document.domain_id.in_(list(domain_ids)))

        # 加 order_by，让结果稳定可复现（不然数据库返回顺序可能飘）
        stmt = stmt.order_by(Chunk.id.asc()).limit(per)

        rows = db.execute(stmt).scalars().all()

        for row_text in rows:
            # 保险：只处理 title 真的匹配的行（防止极端情况下 like 命中怪东西）
            row_title = extract_title(row_text)
            if row_title != t:
                continue

            for url in _extract_urls_from_row(row_text):
                if url in seen_url_by_title[t]:
                    continue
                seen_url_by_title[t].add(url)
                urls_by_title[t].append(url)

    return [(t, urls_by_title.get(t, [])) for t in titles]


def format_references_from_titles(
    entries: Sequence[tuple[str, list[str]]],
    language: str,
) -> str:
    """按新格式渲染：1. Title，链接：URL1（若多个 URL，下一行继续列）"""
    labels = _REFERENCE_LABELS.get(language) or _REFERENCE_LABELS[_FALLBACK_LANGUAGE]
    heading = labels.get("heading", "参考资料")
    heading_separator = labels.get("heading_separator", "：")

    lines: list[str] = []
    for idx, (title, urls) in enumerate(entries, start=1):
        if urls:
            lines.append(f"{idx}. {title}，链接：{urls[0]}")
            for u in urls[1:]:
                lines.append(f"   {u}")
        else:
            lines.append(f"{idx}. {title}")

    return f"{heading}{heading_separator}\n" + "\n".join(lines)


def chunk_to_memory_text(chunk: Chunk) -> str:
    """把单个 chunk 渲染成可持久化的“记忆”文本，只保留内容。"""
    return (chunk.content or "").strip()


def compress_chunk_memory(question: str, chunks: Sequence[Chunk]) -> str:
    """Use the chat model to compress retrieved chunks for long-term memory."""
    context = build_context(list(chunks)).text
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

    # B：上下文拼接做严格截断 + 记录 used_chunks（用于参考文献）
    ctx = build_context(list(chunks))
    context = ctx.text

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
        trimmed_user = (
            user_only[-max(0, RAG_HISTORY_MAX_USER_TURNS):]
            if RAG_HISTORY_MAX_USER_TURNS
            else []
        )
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

    # === 新参考文献拼接：仅对“实际进 context 的 chunks”做 title 去重，并从 DB 行字段抽 URL ===
    ref_entries = build_reference_entries_from_context(
        db,
        ctx.used_chunks,
        domain_ids=domain_ids,
        rows_per_title=RAG_REFERENCE_ROWS_PER_TITLE,
    )
    if ref_entries:
        reference_block = format_references_from_titles(ref_entries, _normalized_language)
        final_text = f"{final_text}\n\n{reference_block}"

    return final_text, references, chunks
