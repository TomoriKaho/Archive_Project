"""文档与chunk相关的REST接口。"""
from __future__ import annotations  # 允许前置类型注解

import logging  # 统一日志输出
from typing import List, Literal, Optional  # 类型注解
from uuid import UUID  # 使用UUID匹配数据库字段

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status  # FastAPI核心组件
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
from app.services.chunking import make_chunks  # 文档切分服务
from app.services.rag import RagConfigurationError, get_rag_service  # RAG 索引服务

router = APIRouter(tags=["documents"])  # 声明文档相关路由
logger = logging.getLogger(__name__)  # 初始化模块级日志


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(
    domain_id: Optional[int] = Query(default=None, description="按domain过滤，缺省返回全量"),  # 可选domain过滤
    limit: int = Query(20, ge=1, le=100, description="单页数量，最大100以避免全表扫描"),  # 限制单次查询量
    offset: int = Query(0, ge=0, description="分页偏移量，从0开始"),  # 偏移量
    sort_by: Literal["created_at", "title"] = Query(
        "created_at",
        description="排序字段，可选created_at或title",
    ),  # 枚举校验排序字段
    order: Literal["asc", "desc"] = Query(
        "desc",
        description="排序方向，可选asc或desc",
    ),  # 枚举校验排序方向
    db: Session = Depends(get_db),  # 注入数据库会话
):
    """获取文档列表，支持分页与排序。"""
    doc_repo = DocumentRepository(db)  # 初始化仓储
    items = doc_repo.list_with_filters(
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        order=order,
        domain_id=domain_id,
    )  # 查询数据
    total = doc_repo.count_with_filters(domain_id=domain_id)  # 计算总量
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
        items=[DocumentOut.model_validate(item) for item in items],
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
    return doc  # 返回文档


@router.delete("/documents/by-uuid/{doc_uuid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_by_uuid(doc_uuid: UUID, db: Session = Depends(get_db)):
    """按UUID删除文档，同时依赖外键级联清理chunks。"""
    deleted = DocumentRepository(db).delete_by_uuid(doc_uuid)  # 先删后看结果
    if not deleted:
        logger.info("delete_document_by_uuid idempotent miss uuid=%s", doc_uuid)  # 记录幂等删除
    else:
        logger.info("delete_document_by_uuid success uuid=%s", doc_uuid)  # 删除成功日志
    return Response(status_code=status.HTTP_204_NO_CONTENT)  # 幂等策略：无论是否存在都返回204


@router.post("/domains/{domain_id}/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def create_document(domain_id: int, payload: DocumentCreate, db: Session = Depends(get_db)):
    """在指定domain下创建文档并立即生成chunks。"""
    domain_repo = DomainRepository(db)  # 初始化domain仓储
    if not domain_repo.get(domain_id):
        raise HTTPException(status_code=404, detail="domain not found")  # domain不存在直接返回404
    doc_repo = DocumentRepository(db)  # 初始化文档仓储
    data = payload.model_dump()  # 转换为字典便于拆分
    raw_content = data.pop("content")  # 取出原始内容用于切分
    data["domain_id"] = domain_id  # 写入所属domain
    document = doc_repo.create(**data)  # 创建文档记录
    chunk_texts = make_chunks(document, raw_content)  # 生成chunk文本列表
    chunk_repo = ChunkRepository(db)
    chunks = chunk_repo.bulk_create_for_document(document.id, chunk_texts)  # 批量写入chunk表
    try:
        rag_pairs = [(chunk.external_id, chunk.content) for chunk in chunks]
        get_rag_service().index_chunks(rag_pairs)
    except RagConfigurationError as exc:  # 明确配置缺失
        logger.exception("create_document rag_configuration_error document_id=%s", document.id)
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc
    except Exception as exc:  # pragma: no cover - 网络错误等不可预测情况
        logger.exception("create_document rag_index_failed document_id=%s", document.id)
        raise HTTPException(
            status_code=500,
            detail="failed to index document chunks into vector store",
        ) from exc
    logger.info(
        "create_document domain=%s document_id=%s uuid=%s chunk_count=%s",
        domain_id,
        document.id,
        document.uuid,
        len(chunk_texts),
    )  # 记录创建详情
    return document  # 返回文档信息


@router.get("/domains/{domain_id}/documents", response_model=List[DocumentOut])
def list_documents_by_domain(domain_id: int, db: Session = Depends(get_db)):
    """列出指定domain下的所有文档。"""
    domain_repo = DomainRepository(db)
    if not domain_repo.get(domain_id):
        raise HTTPException(status_code=404, detail="domain not found")
    logger.info("list_documents_by_domain domain=%s", domain_id)
    return DocumentRepository(db).list_with_filters(
        limit=50,
        offset=0,
        sort_by="created_at",
        order="desc",
        domain_id=domain_id,
    )


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
    return doc


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
    updated = repo.update(doc, **payload.model_dump(exclude_none=True))
    logger.info("update_document domain=%s doc_id=%s", domain_id, doc_id)
    return updated


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
