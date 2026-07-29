"""High level Retrieval-Augmented Generation orchestration."""
from __future__ import annotations

import json
import logging
import os
import re
import time
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


# -------------------------
# Env helpers
# -------------------------
def _env_str(*keys: str, default: str = "") -> str:
    for k in keys:
        v = os.getenv(k)
        if v is not None and str(v).strip() != "":
            return str(v).strip()
    return default


def _env_int(*keys: str, default: int) -> int:
    for k in keys:
        v = os.getenv(k)
        if v is None or str(v).strip() == "":
            continue
        try:
            return int(str(v).strip())
        except ValueError:
            logger.warning("Invalid int env %s=%r, fallback to default=%s", k, v, default)
            return default
    return default


def _env_bool(*keys: str, default: bool = False) -> bool:
    for k in keys:
        v = os.getenv(k)
        if v is None:
            continue
        s = str(v).strip().lower()
        if s in {"1", "true", "yes", "y", "on"}:
            return True
        if s in {"0", "false", "no", "n", "off"}:
            return False
    return default


def _ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000.0


# -------------------------
# Core configs
# -------------------------
OLLAMA_URL = _env_str("OLLAMA_URL", default="http://localhost:11434")
"""Base URL of the Ollama service used for chat completion."""

CHAT_API_URL = _env_str(
    "CHAT_API_URL",
    default="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
"""Base URL of the cloud chat completion endpoint (OpenAI-compatible)."""

CHAT_API_KEY = _env_str("CHAT_API_KEY", default="")
"""API key used to authenticate against the cloud chat provider."""

CHAT_MODEL = _env_str("CHAT_MODEL", default="qwen3-vl-plus")
"""Chat model identifier when querying the cloud provider."""

DEFAULT_TOP_K = _env_int("RAG_TOP_K", default=10)
"""Default number of chunks retrieved when no explicit top_k is provided."""

# 兼容你 .env 里没有 RAG_ 前缀的写法
STRING_MATCH_MAX_PER_ID = _env_int("RAG_STRING_MATCH_MAX_PER_ID", "STRING_MATCH_MAX_PER_ID", default=10)
"""Upper bound of chunks fetched per ID candidate during string search."""

STRING_MATCH_MAX_CANDIDATES = _env_int("RAG_STRING_MATCH_MAX_CANDIDATES", "STRING_MATCH_MAX_CANDIDATES", default=6)
"""Max number of ID/URL candidates used in DB string match per request."""

NEIGHBOR_WINDOW_SIZE = _env_int("RAG_NEIGHBOR_WINDOW_SIZE", "NEIGHBOR_WINDOW_SIZE", default=1)
"""Default window size when expanding chunks with their neighbors."""

NEIGHBOR_MAX_TOTAL_CHUNKS = _env_int("RAG_NEIGHBOR_MAX_TOTAL_CHUNKS", "NEIGHBOR_MAX_TOTAL_CHUNKS", default=100)
"""Safety limit to avoid overlong contexts after neighbor expansion."""

RAG_CHAT_TIMEOUT = _env_int("RAG_CHAT_TIMEOUT", "RAG_OLLAMA_TIMEOUT", default=60)
"""HTTP timeout applied to chat requests."""

CHUNK_MEMORY_WINDOW_MULTIPLIER = _env_int("RAG_CHUNK_MEMORY_WINDOW_MULTIPLIER", default=3)
"""Number of historical chunk batches kept in memory, expressed as a multiplier of top_k."""

# 上下文体积控制
RAG_CHUNK_CHAR_LIMIT = _env_int("RAG_CHUNK_CHAR_LIMIT", default=1200)
"""Max chars kept per chunk when building final LLM context."""

RAG_CONTEXT_MAX_CHARS = _env_int("RAG_CONTEXT_MAX_CHARS", default=12000)
"""Max total chars for all chunks combined in final LLM context."""

RAG_CONTEXT_MAX_CHUNKS = _env_int("RAG_CONTEXT_MAX_CHUNKS", default=40)
"""Hard cap on number of chunks included in final LLM context (after expansion)."""

RAG_HISTORY_MAX_USER_TURNS = _env_int("RAG_HISTORY_MAX_USER_TURNS", default=3)
"""Only keep last N user turns for final answer prompt (reduce token bloat)."""

RAG_REFERENCE_ROWS_PER_TITLE = _env_int("RAG_REFERENCE_ROWS_PER_TITLE", default=20)
"""Row scan limit per title when building reference URLs from DB."""

# 新增：对照实验开关
RAG_DISABLE_STRING_MATCH = _env_bool("RAG_DISABLE_STRING_MATCH", default=False)
RAG_DISABLE_REFERENCES = _env_bool("RAG_DISABLE_REFERENCES", default=False)

# 新增：性能日志开关（默认关）
RAG_PERF_LOG = _env_bool("RAG_PERF_LOG", default=False)


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
            "5. 当前界面语言为中文，请始终使用中文回答问题；\n"
            "6. 对于涉及档案事实、时间线、机构、人物、事件关系的问题，"
            "优先给出完整结论，再补充关键细节、时间范围、相互关系以及能确认或不能确认的边界；\n"
            "7. 除非用户明确要求极简回答，事实性问题不要只用一句话作答；"
            "若资料足够，应组织成至少两到三个完整句子，必要时分段说明。"
        ),
        "context_intro": "以下是与当前问题相关的档案片段，请严格基于这些内容进行回答：\n\n{context}",
        "user_instruction_intro": "以下是用户在创建会话时提供的初始指示，请务必逐条严格遵守：\n{instructions}",
        "memory_intro": "下面是若干档案内容的节选，请在回答问题时仅以这些内容为依据：\n\n{memory}",
        "answer_output_intro": (
            "请阅读上面的档案资料和对话记录，回答下面的问题。\n"
            "你必须只输出一个 JSON 对象，不要输出 Markdown 代码块或任何额外说明。\n"
            "JSON 格式固定为：{{\"answer\": string, \"need_references\": boolean}}\n"
            "字段要求：\n"
            "1. answer：写给用户看的回答正文，不要包含“参考资料”“参考文献”等附录；\n"
            "2. need_references：只有当 answer 直接使用了档案中的具体事实、编号、日期、姓名、地点、链接，或其他需要用户追溯原始档案的信息时才为 true；\n"
            "3. 如果只是问候、寒暄、确认需求、说明能力、流程引导、泛化建议，或无需查看原始档案即可理解的回答，则必须为 false；\n"
            "4. 如果问题涉及多个时间点、机构、人物、档案条目或事件，answer 不要只罗列一句结果，"
            "应先概括结论，再补充时间范围、主体关系、差异点和重要限定条件；\n"
            "5. 如果用户的问题带有“分析”“比较”“梳理”“说明”“介绍”“为什么”“是否”等意图，"
            "answer 应体现分析性，不仅要列事实，还要说明这些事实之间的关系；\n"
            "6. 若资料只能支持有限结论，要明确说明目前只能确认到哪一层，不要过度推断；\n"
            "7. JSON 中布尔值必须使用 true 或 false。\n\n"
            "问题：\n{question}"
        ),
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
            "5. The UI language is English; always reply in English.\n"
            "6. For archive questions involving facts, timelines, institutions, people, or event relationships,"
            " give the main conclusion first, then add the key details, time span, relationships, and any limits on what can be confirmed.\n"
            "7. Unless the user explicitly wants a minimal answer, do not answer factual questions in a single short sentence;"
            " when the material is sufficient, use at least two or three complete sentences and split into paragraphs when helpful."
        ),
        "context_intro": "Here are the archive snippets relevant to the question. Base your answer strictly on them:\n\n{context}",
        "user_instruction_intro": "Initial user instructions for this chat—follow each item strictly:\n{instructions}",
        "memory_intro": "Below are excerpts from archive content. Use only these passages when answering:\n\n{memory}",
        "answer_output_intro": (
            "Read the archive material and conversation above, then answer the question below.\n"
            "You must output exactly one JSON object, with no Markdown fences or extra commentary.\n"
            "Use this exact shape: {{\"answer\": string, \"need_references\": boolean}}\n"
            "Field requirements:\n"
            "1. answer: the user-facing reply only; do not include a references appendix;\n"
            "2. need_references: set to true only when the answer directly uses concrete archival facts, identifiers, dates, names, places, links, or other details that should be traceable to the source archive;\n"
            "3. If the reply is only a greeting, clarification, capability explanation, workflow guidance, or general advice that does not need source tracing, it must be false;\n"
            "4. If the question involves multiple dates, institutions, people, archive entries, or events, do not reply with a single bare result;"
            " first summarize the conclusion, then add the timeline, relationships, differences, and important limitations;\n"
            "5. If the user is asking for analysis, comparison, explanation, overview, or interpretation, the answer should be analytical rather than a raw fact list;\n"
            "6. If the material supports only a limited conclusion, state that boundary clearly instead of over-inferring;\n"
            "7. The boolean value must be true or false.\n\n"
            "Question:\n{question}"
        ),
        "no_context": "There is not enough information in the knowledge base to answer this question.",
    },
}

