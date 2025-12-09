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

STRING_MATCH_MAX_PER_ID = int(os.getenv("RAG_STRING_MATCH_MAX_PER_ID", "20"))
"""Upper bound of chunks fetched per ID candidate during string search."""

NEIGHBOR_WINDOW_SIZE = int(os.getenv("RAG_NEIGHBOR_WINDOW_SIZE", "1"))
"""Default window size when expanding chunks with their neighbors."""

NEIGHBOR_MAX_TOTAL_CHUNKS = int(os.getenv("RAG_NEIGHBOR_MAX_TOTAL_CHUNKS", "100"))
"""Safety limit to avoid overlong contexts after neighbor expansion."""

RAG_CHAT_TIMEOUT = int(os.getenv("RAG_CHAT_TIMEOUT", os.getenv("RAG_OLLAMA_TIMEOUT", "60")))
"""HTTP timeout applied to chat requests."""

CHUNK_MEMORY_WINDOW_MULTIPLIER = int(os.getenv("RAG_CHUNK_MEMORY_WINDOW_MULTIPLIER", "3"))
"""Number of historical chunk batches kept in memory, expressed as a multiplier of top_k."""

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
_ERA_PREFIX = re.compile(r"(平|昭|令)[^\d]{0,2}\d{1,}")
_URL_PATTERN = re.compile(r"https?://[^\s<>\u3000\"']+", re.IGNORECASE)


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
    *,
    limit: int | None = None,
) -> list[Chunk]:
    """Merge string and vector retrieval results with ID hits prioritized.

    Strategy: return all string matches first (ID recall is most important),
    then append remaining vector hits while keeping unique chunk IDs.
    When limit is provided, truncate the merged list to avoid exceeding the
    caller's budget.
    """

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
    ordinal_scores: defaultdict[int, dict[int, float]] = defaultdict(dict)
    for chunk in chunks:
        base_score = 0.0 if score_map is None else score_map.get(chunk.id, 0.0)
        for offset in range(-window_size, window_size + 1):
            ordinal = chunk.ordinal + offset
            targets[chunk.document_id].add(ordinal)
            # Neighbor scores slightly decay by distance but stay tied to the anchor chunk.
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


