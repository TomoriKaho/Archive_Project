"""Shared dataclasses used by the RAG pipeline."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class RetrievedChunk:
    chunk_id: str
    document_id: int
    document_uuid: str
    document_title: str
    chunk_ordinal: int
    content: str
    score: float

    def to_source_metadata(self) -> dict[str, Any]:
        """Return a dictionary representation safe for JSON serialization."""

        return asdict(self)


@dataclass(slots=True)
class RagResult:
    answer: str
    sources: list[RetrievedChunk]

