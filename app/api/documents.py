"""文档与chunk相关的REST接口。"""
from __future__ import annotations  # 允许前置类型注解

import json  # 处理Form中的元数据
import logging  # 统一日志输出
from typing import List, Literal, Optional  # 类型注解
from uuid import UUID  # 使用UUID匹配数据库字段

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)  # FastAPI核心组件
from sqlalchemy.orm import Session  # 数据库会话类型

from app.api.deps import get_db  # 获取数据库session的依赖
from app.repositories.document_repo import DocumentRepository  # 文档仓储
from app.repositories.domain_repo import DomainRepository  # domain仓储用于校验存在性
from app.repositories.chunk_repo import ChunkRepository  # chunk仓储
from app.schemas.document import (  # 文档相关schema
    DocumentCreate,
    DocumentListResponse,
    DocumentOut,
    DocumentUpdate,
)
from app.schemas.chunk import ChunkOut  # chunk输出schema
from app.services.chunking import (
    make_chunks,
    parse_structured_entities_from_csv,
)  # 文档切分服务
from app.services.rag_service import index_chunks, remove_vectors  # 自动管理向量库

router = APIRouter(tags=["documents"])  # 声明文档相关路由
logger = logging.getLogger(__name__)  # 初始化模块级日志


def _strip_tags(metadata: dict | None) -> dict:
    """移除元数据中遗留的标签键。"""
    if not metadata:
        return {}
    if "tags" not in metadata:
        return metadata
    return {key: value for key, value in metadata.items() if key != "tags"}