def build_retrieval_query_text(
    question: str,
    history: Sequence[dict[str, str]] | None = None,
) -> str:
    """根据当前问题 + 近期会话历史，构造用于向量检索的查询文本。

    这样可以缓解“它 / 这个档案”之类代词导致的语义丢失问题，并优先利用
    已经由 LLM 压缩过的摘要，避免长篇上下文喧宾夺主。
    """

    @lru_cache(maxsize=32)
    def _extract_keyword_tokens(text: str, *, limit: int = 12) -> list[str]:
        """提取用于向量检索的关键词，改为通过聊天模型生成。"""

        def _fallback_regex_tokens(content: str, *, count: int) -> list[str]:
            normalized = content.strip()
            tokens: list[str] = _DIGIT_RUN.findall(normalized)
            tokens.extend(_ALNUM_MIXED.findall(normalized))
            rough_parts = re.split(
                r"[\s,.;:!?，。！？；、\-\(\)\[\]\{\}<>\"'\/]+", normalized
            )
            for part in rough_parts:
                piece = part.strip()
                if len(piece) < 2:
                    continue
                tokens.append(piece)

            seen: set[str] = set()
            unique: list[str] = []
            for token in tokens:
                if token in seen:
                    continue
                seen.add(token)
                unique.append(token)
                if len(unique) >= count:
                    break
            return unique

        if not text:
            return []

        normalized = text.strip()
        if not normalized:
            return []

        system_prompt = (
            "你是一个关键词提取器。请从文本中抽取不超过{limit}个关键词或短语，"
            "优先保留年份、数字、编号、实体名（如地名、人名、机构名）、重要名词。"
            "仅输出用空格分隔的关键词列表，不要添加额外解释。"
        ).format(limit=limit)
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    "文本：" + normalized + "\n\n格式：关键词1 关键词2 ...，总数不超过 {limit} 个。"
                ).format(limit=limit),
            },
        ]

        try:
            raw = chat(messages)
        except RuntimeError:
            logger.warning("LLM 关键词提取失败，回退正则方式")
            return _fallback_regex_tokens(normalized, count=limit)

        tokens = []
        for token in re.split(r"[\s,，、]+", raw.strip()):
            piece = token.strip()
            if not piece:
                continue
            tokens.append(piece)
            if len(tokens) >= limit:
                break

        if not tokens:
            return _fallback_regex_tokens(normalized, count=limit)
        return tokens

    if not history:
        # 没有历史，直接用当前问题的关键词
        keywords = _extract_keyword_tokens(question)
        return " ".join(keywords) if keywords else question.strip()

    # 优先取最近的“对话摘要”（system 角色消息），摘要已经经过 LLM 压缩，可
    # 以提供稳定的历史语义，又不会像长篇回答那样主导嵌入。
    summary: str | None = None
    for msg in reversed(history):
        if msg.get("role") != "system":
            continue
        content = (msg.get("content") or "").strip()
        if not content:
            continue
        summary = content[:800]  # 摘要一般不长，但仍做安全截断
        break

    # 仅保留最近几条「用户提问」，避免上一轮长篇回答主导向量语义
    tail = [
        msg
        for msg in list(history)[-6:]
        if msg.get("role") == "user" and (msg.get("content") or "").strip()
    ]

    history_lines: list[str] = []
    if summary:
        summary_keywords = _extract_keyword_tokens(summary, limit=8)
        summary_block = " ".join(summary_keywords) if summary_keywords else summary
        history_lines.append(f"对话摘要关键词：{summary_block}")

    # 把用户的发言简单串起来（限制单条长度，降低历史权重）
    for msg in tail[-3:]:  # 最多取 3 条用户提问，聚焦近期主题
        content = (msg.get("content") or "").strip()
        # 仅保留关键词，避免长篇描述主导嵌入
        keywords = _extract_keyword_tokens(content)
        trimmed = " ".join(keywords) if keywords else content[:200]
        history_lines.append(f"用户关键词：{trimmed}")

    history_block = "\n".join(history_lines).strip()

    # 最后明确告诉嵌入模型：下面是当前问题
    question_keywords = _extract_keyword_tokens(question)
    current_line = "当前问题关键词：" + (
        " ".join(question_keywords) if question_keywords else question.strip()
    )

    if history_block:
        return f"{history_block}\n\n{current_line}"
    return current_line


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
    strict_targets = extract_strict_match_targets(question)
    combined_candidates: list[str] = []
    seen_candidate: set[str] = set()
    for candidate in strict_targets + id_candidates:
        if candidate in seen_candidate:
            continue
        seen_candidate.add(candidate)
        combined_candidates.append(candidate)
    string_matches = search_chunks_by_id_candidates(
        db, combined_candidates, domain_ids=domain_ids, limit_per_id=STRING_MATCH_MAX_PER_ID
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

    merged_chunks = merge_string_and_vector_results(
        string_matches, ordered_chunks, limit=limit
    )

    score_map: dict[int, float] = {cid: score for cid, score in filtered_results}
    if merged_chunks:
        max_score = max(score_map.values(), default=0.0)
        string_score = max_score + 1.0 if string_matches else max_score
        for chunk in string_matches:
            score_map[chunk.id] = max(score_map.get(chunk.id, 0.0), string_score)

    expanded_chunks = expand_with_neighbor_chunks(
        db,
        merged_chunks,
        window_size=NEIGHBOR_WINDOW_SIZE,
        max_total_chunks=limit,
        score_map=score_map,
    )

    references = [(chunk.id, score_map.get(chunk.id, 0.0)) for chunk in expanded_chunks]
    return expanded_chunks, references


def build_context(chunks: list[Chunk]) -> str:
    """把检索到的 chunk 拼成给 LLM 的上下文，只保留正文内容。"""

    if not chunks:
        return ""

    contents: list[str] = []
    for chunk in chunks:
        text = (chunk.content or "").strip()
        if not text:
            continue
        contents.append(text)

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
        prefix = {
            "user": "用户",
            "assistant": "助手",
            "system": "系统",
        }.get(role, role)
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

    context = build_context(chunks)
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

        # ... 前面的 system_prompt / history 处理保持不变

    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt}
    ]

    # 先把相关档案片段作为一条 user 消息给出去
    if context:
        messages.append(
            {
                "role": "user",
                "content": prompt_template["context_intro"].format(context=context),
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
