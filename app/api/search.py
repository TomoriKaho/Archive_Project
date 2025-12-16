"""传统档案搜索相关的REST接口。"""
from __future__ import annotations

import csv
import io
import json
import logging
import re
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.entities import Document, Domain
from app.schemas.search import ArchiveSearchItem, ArchiveSearchResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["search"])


def _parse_domain_ids(raw_ids: str | None) -> list[int]:
    """解析逗号分隔的domain id字符串。"""

    if not raw_ids:
        return []
    ids: list[int] = []
    for part in raw_ids.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.append(int(part))
        except ValueError:
            raise HTTPException(status_code=400, detail="domain_ids must be integers")
    return ids


def _tokenize_query(query: str) -> list[str]:
    """将查询语句拆分为去重后的词元，过滤过短词汇。"""

    tokens = re.findall(r"[\w\u4e00-\u9fff]+", query, flags=re.UNICODE)
    normalized = []
    seen = set()
    for token in tokens:
        clean = token.strip()
        if len(clean) < 2:
            continue
        lower = clean.lower()
        if lower in seen:
            continue
        seen.add(lower)
        normalized.append(clean)
    return normalized


def _iter_documents_with_domain(db: Session, domain_ids: Sequence[int] | None) -> list[Tuple[Document, str]]:
    """拉取需要参与搜索的文档及其所属domain名称。"""

    stmt: Select[Tuple[Document, str]] = (
        select(Document, Domain.name)
        .join(Domain, Document.domain_id == Domain.id)
        .order_by(Document.created_at.desc(), Document.id.desc())
    )
    if domain_ids:
        stmt = stmt.where(Document.domain_id.in_(domain_ids))
    rows = db.execute(stmt).all()
    return [(row[0], row[1]) for row in rows]


def _ensure_csv_field_size_limit(raw_content: str) -> None:
    """保证CSV解析时的字段大小限制足够覆盖内容长度。"""

    if not raw_content:
        return
    current_limit = csv.field_size_limit()
    desired_limit = max(len(raw_content), current_limit)
    if desired_limit > current_limit:
        try:
            csv.field_size_limit(desired_limit)
        except OverflowError:
            csv.field_size_limit(max(current_limit, 1024 * 1024))


def _iter_archives(document: Document) -> Iterable[Any]:
    """按文档类型切换解析策略，逐个yield archive。"""

    metadata = document.doc_metadata or {}
    source = str(metadata.get("source") or "").lower()
    raw_content = document.raw_content or ""

    if source == "csv":
        stream = io.StringIO(raw_content.lstrip("\ufeff"))
        try:
            _ensure_csv_field_size_limit(raw_content)
            reader = csv.DictReader(stream)
        except csv.Error:
            reader = None
        if reader is not None:
            for row in reader:
                yield row
        return

    if source == "json":
        try:
            parsed = json.loads(raw_content)
        except json.JSONDecodeError:
            return
        if isinstance(parsed, dict) and isinstance(parsed.get("entities"), list):
            entities = parsed.get("entities") or []
        elif isinstance(parsed, list):
            entities = parsed
        else:
            entities = [parsed]
        for entity in entities:
            yield entity
        return

    for line in raw_content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            parsed_line = json.loads(stripped)
            yield parsed_line
        except json.JSONDecodeError:
            yield stripped


def _normalize_metadata(raw: Any) -> Dict[str, Any]:
    """将不同类型的archive值归一化为dict，便于前端树状展示。"""

    if isinstance(raw, dict):
        return raw
    if isinstance(raw, list):
        return {"items": raw}
    if isinstance(raw, (str, int, float, bool)):
        return {"value": raw}
    return {"value": str(raw)}


def _extract_archive_name(metadata: Dict[str, Any]) -> str:
    """从元数据中提取档案名称，优先常见字段，其次取首个值。"""

    preferred_keys = [
        "title",
        "name",
        "archive_name",
        "档案名称",
        "unitid",
    ]
    for key in preferred_keys:
        value = metadata.get(key)
        if value:
            return str(value)
    for value in metadata.values():
        if value:
            return str(value)
    return ""


def _collect_text_candidates(value: Any) -> list[str]:
    """展开元数据中的文本内容用于匹配。"""

    collected: list[str] = []
    if value is None:
        return collected
    if isinstance(value, str):
        collected.append(value)
    elif isinstance(value, (int, float, bool)):
        collected.append(str(value))
    elif isinstance(value, dict):
        for child in value.values():
            collected.extend(_collect_text_candidates(child))
    elif isinstance(value, list):
        for child in value:
            collected.extend(_collect_text_candidates(child))
    return collected


def _matches(tokens: list[str], text: str, mode: str) -> bool:
    """判断文本是否满足查询词元。"""

    if not text:
        return False
    if mode == "fuzzy":
        lower_text = text.lower()
        return all(token.lower() in lower_text for token in tokens)

    for token in tokens:
        pattern = rf"(?<![\w]){re.escape(token)}(?![\w])"
        if not re.search(pattern, text, flags=re.IGNORECASE):
            return False
    return True


@router.get("/search/archives", response_model=ArchiveSearchResponse)
def search_archives(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(10, ge=1, le=10, description="每页数量，最大10"),
    domain_ids: str | None = Query(
        default=None,
        description="逗号分隔的domain id列表，可选",
        alias="domain_ids",
    ),
    mode: str = Query("precise", pattern="^(precise|fuzzy)$"),
    db: Session = Depends(get_db),
):
    """在指定知识域内按archive粒度进行传统搜索。"""

    if len(q) > 250:
        raise HTTPException(status_code=400, detail="搜索关键词长度不能超过250个字符")

    tokens = _tokenize_query(q)
    if not tokens:
        raise HTTPException(status_code=400, detail="请输入不少于2个字符的有效搜索词")

    domain_id_list = _parse_domain_ids(domain_ids)
    documents = _iter_documents_with_domain(db, domain_id_list)

    start_index = (page - 1) * page_size
    end_index = start_index + page_size

    matched_items: List[ArchiveSearchItem] = []
    total_matches = 0

    for document, domain_name in documents:
        for archive in _iter_archives(document):
            normalized_metadata = _normalize_metadata(archive)
            text_candidates = _collect_text_candidates(normalized_metadata)
            haystack = " \n ".join(text_candidates)
            if not _matches(tokens, haystack, mode):
                continue

            archive_name = _extract_archive_name(normalized_metadata) or document.title
            total_matches += 1
            if total_matches <= start_index or total_matches > end_index:
                continue

            matched_items.append(
                ArchiveSearchItem(
                    page=total_matches,
                    archive_name=archive_name,
                    document_name=document.title,
                    domain_name=domain_name,
                    metadata=normalized_metadata,
                )
            )

    logger.info(
        "search_archives query=%s mode=%s domains=%s total=%s page=%s size=%s",
        q,
        mode,
        domain_id_list,
        total_matches,
        page,
        page_size,
    )
    return ArchiveSearchResponse(
        items=matched_items,
        total=total_matches,
        page=page,
        page_size=page_size,
    )

