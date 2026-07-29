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
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_current_user, get_db
from app.models.entities import ArchiveAsset, ArchiveEntry, ArchiveImportJob, User
from app.schemas.archive import (
    ArchiveAssetListOut,
    ArchiveAssetOut,
    ArchiveImportErrorsOut,
    ArchiveImportJobOut,
)
from app.services.archive_assets import (
    get_asset_path,
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
