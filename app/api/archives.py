"""档案资源导入、查询与下载接口。"""

from __future__ import annotations

from typing import Literal
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_current_user, get_db
from app.models.entities import (
    ArchiveAsset,
    ArchiveEntry,
    ArchiveImportJob,
    ArchiveUploadSession,
    User,
)
from app.schemas.archive import (
    ArchiveAssetListOut,
    ArchiveAssetOut,
    ArchiveImportErrorsOut,
    ArchiveImportJobOut,
    ArchiveUploadCreate,
    ArchiveUploadOut,
)
from app.services.archive_assets import (
    ARCHIVE_UPLOAD_CHUNK_BYTES,
    ARCHIVE_UPLOAD_MAX_CHUNK_BYTES,
    begin_archive_upload,
    complete_archive_upload,
    get_asset_path,
    get_upload_path,
    process_archive_import_job,
    save_import_package,
)


router = APIRouter(tags=["archives"])


def _asset_out(asset: ArchiveAsset) -> ArchiveAssetOut:
    return ArchiveAssetOut(
        id=asset.id,
        filename=asset.original_filename,
        content_type=asset.content_type,
        size_bytes=asset.size_bytes,
        sha256=asset.sha256,
    )


def _upload_out(upload: ArchiveUploadSession) -> ArchiveUploadOut:
    return ArchiveUploadOut(
        id=upload.id,
        archive_entry_id=upload.archive_entry_id,
        archive_asset_id=upload.archive_asset_id,
        filename=upload.original_filename,
        content_type=upload.content_type,
        size_bytes=upload.size_bytes,
        sha256=upload.sha256,
        received_bytes=upload.received_bytes,
        chunk_size=ARCHIVE_UPLOAD_CHUNK_BYTES,
        status=upload.status,
        error_message=upload.error_message,
    )


def _get_owned_upload(
    db: Session,
    upload_id: UUID,
    current_admin: User,
    *,
    for_update: bool = False,
) -> ArchiveUploadSession:
    statement = select(ArchiveUploadSession).where(
        ArchiveUploadSession.id == upload_id
    )
    if for_update:
        statement = statement.with_for_update()
    upload = db.execute(statement).scalar_one_or_none()
    if not upload:
        raise HTTPException(status_code=404, detail="上传会话不存在")
    if (
        upload.created_by_user_id is not None
        and upload.created_by_user_id != current_admin.id
    ):
        raise HTTPException(status_code=403, detail="不能操作其他管理员的上传会话")
    return upload


@router.post(
    "/admin/archive-uploads",
    response_model=ArchiveUploadOut,
    status_code=status.HTTP_201_CREATED,
)
def create_archive_upload(
    payload: ArchiveUploadCreate,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> ArchiveUploadOut:
    """创建或恢复面向超大档案文件的分片上传会话。"""

    try:
        upload = begin_archive_upload(
            db,
            created_by_user_id=current_admin.id,
            document_uuid=payload.document_uuid,
            source_archive_id=payload.source_archive_id,
            filename=payload.filename,
            content_type=payload.content_type,
            size_bytes=payload.size_bytes,
            sha256=payload.sha256,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _upload_out(upload)


@router.get(
    "/admin/archive-uploads/{upload_id}",
    response_model=ArchiveUploadOut,
)
def get_archive_upload(
    upload_id: UUID,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> ArchiveUploadOut:
    return _upload_out(_get_owned_upload(db, upload_id, current_admin))


@router.put(
    "/admin/archive-uploads/{upload_id}/chunk",
    response_model=ArchiveUploadOut,
)
async def upload_archive_chunk(
    upload_id: UUID,
    request: Request,
    offset: int = Query(..., ge=0),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> ArchiveUploadOut:
    """从指定偏移追加一个原始二进制分片，偏移不一致时拒绝写入。"""

    raw_length = request.headers.get("content-length")
    if raw_length is None:
        raise HTTPException(status_code=411, detail="分片必须提供 Content-Length")
    try:
        content_length = int(raw_length)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Content-Length 无效") from exc
    if content_length <= 0 or content_length > ARCHIVE_UPLOAD_MAX_CHUNK_BYTES:
        raise HTTPException(status_code=413, detail="分片大小超出限制")

    upload = _get_owned_upload(
        db, upload_id, current_admin, for_update=True
    )
    if upload.status != "active":
        if upload.status == "completed":
            return _upload_out(upload)
        raise HTTPException(status_code=409, detail="上传会话已不可写入")
    if offset != upload.received_bytes:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "上传偏移不一致",
                "expected_offset": upload.received_bytes,
            },
        )
    if offset + content_length > upload.size_bytes:
        raise HTTPException(status_code=413, detail="分片超过声明的文件大小")

    path = get_upload_path(upload.id)
    actual_size = path.stat().st_size if path.exists() else 0
    if actual_size != offset:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "服务端临时文件与上传状态不一致",
                "expected_offset": actual_size,
            },
        )

    written = 0
    try:
        with path.open("ab") as output:
            async for chunk in request.stream():
                if not chunk:
                    continue
                written += len(chunk)
                if written > content_length:
                    raise ValueError("请求体超过 Content-Length")
                output.write(chunk)
            output.flush()
    except BaseException:
        with path.open("r+b") as output:
            output.truncate(offset)
        raise
    if written != content_length:
        with path.open("r+b") as output:
            output.truncate(offset)
        raise HTTPException(status_code=400, detail="分片长度与 Content-Length 不符")

    upload.received_bytes = offset + written
    return _upload_out(upload)