_REFERENCE_LABELS = {
    "zh": {
        "heading": "参考资料",
        "heading_separator": "：",
        "title_link_separator": "，",
        "link_label": "链接",
        "url_separator": "：",
    },
    "en": {
        "heading": "References",
        "heading_separator": ":",
        "title_link_separator": ", ",
        "link_label": "Link",
        "url_separator": ": ",
    },
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


def _perf(msg: str, **kv: Any) -> None:
    """Perf log helper (only when RAG_PERF_LOG=1)."""
    if not RAG_PERF_LOG:
        return
    if kv:
        logger.info("[RAG_PERF] %s | %s", msg, " ".join(f"{k}={v}" for k, v in kv.items()))
    else:
        logger.info("[RAG_PERF] %s", msg)


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


@lru_cache(maxsize=256)
def _extract_keyword_tokens_local(text: str, *, limit: int = 24) -> tuple[str, ...]:
    """本地抽取关键词，用于向量检索 query（快、稳定、可缓存）。"""
    if not text:
        return tuple()

    normalized = text.strip()
    if not normalized:
        return tuple()

    tokens: list[str] = []
    tokens.extend(_URL_PATTERN.findall(normalized))
    tokens.extend(_DIGIT_RUN.findall(normalized))
    tokens.extend(_ALNUM_MIXED.findall(normalized))
    tokens.extend(_ERA_PREFIX.findall(normalized))
    tokens.extend(_WORDISH.findall(normalized))

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

    parts: list[str] = []
    for ut in user_tail[-RAG_HISTORY_MAX_USER_TURNS:]:
        toks = _extract_keyword_tokens_local(ut, limit=12)
        if toks:
            parts.append(" ".join(toks))

    q_toks = _extract_keyword_tokens_local(q, limit=24)
    parts.append(" ".join(q_toks) if q_toks else q)

    merged = "\n".join([p for p in parts if p.strip()]).strip()
    return merged or q


def search_chunks_by_id_candidates(
    db: Session,
    id_candidates: list[str],
    *,
    domain_ids: list[int] | None = None,
    limit_per_id: int = STRING_MATCH_MAX_PER_ID,
) -> list[Chunk]:
    """Perform fuzzy string search for chunks containing any of the IDs.

    把“每个 candidate 一次查询”改为“少量 candidate 合并 OR 一次查询”，
    显著减少 DB 往返与扫描次数（仍建议 DB 侧加 pg_trgm 索引）。
    """
    if not id_candidates:
        return []

    cands = _dedupe_preserve_order(id_candidates)
    cands.sort(key=lambda s: (0 if s.startswith("http") else 1, -len(s)))
    cands = cands[: max(1, STRING_MATCH_MAX_CANDIDATES)]

    conditions = [Chunk.content.ilike(f"%{cand}%") for cand in cands]
    stmt = select(Chunk).where(or_(*conditions))

    if domain_ids:
        stmt = stmt.join(Chunk.document).where(Document.domain_id.in_(list(domain_ids)))

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
    t_all = time.perf_counter()
    limit = top_k or DEFAULT_TOP_K

    # 1) string match candidates
    t0 = time.perf_counter()
    id_candidates = extract_id_candidates(question)
    strict_targets = extract_strict_match_targets(question)

    combined_candidates: list[str] = []
    seen_candidate: set[str] = set()
    for candidate in strict_targets + id_candidates:
        if candidate in seen_candidate:
            continue
        seen_candidate.add(candidate)
        combined_candidates.append(candidate)
    _perf("extract_candidates", ms=round(_ms(t0), 1), cands=len(combined_candidates))

    # 2) string match (optional)
    t0 = time.perf_counter()
    string_matches: list[Chunk] = []
    if not RAG_DISABLE_STRING_MATCH:
        string_matches = search_chunks_by_id_candidates(
            db,
            combined_candidates,
            domain_ids=domain_ids,
            limit_per_id=STRING_MATCH_MAX_PER_ID,
        )
    _perf("string_match", ms=round(_ms(t0), 1), disabled=int(RAG_DISABLE_STRING_MATCH), hits=len(string_matches))

    # 3) build query text + embed
    t0 = time.perf_counter()
    query_text = build_retrieval_query_text(question, history)
    _perf("build_query_text", ms=round(_ms(t0), 1), chars=len(query_text))

    t0 = time.perf_counter()
    query_vec = embed(query_text)
    _perf("embed_query", ms=round(_ms(t0), 1), vec_dim=(len(query_vec) if query_vec else 0))

    # 4) qdrant search
    t0 = time.perf_counter()
    search_results = search_with_scores(
        query_vec,
        limit,
        domain_ids=domain_ids,
    )
    _perf("qdrant_search", ms=round(_ms(t0), 1), hits=len(search_results))

    chunk_ids = [chunk_id for chunk_id, _ in search_results]

    # 5) fetch chunks from DB
    t0 = time.perf_counter()
    repo = ChunkRepository(db)
    fetched = repo.get_many(chunk_ids, domain_ids=domain_ids)
    chunk_map = {chunk.id: chunk for chunk in fetched}
    filtered_results = [(cid, score) for cid, score in search_results if cid in chunk_map]
    ordered_chunks = [chunk_map[cid] for cid, _ in filtered_results]
    _perf("db_fetch_chunks", ms=round(_ms(t0), 1), fetched=len(fetched), kept=len(ordered_chunks))

    # 6) merge
    t0 = time.perf_counter()
    merged_chunks = merge_string_and_vector_results(
        string_matches, ordered_chunks, limit=limit
    )
    _perf("merge_results", ms=round(_ms(t0), 1), merged=len(merged_chunks))

    score_map: dict[int, float] = {cid: score for cid, score in filtered_results}
    if merged_chunks:
        max_score = max(score_map.values(), default=0.0)
        string_score = max_score + 1.0 if string_matches else max_score
        for chunk in string_matches:
            score_map[chunk.id] = max(score_map.get(chunk.id, 0.0), string_score)

    # 7) neighbor expand
    t0 = time.perf_counter()
    expanded_chunks = expand_with_neighbor_chunks(
        db,
        merged_chunks,
        window_size=NEIGHBOR_WINDOW_SIZE,
        max_total_chunks=NEIGHBOR_MAX_TOTAL_CHUNKS,
        score_map=score_map,
    )
    _perf("neighbor_expand", ms=round(_ms(t0), 1), expanded=len(expanded_chunks))

    references = [(chunk.id, score_map.get(chunk.id, 0.0)) for chunk in expanded_chunks]
    _perf("retrieve_total", ms=round(_ms(t_all), 1), final_chunks=len(expanded_chunks))
    return expanded_chunks, references


@dataclass(frozen=True)
class ContextBuildResult:
    text: str
    used_chunks: list[Chunk]


@dataclass(frozen=True)
class StructuredAnswerResult:
    answer: str
    need_references: bool


def build_context(
    chunks: list[Chunk],
    *,
    per_chunk_char_limit: int = RAG_CHUNK_CHAR_LIMIT,
    max_total_chars: int = RAG_CONTEXT_MAX_CHARS,
    max_chunks: int = RAG_CONTEXT_MAX_CHUNKS,
) -> ContextBuildResult:
    """把检索到的 chunk 拼成给 LLM 的上下文，并控制体积；返回实际 used_chunks。"""
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


# -------------------------
# New references logic (stable)
# -------------------------
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
    if RAG_DISABLE_REFERENCES:
        return []
    if rows_per_title <= 0:
        return []

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

    per = max(1, int(rows_per_title))

    urls_by_title: dict[str, list[str]] = {t: [] for t in titles}
    seen_url_by_title: dict[str, set[str]] = {t: set() for t in titles}

    t_all = time.perf_counter()
    for t in titles:
        cond = _title_prefix_condition(t)
        if cond is None:
            continue

        stmt = select(Chunk.content).where(cond)

        if domain_ids:
            stmt = stmt.join(Chunk.document).where(Document.domain_id.in_(list(domain_ids)))

        stmt = stmt.order_by(Chunk.id.asc()).limit(per)

        rows = db.execute(stmt).scalars().all()

        for row_text in rows:
            row_title = extract_title(row_text)
            if row_title != t:
                continue

            for url in _extract_urls_from_row(row_text):
                if url in seen_url_by_title[t]:
                    continue
                seen_url_by_title[t].add(url)
                urls_by_title[t].append(url)

    _perf("build_references_db", ms=round(_ms(t_all), 1), titles=len(titles), per=per)
    return [(t, urls_by_title.get(t, [])) for t in titles]


def format_references_from_titles(
    entries: Sequence[tuple[str, list[str]]],
    language: str,
) -> str:
    """按新格式渲染：1. Title，链接：URL1（若多个 URL，下一行继续列）"""
    labels = _REFERENCE_LABELS.get(language) or _REFERENCE_LABELS[_FALLBACK_LANGUAGE]
    heading = labels.get("heading", "参考资料")
    heading_separator = labels.get("heading_separator", "：")
    title_link_separator = labels.get("title_link_separator", "，")
    link_label = labels.get("link_label", "链接")
    url_separator = labels.get("url_separator", "：")

    lines: list[str] = []
    for idx, (title, urls) in enumerate(entries, start=1):
        if urls:
            lines.append(f"{idx}. {title}{title_link_separator}{link_label}{url_separator}{urls[0]}")
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
        {"role": "user", "content": f"问题：{question}\n\n相关片段：\n{context}"},
    ]
    try:
        summary = chat(messages)
    except RuntimeError:
        logger.warning("failed to compress chunk memory, fallback to raw context")
        return context[:2000]
    return summary.strip()