def _build_document_response(document) -> DocumentOut:
    """将数据库实体转换为不含标签信息的响应模型。"""
    schema = DocumentOut.model_validate(document)
    schema.doc_metadata.pop("tags", None)
    return schema


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(
    domain_id: Optional[int] = Query(default=None, description="按domain过滤，缺省返回全量"),  # 可选domain过滤
    search: Optional[str] = Query(
        default=None,
        min_length=1,
        max_length=100,
        description="按标题模糊搜索（大小写不敏感）",
    ),  # 支持标题模糊搜索
    limit: int = Query(20, ge=1, le=100, description="单页数量，最大100以避免全表扫描"),  # 限制单次查询量
    offset: int = Query(0, ge=0, description="分页偏移量，从0开始"),  # 偏移量
    sort_by: Literal["created_at", "title", "domain", "updated_at"] = Query(
        "created_at",
        description="排序字段，可选created_at、title、domain或updated_at",
    ),  # 枚举校验排序字段
    order: Literal["asc", "desc"] = Query(
        "desc",
        description="排序方向，可选asc或desc",
    ),  # 枚举校验排序方向
    db: Session = Depends(get_db),  # 注入数据库会话
):
    """获取文档列表，支持分页与排序。"""
    doc_repo = DocumentRepository(db)  # 初始化仓储
    search_value = search.strip() if search else None
    items = doc_repo.list_with_filters(
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        order=order,
        domain_id=domain_id,
        search=search_value,
    )  # 查询数据
    total = doc_repo.count_with_filters(domain_id=domain_id, search=search_value)  # 计算总量
    logger.info(
        "list_documents_paged domain=%s limit=%s offset=%s sort_by=%s order=%s total=%s",
        domain_id,
        limit,
        offset,
        sort_by,
        order,
        total,
    )  # 记录分页查询
    return DocumentListResponse(
        items=[_build_document_response(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        order=order,
    )
    # 设计说明：limit设置上限100，既满足前端需求又避免一次性拉取大量数据导致数据库压力；COUNT(*)在当前规模成本可接受。


@router.get("/documents/by-uuid/{doc_uuid}", response_model=DocumentOut)
def get_document_by_uuid(doc_uuid: UUID, db: Session = Depends(get_db)):
    """按UUID获取单个文档。"""
    doc = DocumentRepository(db).get_by_uuid(doc_uuid)  # 调用仓储查询
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")  # 未命中返回404
    logger.info("get_document_by_uuid uuid=%s", doc_uuid)  # 打印访问日志
    return _build_document_response(doc)  # 返回文档


@router.delete("/documents/by-uuid/{doc_uuid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_by_uuid(doc_uuid: UUID, db: Session = Depends(get_db)):
    """按UUID删除文档，同时依赖外键级联清理chunks。"""
    doc_repo = DocumentRepository(db)
    document = doc_repo.get_by_uuid(doc_uuid)
    if not document:
        logger.info("delete_document_by_uuid idempotent miss uuid=%s", doc_uuid)  # 记录幂等删除
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    chunk_repo = ChunkRepository(db)
    chunks = list(chunk_repo.list_by_document(document.id))
    chunk_ids = [chunk.id for chunk in chunks]
    removed = 0
    if chunk_ids:
        try:
            removed = remove_vectors(chunk_ids)
        except RuntimeError as exc:  # pragma: no cover - 向量服务异常时记录日志并返回
            logger.exception(
                "auto_remove_vectors_failed document_id=%s uuid=%s chunk_count=%s",
                document.id,
                doc_uuid,
                len(chunk_ids),
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=str(exc),
            ) from exc
    db.delete(document)
    db.flush()
    logger.info(
        "delete_document_by_uuid success uuid=%s document_id=%s removed_vectors=%s",
        doc_uuid,
        document.id,
        removed,
    )  # 删除成功日志
    return Response(status_code=status.HTTP_204_NO_CONTENT)  # 幂等策略：无论是否存在都返回204


@router.post(
    "/domains/{domain_id}/documents",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    domain_id: int,
    request: Request,
    db: Session = Depends(get_db),
    title_form: str | None = Form(default=None, alias="title"),
    mode_form: str | None = Form(default=None, alias="mode"),
    content_form: str | None = Form(default=None, alias="content"),
    metadata_form: str | None = Form(default=None, alias="doc_metadata"),
    file: UploadFile | None = File(default=None),
):
    """在指定domain下创建文档并立即生成chunks。"""
    domain_repo = DomainRepository(db)  # 初始化domain仓储
    if not domain_repo.get(domain_id):
        raise HTTPException(status_code=404, detail="domain not found")  # domain不存在直接返回404
    doc_repo = DocumentRepository(db)  # 初始化文档仓储
    content_type = request.headers.get("content-type", "")
    structured_entities = None
    if content_type.startswith("multipart/form-data"):
        title_value = (title_form or "").strip()
        if not title_value:
            raise HTTPException(status_code=422, detail="title is required")
        mode = (mode_form or "text").lower()
        doc_metadata = {}
        raw_content = ""
        if metadata_form:
            try:
                parsed_metadata = json.loads(metadata_form)
                if isinstance(parsed_metadata, dict):
                    doc_metadata = parsed_metadata
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="doc_metadata must be valid JSON")
        if mode == "csv":
            if file is None:
                raise HTTPException(status_code=400, detail="csv file is required")
            raw_bytes = await file.read()
            if not raw_bytes:
                raise HTTPException(status_code=400, detail="csv file is empty")
            try:
                csv_text = raw_bytes.decode("utf-8-sig")
            except UnicodeDecodeError:
                csv_text = raw_bytes.decode("utf-8", errors="ignore")
            structured_entities = parse_structured_entities_from_csv(csv_text)
            if not structured_entities:
                raise HTTPException(status_code=400, detail="csv file has no valid rows")
            raw_content = csv_text
            doc_metadata.update({"type": "structured", "source": "csv"})
        else:
            raw_content = content_form or ""
            if not raw_content.strip():
                raise HTTPException(status_code=400, detail="text content is required")
        title = title_value
    else:
        try:
            payload_data = await request.json()
        except ValueError as exc:  # pragma: no cover - FastAPI会统一处理但做容错
            raise HTTPException(status_code=400, detail="invalid request body") from exc
        payload = DocumentCreate.model_validate(payload_data)
        title = payload.title
        raw_content = payload.content
        doc_metadata = payload.doc_metadata or {}
    doc_metadata = _strip_tags(doc_metadata)
    data = {"title": title, "doc_metadata": doc_metadata, "domain_id": domain_id}
    document = doc_repo.create(**data)  # 创建文档记录
    chunk_texts = make_chunks(
        document,
        raw_content,
        structured_entities=structured_entities,
    )  # 生成chunk文本列表
    chunk_repo = ChunkRepository(db)
    chunks = list(
        chunk_repo.bulk_create_for_document(document.id, chunk_texts)
    )  # 批量写入chunk表
    for chunk in chunks:  # 确保向量写入时能读取domain信息
        chunk.document = document
    try:
        indexed = index_chunks(chunks)
    except RuntimeError as exc:  # pragma: no cover - 向量服务异常时记录日志并返回
        logger.exception(
            "auto_index_document_failed domain=%s document_id=%s uuid=%s",
            domain_id,
            document.id,
            document.uuid,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    logger.info(
        "create_document domain=%s document_id=%s uuid=%s chunk_count=%s indexed=%s",
        domain_id,
        document.id,
        document.uuid,
        len(chunk_texts),
        indexed,
    )  # 记录创建详情
    return _build_document_response(document)  # 返回文档信息


@router.get("/domains/{domain_id}/documents", response_model=List[DocumentOut])
def list_documents_by_domain(domain_id: int, db: Session = Depends(get_db)):
    """列出指定domain下的所有文档。"""
    domain_repo = DomainRepository(db)
    if not domain_repo.get(domain_id):
        raise HTTPException(status_code=404, detail="domain not found")
    logger.info("list_documents_by_domain domain=%s", domain_id)
    documents = DocumentRepository(db).list_with_filters(
        limit=50,
        offset=0,
        sort_by="created_at",
        order="desc",
        domain_id=domain_id,
    )
    return [_build_document_response(doc) for doc in documents]


def _collect_chunks(db: Session, document_id: int) -> List[ChunkOut]:
    """统一获取指定文档的chunk列表。"""
    chunks = ChunkRepository(db).list_by_document(document_id)
    logger.info("collect_chunks doc_id=%s chunk_count=%s", document_id, len(chunks))
    return [ChunkOut.model_validate(chunk) for chunk in chunks]


@router.get("/domains/{domain_id}/documents/{doc_id}", response_model=DocumentOut)
def get_document(domain_id: int, doc_id: int, db: Session = Depends(get_db)):
    """在domain上下文内获取指定文档。"""
    domain_repo = DomainRepository(db)
    if not domain_repo.get(domain_id):
        raise HTTPException(status_code=404, detail="domain not found")
    doc = DocumentRepository(db).get(doc_id)
    if not doc or doc.domain_id != domain_id:
        raise HTTPException(status_code=404, detail="document not found")
    logger.info("get_document domain=%s doc_id=%s", domain_id, doc_id)
    return _build_document_response(doc)


@router.patch("/domains/{domain_id}/documents/{doc_id}", response_model=DocumentOut)
def update_document(domain_id: int, doc_id: int, payload: DocumentUpdate, db: Session = Depends(get_db)):
    """更新文档元信息，不触发重新切分。"""
    domain_repo = DomainRepository(db)
    if not domain_repo.get(domain_id):
        raise HTTPException(status_code=404, detail="domain not found")
    repo = DocumentRepository(db)
    doc = repo.get(doc_id)
    if not doc or doc.domain_id != domain_id:
        raise HTTPException(status_code=404, detail="document not found")
    update_data = payload.model_dump(exclude_none=True)
    if "doc_metadata" in update_data:
        update_data["doc_metadata"] = _strip_tags(update_data["doc_metadata"])
    updated = repo.update(doc, **update_data)
    logger.info("update_document domain=%s doc_id=%s", domain_id, doc_id)
    return _build_document_response(updated)


@router.delete("/domains/{domain_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(domain_id: int, doc_id: int, db: Session = Depends(get_db)):
    """删除指定domain下的文档。"""
    domain_repo = DomainRepository(db)
    if not domain_repo.get(domain_id):
        raise HTTPException(status_code=404, detail="domain not found")
    repo = DocumentRepository(db)
    doc = repo.get(doc_id)
    if not doc or doc.domain_id != domain_id:
        raise HTTPException(status_code=404, detail="document not found")
    repo.delete(doc_id)
    logger.info("delete_document domain=%s doc_id=%s", domain_id, doc_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/domains/{domain_id}/documents/{doc_id}/chunks",
    response_model=List[ChunkOut],
    deprecated=True,
)
def list_chunks(domain_id: int, doc_id: int, db: Session = Depends(get_db)):
    """获取指定文档的chunk列表（推荐使用新路径）。"""
    domain_repo = DomainRepository(db)
    if not domain_repo.get(domain_id):
        raise HTTPException(status_code=404, detail="domain not found")
    doc = DocumentRepository(db).get(doc_id)
    if not doc or doc.domain_id != domain_id:
        raise HTTPException(status_code=404, detail="document not found")
    return _collect_chunks(db, doc_id)



@router.get("/documents/{doc_id}/chunks", response_model=List[ChunkOut])
def list_chunks_by_document_id(doc_id: int, db: Session = Depends(get_db)):
    """通过文档ID获取chunk列表。"""
    doc = DocumentRepository(db).get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    return _collect_chunks(db, doc_id)


@router.get("/documents/by-uuid/{doc_uuid}/chunks", response_model=List[ChunkOut])
def list_chunks_by_document_uuid(doc_uuid: UUID, db: Session = Depends(get_db)):
    """通过文档UUID获取chunk列表。"""
    doc = DocumentRepository(db).get_by_uuid(doc_uuid)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    return _collect_chunks(db, doc.id)



@router.post(
    "/domains/{domain_id}/documents/{doc_id}/chunks",
    deprecated=True,
    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
)
def create_chunk_manual(*_, **__):
    """提示用户chunk只能自动生成。"""
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="chunk are generated automatically and cannot be created manually",
    )


@router.patch(
    "/domains/{domain_id}/documents/{doc_id}/chunks/{chunk_id}",
    deprecated=True,
    status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
)
def update_chunk_manual(*_, **__):
    """提示用户chunk禁止修改。"""
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="chunk modification is disabled to keep consistency with source content",
    )
