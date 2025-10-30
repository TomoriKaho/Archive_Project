"""面向前端的 RAG 查询接口。"""
from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.repositories.chunk_repo import ChunkRepository
from app.schemas.rag import RagHit, RagQueryRequest, RagQueryResponse
from app.services.rag import ContextChunk, RagConfigurationError, get_rag_service

router = APIRouter(prefix="/rag", tags=["rag"])
logger = logging.getLogger(__name__)


@router.post("/query", response_model=RagQueryResponse)
def query_rag(payload: RagQueryRequest, db: Session = Depends(get_db)) -> RagQueryResponse:
    """执行一次检索增强问答流程。"""

    try:
        service = get_rag_service()
    except RagConfigurationError as exc:
        logger.exception("rag_query configuration_error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    repo = ChunkRepository(db)
    vector_limit = max(payload.top_k * 4, payload.top_k)

    try:
        vector_hits = service.vector_search(payload.question, limit=vector_limit)
    except Exception as exc:  # pragma: no cover - 网络或服务异常
        logger.exception("rag_query vector_search_failed")
        raise HTTPException(
            status_code=502,
            detail="vector search failed",
        ) from exc

    external_ids = [hit.external_id for hit in vector_hits]
    chunk_map = dict(repo.map_by_external_ids(external_ids))

    hits: List[RagHit] = []
    contexts: List[ContextChunk] = []

    for hit in vector_hits:
        chunk = chunk_map.get(hit.external_id)
        if not chunk:
            continue
        document = chunk.document
        if payload.domain_id is not None and document.domain_id != payload.domain_id:
            continue

        hits.append(
            RagHit(
                chunk_id=chunk.id,
                external_id=chunk.external_id,
                document_id=chunk.document_id,
                document_title=document.title,
                domain_id=document.domain_id,
                ordinal=chunk.ordinal,
                content=chunk.content,
                score=hit.score,
            )
        )
        contexts.append(
            ContextChunk(
                external_id=chunk.external_id,
                label=f"{document.title} · chunk#{chunk.ordinal}",
                content=chunk.content,
                score=hit.score,
            )
        )
        if len(hits) >= payload.top_k:
            break

    try:
        answer = service.build_answer(payload.question, contexts)
    except Exception as exc:  # pragma: no cover - 网络或服务异常
        logger.exception("rag_query chat_failed")
        raise HTTPException(
            status_code=502,
            detail="failed to generate answer",
        ) from exc

    return RagQueryResponse(answer=answer, hits=hits)

