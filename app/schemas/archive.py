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


class ArchiveUploadCreate(ORMModel):
    document_uuid: UUID
    source_archive_id: str = Field(min_length=1, max_length=255)
    filename: str = Field(min_length=1, max_length=512)
    content_type: str = Field(default="application/pdf", max_length=255)
    size_bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")


class ArchiveUploadOut(ORMModel):
    id: UUID
    archive_entry_id: UUID
    archive_asset_id: UUID | None = None
    filename: str
    content_type: str
    size_bytes: int
    sha256: str
    received_bytes: int
    chunk_size: int
    status: Literal["active", "completed", "failed"]
    error_message: str | None = None
