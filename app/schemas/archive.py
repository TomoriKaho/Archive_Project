"""档案条目、下载资源与批量导入响应模型。"""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field

from .base import ORMModel


class ArchiveAssetOut(ORMModel):
    id: UUID
    filename: str
    content_type: str
    size_bytes: int
    sha256: str


class ArchiveAssetListOut(ORMModel):
    archive_id: UUID
    items: list[ArchiveAssetOut] = Field(default_factory=list)


class ArchiveImportJobOut(ORMModel):
    id: UUID
    source_filename: str
    duplicate_strategy: Literal["reject", "skip", "replace", "append"]
    status: Literal["queued", "processing", "completed", "failed"]
    total_entries: int
    processed_entries: int
    succeeded_entries: int
    failed_entries: int
    error_summary: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class ArchiveImportErrorsOut(ORMModel):
    job_id: UUID
    status: str
    errors: list[dict[str, Any]] = Field(default_factory=list)
