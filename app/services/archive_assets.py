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
from typing import Any, Iterable
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.entities import (
    ArchiveAsset,
    ArchiveEntry,
    ArchiveImportJob,
    ArchiveUploadSession,
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
ARCHIVE_UPLOAD_CHUNK_BYTES = int(
    os.getenv("ARCHIVE_UPLOAD_CHUNK_BYTES", str(8 * 1024 * 1024))
)
ARCHIVE_UPLOAD_MAX_CHUNK_BYTES = int(
    os.getenv("ARCHIVE_UPLOAD_MAX_CHUNK_BYTES", str(16 * 1024 * 1024))
)
ARCHIVE_UPLOAD_CHUNK_BYTES = min(
    ARCHIVE_UPLOAD_CHUNK_BYTES, ARCHIVE_UPLOAD_MAX_CHUNK_BYTES
)
ARCHIVE_UPLOAD_MAX_FILE_BYTES = int(
    os.getenv("ARCHIVE_UPLOAD_MAX_FILE_BYTES", str(10 * 1024 * 1024 * 1024))
)

_KEY_FIELDS = (
    "external_key",
    "archive_id",
    "档案id",
    "档案ID",
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


def get_upload_path(upload_id: UUID) -> Path:
    """返回分片上传临时文件路径，路径只由服务端 UUID 决定。"""

    upload_root = (ARCHIVE_ASSET_ROOT / "uploads").resolve()
    upload_root.mkdir(parents=True, exist_ok=True)
    return upload_root / f"{upload_id}.part"


def iter_document_archives(document: Document) -> Iterable[Any]:
    """按文档来源格式逐条读取档案元数据。"""

    metadata = document.doc_metadata or {}
    source = str(metadata.get("source") or "").lower()
    raw_content = document.raw_content or ""

    if source == "csv":
        stream = io.StringIO(raw_content.lstrip("\ufeff"))
        try:
            csv.field_size_limit(max(csv.field_size_limit(), len(raw_content)))
            yield from csv.DictReader(stream)
        except (csv.Error, OverflowError):
            return
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
        yield from entities
        return

    for line in raw_content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            yield json.loads(stripped)
        except json.JSONDecodeError:
            yield stripped


def normalize_archive_metadata(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, list):
        return {"items": raw}
    if isinstance(raw, (str, int, float, bool)):
        return {"value": raw}
    return {"value": str(raw)}


def extract_archive_title(metadata: dict[str, Any], fallback: str) -> str:
    for key in ("title", "titulo", "name", "archive_name", "档案名称", "unitid"):
        value = metadata.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    for value in metadata.values():
        if value is not None and str(value).strip():
            return str(value).strip()
    return fallback


def _normalize_source_archive_id(value: Any) -> str:
    text = str(value or "").strip()
    if text.endswith(".0") and text[:-2].isdigit():
        return text[:-2]
    return text


def _metadata_source_archive_id(metadata: dict[str, Any]) -> str:
    for key in (
        "档案id",
        "档案ID",
        "source_archive_id",
        "source_id",
        "数据库唯一ID（ES/AGI/档案馆自有ID）",
        "数据库唯一ID\n（ES/AGI/档案馆自有ID）",
    ):
        value = metadata.get(key)
        if value is not None and str(value).strip():
            return _normalize_source_archive_id(value)
    return ""


def resolve_archive_entry(
    db: Session,
    document_uuid: UUID,
    source_archive_id: str,
) -> ArchiveEntry:
    """通过来源档案 ID 找到原始条目，并返回平台内部稳定条目。"""

    document = db.execute(
        select(Document).where(Document.uuid == document_uuid)
    ).scalar_one_or_none()
    if not document:
        raise LookupError("document_uuid 不存在")

    wanted = _normalize_source_archive_id(source_archive_id)
    direct = db.execute(
        select(ArchiveEntry).where(
            ArchiveEntry.document_id == document.id,
            ArchiveEntry.external_key == wanted,
        )
    ).scalar_one_or_none()
    if direct:
        return direct

    records: list[tuple[int, dict[str, Any], str]] = []
    matches: list[tuple[int, dict[str, Any], str]] = []
    for ordinal, raw in enumerate(iter_document_archives(document), start=1):
        metadata = normalize_archive_metadata(raw)
        source_id = _metadata_source_archive_id(metadata)
        external_key = derive_archive_external_key(metadata, ordinal)
        records.append((ordinal, metadata, external_key))
        if source_id == wanted:
            matches.append((ordinal, metadata, external_key))
    if not matches:
        raise LookupError(f"文档中不存在来源档案 id: {wanted}")
    if len(matches) > 1:
        raise ValueError(f"文档中的来源档案 id 不唯一: {wanted}")

    existing_keys = set(
        db.execute(
            select(ArchiveEntry.external_key).where(
                ArchiveEntry.document_id == document.id
            )
        ).scalars()
    )
    created_by_key: dict[str, ArchiveEntry] = {}
    for ordinal, metadata, external_key in records:
        if external_key in existing_keys:
            continue
        entry = ArchiveEntry(
            document_id=document.id,
            domain_id=document.domain_id,
            external_key=external_key,
            title=extract_archive_title(metadata, document.title)[:512],
            ordinal=ordinal,
            metadata_json=metadata,
        )
        db.add(entry)
        existing_keys.add(external_key)
        created_by_key[external_key] = entry
    db.flush()
    _, _, target_key = matches[0]
    target = created_by_key.get(target_key)
    if target:
        return target
    target = db.execute(
        select(ArchiveEntry).where(
            ArchiveEntry.document_id == document.id,
            ArchiveEntry.external_key == target_key,
        )
    ).scalar_one_or_none()
    if not target:
        raise RuntimeError("档案条目正规化失败")
    return target


def begin_archive_upload(
    db: Session,
    *,
    created_by_user_id: int,
    document_uuid: UUID,
    source_archive_id: str,
    filename: str,
    content_type: str,
    size_bytes: int,
    sha256: str,
) -> ArchiveUploadSession:
    """创建或恢复一个按来源档案 ID 绑定的分片上传会话。"""

    if size_bytes > ARCHIVE_UPLOAD_MAX_FILE_BYTES:
        raise ValueError("文件超过服务端允许的最大大小")
    safe_filename = Path(filename).name.strip()
    if not safe_filename or safe_filename != filename.strip():
        raise ValueError("filename 必须是不含目录的文件名")

    entry = resolve_archive_entry(db, document_uuid, source_archive_id)
    digest = sha256.lower()
    existing_asset = db.execute(
        select(ArchiveAsset).where(
            ArchiveAsset.archive_entry_id == entry.id,
            ArchiveAsset.original_filename == safe_filename,
        )
    ).scalar_one_or_none()
    if existing_asset:
        if (
            existing_asset.sha256 == digest
            and existing_asset.size_bytes == size_bytes
        ):
            completed = ArchiveUploadSession(
                created_by_user_id=created_by_user_id,
                archive_entry_id=entry.id,
                archive_asset_id=existing_asset.id,
                original_filename=safe_filename,
                content_type=content_type or existing_asset.content_type,
                size_bytes=size_bytes,
                sha256=digest,
                received_bytes=size_bytes,
                status="completed",
                completed_at=datetime.now(timezone.utc),
            )
            db.add(completed)
            db.flush()
            return completed
        raise FileExistsError("该档案条目已有同名但内容不同的资源")

    active = db.execute(
        select(ArchiveUploadSession)
        .where(
            ArchiveUploadSession.archive_entry_id == entry.id,
            ArchiveUploadSession.original_filename == safe_filename,
            ArchiveUploadSession.sha256 == digest,
            ArchiveUploadSession.size_bytes == size_bytes,
            ArchiveUploadSession.status == "active",
        )
        .order_by(ArchiveUploadSession.created_at.desc())
    ).scalars().first()
    if active:
        path = get_upload_path(active.id)
        actual_size = path.stat().st_size if path.exists() else 0
        if actual_size != active.received_bytes:
            active.received_bytes = actual_size
        return active

    upload = ArchiveUploadSession(
        id=uuid4(),
        created_by_user_id=created_by_user_id,
        archive_entry_id=entry.id,
        original_filename=safe_filename,
        content_type=content_type or "application/octet-stream",
        size_bytes=size_bytes,
        sha256=digest,
        received_bytes=0,
        status="active",
    )
    db.add(upload)
    db.flush()
    get_upload_path(upload.id).touch(exist_ok=False)
    return upload


def complete_archive_upload(
    db: Session,
    upload: ArchiveUploadSession,
) -> ArchiveAsset:
    """校验完整文件并转入内容寻址存储，然后建立下载资源记录。"""

    if upload.status == "completed" and upload.archive_asset_id:
        asset = db.get(ArchiveAsset, upload.archive_asset_id)
        if asset:
            return asset
    if upload.status != "active":
        raise ValueError("上传会话已不可完成")
    if upload.received_bytes != upload.size_bytes:
        raise ValueError("文件尚未上传完整")

    path = get_upload_path(upload.id)
    if not path.is_file() or path.stat().st_size != upload.size_bytes:
        raise ValueError("服务端临时文件大小不一致")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(4 * 1024 * 1024):
            digest.update(chunk)
    actual_sha256 = digest.hexdigest()
    if actual_sha256 != upload.sha256:
        path.unlink(missing_ok=True)
        upload.status = "failed"
        upload.error_message = "SHA-256 校验失败"
        raise ValueError(upload.error_message)

    existing_asset = db.execute(
        select(ArchiveAsset).where(
            ArchiveAsset.archive_entry_id == upload.archive_entry_id,
            ArchiveAsset.original_filename == upload.original_filename,
        )
    ).scalar_one_or_none()
    if existing_asset:
        if (
            existing_asset.sha256 == upload.sha256
            and existing_asset.size_bytes == upload.size_bytes
        ):
            path.unlink(missing_ok=True)
            upload.status = "completed"
            upload.archive_asset_id = existing_asset.id
            upload.completed_at = datetime.now(timezone.utc)
            return existing_asset
        raise FileExistsError("该档案条目已有同名但内容不同的资源")

    object_key = (
        f"{upload.sha256[:2]}/{upload.sha256[2:4]}/{upload.sha256}"
    )
    destination = get_asset_path(object_key)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        path.unlink(missing_ok=True)
    else:
        shutil.move(str(path), destination)

    asset = ArchiveAsset(
        archive_entry_id=upload.archive_entry_id,
        original_filename=upload.original_filename,
        object_key=object_key,
        content_type=upload.content_type,
        size_bytes=upload.size_bytes,
        sha256=upload.sha256,
        status="ready",
    )
    db.add(asset)
    db.flush()
    upload.archive_asset_id = asset.id
    upload.status = "completed"
    upload.completed_at = datetime.now(timezone.utc)
    upload.error_message = None
    return asset


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
