"""Schemas dedicated to RAG endpoints."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from .message import MessageOut


class AskRequest(BaseModel):
    """Incoming payload for /chats/{chat_id}/ask endpoint."""

    question: str = Field(..., min_length=1, description="用户提出的问题")
    top_k: int | None = Field(None, ge=1, le=100, description="召回的 chunk 数量")
    domain_ids: List[int] | None = Field(None, description="限制可用的 domain 列表")


class Reference(BaseModel):
    """Simple reference entry linking answer back to chunk id and similarity score."""

    chunk_id: int
    score: float


class AskResponse(MessageOut):
    """Assistant message augmented with source references."""

    references: List[Reference] = Field(default_factory=list)


class PreviewItem(BaseModel):
    """Preview of retrieved chunks for debug endpoint."""

    chunk_id: int
    document_id: int
    domain_id: int | None
    score: float
    content_preview: str
