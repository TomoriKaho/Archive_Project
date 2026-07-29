"""档案条目资源的稳定标识、文件存储与批量导入。"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import mimetypes
import os
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.entities import (
    ArchiveAsset,
    ArchiveEntry,
    ArchiveImportJob,
    Document,
)


ARCHIVE_ASSET_ROOT = Path(
    os.getenv("ARCHIVE_ASSET_ROOT", "var/archive-assets")
).resolve()
MAX_IMPORT_BYTES = int(os.getenv("ARCHIVE_IMPORT_MAX_BYTES", str(512 * 1024 * 1024)))
MAX_IMPORT_FILES = int(os.getenv("ARCHIVE_IMPORT_MAX_FILES", "10000"))
MAX_UNCOMPRESSED_BYTES = int(
    os.getenv("ARCHIVE_IMPORT_MAX_UNCOMPRESSED_BYTES", str(5 * 1024 * 1024 * 1024))
)

_KEY_FIELDS = (
    "external_key",
    "archive_id",
    "id",
    "uuid",
    "unitid",
    "toegang_code",
    "档号",
    "编号",
)


class ArchiveImportValidationError(ValueError):
    def __init__(self, errors: list[dict[str, Any]]):
        super().__init__("archive import validation failed")
        self.errors = errors


def derive_archive_external_key(metadata: dict[str, Any], ordinal: int = 0) -> str:
    """优先使用业务标识，否则使用规范化元数据摘要生成稳定键。"""

    for key in _KEY_FIELDS:
        value = metadata.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()[:255]
    canonical = json.dumps(
        metadata,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def get_asset_path(object_key: str) -> Path:
    candidate = (ARCHIVE_ASSET_ROOT / "objects" / object_key).resolve()
    object_root = (ARCHIVE_ASSET_ROOT / "objects").resolve()
    if object_root not in candidate.parents:
        raise ValueError("invalid archive asset object key")
    return candidate


def save_import_package(upload_file, job_id: UUID) -> Path:
    """将上传包流式写入本地 staging，并限制压缩包大小。"""

    staging = ARCHIVE_ASSET_ROOT / "imports"
    staging.mkdir(parents=True, exist_ok=True)
    package_path = staging / f"{job_id}.zip"
    total = 0
    with package_path.open("wb") as output:
        while True:
            chunk = upload_file.file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_IMPORT_BYTES:
                output.close()
                package_path.unlink(missing_ok=True)
                raise ValueError("导入压缩包超过大小限制")
            output.write(chunk)
    return package_path


def _safe_member_path(raw_path: str) -> str:
    normalized = PurePosixPath(str(raw_path).replace("\\", "/"))
    if (
        not raw_path
        or normalized.is_absolute()
        or ".." in normalized.parts
        or normalized.as_posix().startswith("/")
    ):
        raise ValueError(f"非法压缩包路径: {raw_path}")
    return normalized.as_posix()


def _validate_zip(archive: zipfile.ZipFile) -> None:
    files = [item for item in archive.infolist() if not item.is_dir()]
    if len(files) > MAX_IMPORT_FILES:
        raise ValueError("导入文件数量超过限制")
    total_uncompressed = 0
    for item in files:
        _safe_member_path(item.filename)
        total_uncompressed += item.file_size
        if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
            raise ValueError("导入包解压后大小超过限制")


def _parse_metadata_json(raw: Any) -> dict[str, Any]:
    if raw is None or raw == "":
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(str(raw))
    except json.JSONDecodeError as exc:
        raise ValueError("metadata 必须是 JSON 对象") from exc
    if not isinstance(parsed, dict):
        raise ValueError("metadata 必须是 JSON 对象")
    return parsed


def _load_json_manifest(raw: bytes) -> list[dict[str, Any]]:
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("manifest.json 格式无效") from exc
    entries = payload.get("entries") if isinstance(payload, dict) else None
    if not isinstance(entries, list):
        raise ValueError("manifest.json 必须包含 entries 数组")
    return entries


def _load_csv_manifest(raw: bytes) -> list[dict[str, Any]]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("manifest.csv 必须使用 UTF-8 编码") from exc
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for row_number, row in enumerate(csv.DictReader(io.StringIO(text)), start=2):
        document_uuid = (row.get("document_uuid") or "").strip()
        external_key = (row.get("external_key") or "").strip()
        group_key = (document_uuid, external_key or f"row:{row_number}")
        entry = grouped.setdefault(
            group_key,
            {
                "document_uuid": document_uuid,
                "domain_id": row.get("domain_id"),
                "external_key": external_key,
                "archive_name": row.get("archive_name") or "",
                "ordinal": row.get("ordinal") or 0,
                "metadata": _parse_metadata_json(row.get("metadata_json")),
                "assets": [],
            },
        )
        resource_path = (row.get("resource_path") or "").strip()
        if resource_path:
            entry["assets"].append(
                {
                    "path": resource_path,
                    "display_name": row.get("display_name") or "",
                    "content_type": row.get("mime_type") or "",
                    "sha256": row.get("sha256") or "",
                }
            )
    return list(grouped.values())


def _load_manifest(archive: zipfile.ZipFile) -> list[dict[str, Any]]:
    names = {_safe_member_path(name): name for name in archive.namelist()}
    if "manifest.json" in names:
        return _load_json_manifest(archive.read(names["manifest.json"]))
    if "manifest.csv" in names:
        return _load_csv_manifest(archive.read(names["manifest.csv"]))
    raise ValueError("压缩包根目录必须包含 manifest.json 或 manifest.csv")


def _store_zip_member(
    archive: zipfile.ZipFile,
    member_name: str,
    expected_sha256: str | None,
) -> tuple[str, str, int]:
    objects_root = ARCHIVE_ASSET_ROOT / "objects"
    staging_root = ARCHIVE_ASSET_ROOT / "staging"
    objects_root.mkdir(parents=True, exist_ok=True)
    staging_root.mkdir(parents=True, exist_ok=True)

    digest = hashlib.sha256()
    size = 0
    with tempfile.NamedTemporaryFile(dir=staging_root, delete=False) as temp:
        temp_path = Path(temp.name)
        with archive.open(member_name) as source:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                digest.update(chunk)
                temp.write(chunk)

    sha256 = digest.hexdigest()
    if expected_sha256 and expected_sha256.lower() != sha256:
        temp_path.unlink(missing_ok=True)
        raise ValueError(f"文件校验失败: {member_name}")

    object_key = f"{sha256[:2]}/{sha256[2:4]}/{sha256}"
    destination = get_asset_path(object_key)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        temp_path.unlink(missing_ok=True)
    else:
        shutil.move(str(temp_path), destination)
    return object_key, sha256, size


def _normalize_entry(
    raw: dict[str, Any],
    index: int,
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("档案条目必须是 JSON 对象")
    document_uuid = str(raw.get("document_uuid") or "").strip()
    if not document_uuid:
        raise ValueError("缺少 document_uuid")
    metadata = _parse_metadata_json(raw.get("metadata"))
    external_key = str(raw.get("external_key") or "").strip()
    if not external_key:
        external_key = derive_archive_external_key(metadata, index)
    title = str(raw.get("archive_name") or raw.get("title") or "").strip()
    if not title:
        title = str(
            metadata.get("title")
            or metadata.get("name")
            or metadata.get("archive_name")
            or metadata.get("档案名称")
            or external_key
        ).strip()
    assets = raw.get("assets") or []
    if not isinstance(assets, list):
        raise ValueError("assets 必须是数组")
    try:
        ordinal = int(raw.get("ordinal") or index)
    except (TypeError, ValueError) as exc:
        raise ValueError("ordinal 必须是整数") from exc
    return {
        "document_uuid": UUID(document_uuid),
        "domain_id": int(raw["domain_id"]) if raw.get("domain_id") else None,
        "external_key": external_key[:255],
        "title": title[:512],
        "ordinal": ordinal,
        "metadata": metadata,
        "assets": assets,
    }


def _process_entries(
    db: Session,
    archive: zipfile.ZipFile,
    entries: list[dict[str, Any]],
    duplicate_strategy: str,
) -> int:
    member_names = {
        _safe_member_path(name): name
        for name in archive.namelist()
        if not name.endswith("/")
    }
    errors: list[dict[str, Any]] = []
    normalized_entries: list[dict[str, Any]] = []
    for index, raw in enumerate(entries, start=1):
        try:
            normalized_entries.append(_normalize_entry(raw, index))
        except (TypeError, ValueError) as exc:
            errors.append({"entry": index, "message": str(exc)})
    if errors:
        raise ArchiveImportValidationError(errors)

    succeeded = 0
    for index, item in enumerate(normalized_entries, start=1):
        document = db.execute(
            select(Document).where(Document.uuid == item["document_uuid"])
        ).scalar_one_or_none()
        if not document:
            errors.append({"entry": index, "message": "document_uuid 不存在"})
            continue
        if item["domain_id"] is not None and item["domain_id"] != document.domain_id:
            errors.append({"entry": index, "message": "domain_id 与文档不匹配"})
            continue

        entry = db.execute(
            select(ArchiveEntry).where(
                ArchiveEntry.document_id == document.id,
                ArchiveEntry.external_key == item["external_key"],
            )
        ).scalar_one_or_none()

        if entry and duplicate_strategy == "reject":
            errors.append(
                {
                    "entry": index,
                    "external_key": item["external_key"],
                    "message": "档案条目已存在",
                }
            )
            continue
        if entry and duplicate_strategy == "skip":
            succeeded += 1
            continue
        if not entry:
            entry = ArchiveEntry(
                document_id=document.id,
                domain_id=document.domain_id,
                external_key=item["external_key"],
                title=item["title"],
                ordinal=item["ordinal"],
                metadata_json=item["metadata"],
            )
            db.add(entry)
            db.flush()
        else:
            entry.title = item["title"]
            entry.ordinal = item["ordinal"]
            entry.metadata_json = item["metadata"]
            if duplicate_strategy == "replace":
                for existing_asset in list(entry.assets):
                    db.delete(existing_asset)
                db.flush()

        existing_assets = {
            asset.original_filename: asset for asset in entry.assets
        }
        for raw_asset in item["assets"]:
            if not isinstance(raw_asset, dict):
                errors.append({"entry": index, "message": "asset 必须是对象"})
                continue
            resource_path = _safe_member_path(str(raw_asset.get("path") or ""))
            archive_member = member_names.get(resource_path)
            if not archive_member:
                errors.append(
                    {
                        "entry": index,
                        "path": resource_path,
                        "message": "资源文件不在压缩包中",
                    }
                )
                continue
            display_name = Path(
                str(raw_asset.get("display_name") or resource_path)
            ).name
            if not display_name:
                errors.append({"entry": index, "message": "资源显示名称为空"})
                continue
            existing_asset = existing_assets.get(display_name)
            if existing_asset and duplicate_strategy == "append":
                errors.append(
                    {
                        "entry": index,
                        "path": resource_path,
                        "message": f"同名资源已存在: {display_name}",
                    }
                )
                continue
            try:
                object_key, sha256, size = _store_zip_member(
                    archive,
                    archive_member,
                    str(raw_asset.get("sha256") or "").strip() or None,
                )
            except ValueError as exc:
                errors.append(
                    {"entry": index, "path": resource_path, "message": str(exc)}
                )
                continue
            content_type = str(raw_asset.get("content_type") or "").strip()
            if not content_type:
                content_type = (
                    mimetypes.guess_type(display_name)[0]
                    or "application/octet-stream"
                )
            db.add(
                ArchiveAsset(
                    archive_entry_id=entry.id,
                    original_filename=display_name[:512],
                    object_key=object_key,
                    content_type=content_type[:255],
                    size_bytes=size,
                    sha256=sha256,
                    status="ready",
                )
            )
        succeeded += 1

    if errors:
        raise ArchiveImportValidationError(errors[:100])
    return succeeded


def process_archive_import_job(
    job_id: UUID,
    package_path: str,
    duplicate_strategy: str,
) -> None:
    """后台执行导入；数据库写入保持整批原子性。"""

    db = SessionLocal()
    package = Path(package_path)
    try:
        job = db.get(ArchiveImportJob, job_id)
        if not job:
            return
        job.status = "processing"
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        try:
            with zipfile.ZipFile(package) as archive:
                _validate_zip(archive)
                entries = _load_manifest(archive)
                job = db.get(ArchiveImportJob, job_id)
                job.total_entries = len(entries)
                db.commit()
                succeeded = _process_entries(
                    db, archive, entries, duplicate_strategy
                )
                job = db.get(ArchiveImportJob, job_id)
                job.processed_entries = len(entries)
                job.succeeded_entries = succeeded
                job.failed_entries = 0
                job.status = "completed"
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
        except (
            ArchiveImportValidationError,
            ValueError,
            zipfile.BadZipFile,
        ) as exc:
            db.rollback()
            job = db.get(ArchiveImportJob, job_id)
            errors = (
                exc.errors
                if isinstance(exc, ArchiveImportValidationError)
                else [{"message": str(exc)}]
            )
            job.status = "failed"
            job.failed_entries = max(len(errors), 1)
            job.processed_entries = job.total_entries
            job.error_summary = errors[:100]
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()
        package.unlink(missing_ok=True)