def _strip_code_fence(text: str) -> str:
    """Remove a single fenced code block wrapper if the model adds one."""
    stripped = (text or "").strip()
    match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else stripped


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Extract the first JSON object from model output."""
    cleaned = _strip_code_fence(text)
    if not cleaned:
        return None

    decoder = json.JSONDecoder()
    for idx, char in enumerate(cleaned):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(cleaned[idx:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def _extract_json_string_field(raw: str, key: str) -> str | None:
    """Salvage a JSON-like string field from invalid JSON output."""
    pattern = rf'"{re.escape(key)}"\s*:\s*"((?:\\.|[^"\\])*)"'
    match = re.search(pattern, raw, flags=re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(f'"{match.group(1)}"')
    except json.JSONDecodeError:
        return None


def _coerce_bool(value: Any) -> bool | None:
    """Normalize bool-like values returned by the model."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in {0, 1}:
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "是", "需要", "need"}:
            return True
        if normalized in {"false", "0", "no", "n", "否", "不需要", "无需", "none"}:
            return False
    return None


def parse_structured_answer(raw: str, *, fallback_text: str) -> StructuredAnswerResult:
    """Parse the model's structured answer and fall back to plain text safely."""
    payload = _extract_json_object(raw)

    answer_value: Any = None
    bool_value: Any = None
    if payload:
        for key in ("answer", "content", "text", "response"):
            if key in payload:
                answer_value = payload[key]
                break
        for key in (
            "need_references",
            "include_references",
            "show_references",
            "should_include_references",
        ):
            if key in payload:
                bool_value = payload[key]
                break

    answer_text = answer_value.strip() if isinstance(answer_value, str) else ""
    if not answer_text:
        for key in ("answer", "content", "text", "response"):
            extracted = _extract_json_string_field(raw, key)
            if extracted and extracted.strip():
                answer_text = extracted.strip()
                break

    need_references = _coerce_bool(bool_value)
    if need_references is None:
        bool_match = re.search(
            r'"(?:need_references|include_references|show_references|should_include_references)"\s*:\s*(true|false|"true"|"false"|1|0)',
            raw,
            flags=re.IGNORECASE,
        )
        if bool_match:
            need_references = _coerce_bool(bool_match.group(1).strip('"'))

    if answer_text:
        return StructuredAnswerResult(
            answer=answer_text,
            need_references=bool(need_references) if need_references is not None else False,
        )

    cleaned = _strip_code_fence(raw).strip()
    if cleaned and not cleaned.startswith("{"):
        return StructuredAnswerResult(answer=cleaned, need_references=False)

    logger.warning("structured answer parse failed, falling back to default text")
    return StructuredAnswerResult(answer=fallback_text, need_references=False)


