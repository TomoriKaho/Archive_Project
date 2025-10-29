"""Schemas describing responses from the RAG pipeline."""
from __future__ import annotations

from .base import ORMModel
from .message import MessageOut


class RagSource(ORMModel):
    chunk_id: str
    document_id: int
    document_uuid: str
    document_title: str
    chunk_ordinal: int
    content: str
    score: float


class RagMessageResponse(ORMModel):
    question: MessageOut
    answer: MessageOut
    sources: list[RagSource]

