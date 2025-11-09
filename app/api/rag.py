"""RAG ingestion and query endpoints."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.entities import User
from app.repositories.chat_repo import ChatRepository
from app.repositories.chunk_repo import ChunkRepository
from app.repositories.document_repo import DocumentRepository
from app.repositories.message_repo import MessageRepository
from app.schemas.message import MessageOut
from app.schemas.rag import AskRequest, AskResponse, PreviewItem, Reference
from app.services.rag_conversation import answer_with_history
from app.services.rag_service import DEFAULT_TOP_K, index_chunks, retrieve_with_scores

logger = logging.getLogger(__name__)

router = APIRouter(tags=["rag"])


@router.post("/rag/ingest/{document_id}")
def ingest_document(
    document_id: int,
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Embed all chunks for a document and push them into Qdrant."""

    document = DocumentRepository(db).get(document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document not found")
    chunks = list(ChunkRepository(db).list_by_document(document_id))
    try:
        indexed = index_chunks(chunks)
    except RuntimeError as exc:
        logger.exception("ingest chunks failed: document_id=%s", document_id)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return {
        "document_id": document_id,
        "total_chunks": len(chunks),
        "indexed": indexed,
    }


@router.post("/chats/{chat_id}/ask", response_model=AskResponse)
def ask_in_chat(
    chat_id: int,
    payload: AskRequest,
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Store the user question, run RAG, and persist the assistant reply."""

    chat = ChatRepository(db).get(chat_id)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="chat not found")
    if chat.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="chat access denied")
    message_repo = MessageRepository(db)
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="question cannot be empty")
    message_repo.create(chat_id=chat_id, role="user", content=question)
    domain_ids = sorted(set(payload.domain_ids)) if payload.domain_ids else None
    top_k = payload.top_k or DEFAULT_TOP_K
    try:
        answer_text, references = answer_with_history(
            chat_id,
            question,
            domain_ids,
            db=db,
            top_k=top_k,
        )
    except RuntimeError as exc:
        logger.exception("rag answer failed: chat_id=%s", chat_id)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    assistant = message_repo.create(chat_id=chat_id, role="assistant", content=answer_text)
    base = MessageOut.model_validate(assistant)
    return AskResponse(
        **base.model_dump(),
        references=[Reference(chunk_id=cid, score=score) for cid, score in references],
    )


@router.get("/rag/preview", response_model=list[PreviewItem])
def preview_retrieval(
    q: str = Query(..., min_length=1, description="待检索的问题"),
    top_k: int = Query(DEFAULT_TOP_K, ge=1, le=100, description="返回的 chunk 数量"),
    domain_id: int | None = Query(None, description="可选的 domain 过滤"),
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Preview chunks fetched by RAG search for debugging purposes."""

    domain_ids = [domain_id] if domain_id is not None else None
    try:
        chunks, references = retrieve_with_scores(q.strip(), top_k, domain_ids, db=db)
    except RuntimeError as exc:
        logger.exception("rag preview failed")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    score_map = {chunk_id: score for chunk_id, score in references}
    previews: list[PreviewItem] = []
    for chunk in chunks:
        previews.append(
            PreviewItem(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                domain_id=chunk.document.domain_id if chunk.document else None,
                score=score_map.get(chunk.id, 0.0),
                content_preview=chunk.content[:200],
            )
        )
    return previews