def chat(
    messages: Sequence[dict[str, str]],
    stream: bool = False,
    *,
    response_format: dict[str, Any] | None = None,
) -> str:
    """Call the cloud chat API (OpenAI-compatible) and return the assistant reply."""
    if stream:
        raise RuntimeError("streaming chat is not supported by the current cloud backend")
    if not CHAT_API_KEY:
        raise RuntimeError("CHAT_API_KEY is required to call the cloud chat API")

    payload = {"model": CHAT_MODEL, "messages": list(messages)}
    if response_format:
        payload["response_format"] = response_format
    req = request.Request(
        url=f"{CHAT_API_URL.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {CHAT_API_KEY}",
        },
        method="POST",
    )

    t0 = time.perf_counter()
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
    finally:
        _perf("cloud_chat_http", ms=round(_ms(t0), 1), model=CHAT_MODEL)

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
    t_all = time.perf_counter()
    _normalized_language, prompt_template = resolve_prompt_template(preferred_language)
    limit = top_k or DEFAULT_TOP_K

    _perf("answer_start", top_k=limit, domain_ids=(domain_ids or []), qlen=len(question or ""))

    t0 = time.perf_counter()
    chunks, references = retrieve_with_scores(
        question,
        limit,
        domain_ids,
        db=db,
        history=history,
    )
    _perf("answer_retrieve", ms=round(_ms(t0), 1), chunks=len(chunks), refs=len(references))

    if not references:
        return prompt_template["no_context"], [], []

    t0 = time.perf_counter()
    ctx = build_context(list(chunks))
    context = ctx.text
    _perf("answer_build_context", ms=round(_ms(t0), 1), used=len(ctx.used_chunks), ctx_chars=len(context or ""))

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
        messages.append({"role": "user", "content": prompt_template["context_intro"].format(context=context)})

    # 最终回答阶段 history 只保留最近 N 条用户提问
    if filtered_history:
        user_only = [m for m in filtered_history if m.get("role") == "user"]
        trimmed_user = user_only[-max(0, RAG_HISTORY_MAX_USER_TURNS):] if RAG_HISTORY_MAX_USER_TURNS else []
        if trimmed_user:
            messages.append({"role": "assistant", "content": "下面是此前用户的提问（仅用于理解上下文，不需要逐条回复）："})
            messages.extend(trimmed_user)

    messages.append(
        {
            "role": "user",
            "content": prompt_template["answer_output_intro"].format(question=question),
        }
    )

    t0 = time.perf_counter()
    raw_answer_text = ""
    try:
        raw_answer_text = chat(messages, response_format={"type": "json_object"})
    except RuntimeError:
        logger.warning("structured answer response_format unsupported, retrying with prompt-only JSON")
        raw_answer_text = chat(messages)
    _perf("answer_chat", ms=round(_ms(t0), 1), ans_chars=len(raw_answer_text or ""))

    structured_answer = parse_structured_answer(
        raw_answer_text,
        fallback_text=prompt_template["no_context"],
    )

    final_text = structured_answer.answer.strip() if structured_answer.answer else ""
    if not final_text:
        final_text = prompt_template["no_context"]

    # 参考文献（可关闭）
    ref_entries: list[tuple[str, list[str]]] = []
    if structured_answer.need_references:
        t0 = time.perf_counter()
        ref_entries = build_reference_entries_from_context(
            db,
            ctx.used_chunks,
            domain_ids=domain_ids,
            rows_per_title=RAG_REFERENCE_ROWS_PER_TITLE,
        )
        _perf("answer_refs", ms=round(_ms(t0), 1), disabled=int(RAG_DISABLE_REFERENCES), titles=len(ref_entries))
    else:
        _perf("answer_refs", ms=0.0, disabled=int(RAG_DISABLE_REFERENCES), titles=0, skipped=1)

    if ref_entries:
        reference_block = format_references_from_titles(ref_entries, _normalized_language)
        final_text = f"{final_text}\n\n{reference_block}"

    _perf("answer_total", ms=round(_ms(t_all), 1))
    return final_text, references, chunks