@router.post(
    "/admin/archive-uploads/{upload_id}/complete",
    response_model=ArchiveUploadOut,
)
def finish_archive_upload(
    upload_id: UUID,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> ArchiveUploadOut:
    """校验完整文件哈希并发布为可供前端下载的档案资源。"""

    upload = _get_owned_upload(
        db, upload_id, current_admin, for_update=True
    )
    try:
        complete_archive_upload(db, upload)
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        if upload.status == "failed":
            db.commit()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _upload_out(upload)


@router.post(
    "/admin/archive-imports",
    response_model=ArchiveImportJobOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_archive_import(
    background_tasks: BackgroundTasks,
    package: UploadFile = File(...),
    duplicate_strategy: Literal["reject", "skip", "replace", "append"] = Form(
        "reject"
    ),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> ArchiveImportJobOut:
    """接收 ZIP + manifest 导入包并异步处理。"""

    filename = (package.filename or "archive-import.zip").strip()
    if not filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="导入文件必须是 ZIP")

    job_id = uuid4()
    try:
        package_path = save_import_package(package, job_id)
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    job = ArchiveImportJob(
        id=job_id,
        created_by_user_id=current_admin.id,
        source_filename=filename[:512],
        duplicate_strategy=duplicate_strategy,
        status="queued",
        error_summary=[],
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    background_tasks.add_task(
        process_archive_import_job,
        job.id,
        str(package_path),
        duplicate_strategy,
    )
    return ArchiveImportJobOut.model_validate(job)


@router.get(
    "/admin/archive-imports/{job_id}",
    response_model=ArchiveImportJobOut,
)
def get_archive_import(
    job_id: UUID,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> ArchiveImportJobOut:
    job = db.get(ArchiveImportJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="导入任务不存在")
    return ArchiveImportJobOut.model_validate(job)


@router.get(
    "/admin/archive-imports/{job_id}/errors",
    response_model=ArchiveImportErrorsOut,
)
def get_archive_import_errors(
    job_id: UUID,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> ArchiveImportErrorsOut:
    job = db.get(ArchiveImportJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="导入任务不存在")
    return ArchiveImportErrorsOut(
        job_id=job.id,
        status=job.status,
        errors=job.error_summary or [],
    )


@router.get(
    "/archives/{archive_id}/assets",
    response_model=ArchiveAssetListOut,
)
def list_archive_assets(
    archive_id: UUID,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ArchiveAssetListOut:
    entry = db.get(ArchiveEntry, archive_id)
    if not entry:
        raise HTTPException(status_code=404, detail="档案条目不存在")
    assets = db.execute(
        select(ArchiveAsset)
        .where(
            ArchiveAsset.archive_entry_id == archive_id,
            ArchiveAsset.status == "ready",
        )
        .order_by(ArchiveAsset.original_filename.asc())
    ).scalars()
    return ArchiveAssetListOut(
        archive_id=archive_id,
        items=[_asset_out(asset) for asset in assets],
    )


@router.get("/archive-assets/{asset_id}/download")
def download_archive_asset(
    asset_id: UUID,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    asset = db.get(ArchiveAsset, asset_id)
    if not asset or asset.status != "ready":
        raise HTTPException(status_code=404, detail="档案资源不存在")
    try:
        path = get_asset_path(asset.object_key)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="档案资源路径无效") from exc
    if not path.is_file():
        raise HTTPException(status_code=404, detail="档案资源文件缺失")
    return FileResponse(
        path=path,
        media_type=asset.content_type or "application/octet-stream",
        filename=asset.original_filename,
    )
