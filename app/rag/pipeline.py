"""Core retrieval-augmented generation pipeline."""
from __future__ import annotations

import logging
from typing import Sequence

from app.services.ollama import get_ollama_client
from app.services.qdrant_client import get_vector_store

from . import prompt
from .types import RagResult, RetrievedChunk

logger = logging.getLogger(__name__)


class RAGPipeline:
    """A simple pipeline that embeds a question, retrieves context and calls the LLM."""

    def __init__(
        self,
        *,
        top_k: int = 5,
    ) -> None:
        self.top_k = top_k

    def run(self, question: str, *, top_k: int | None = None) -> RagResult:
        """Execute the full RAG workflow for a question."""

        if not question.strip():
            raise ValueError("question must not be empty")
        ollama = get_ollama_client()
        store = get_vector_store()
        logger.debug("embedding question with ollama")
        question_embedding = ollama.embed([question])[0]
        logger.debug("retrieving top_k=%s from qdrant", top_k or self.top_k)
        retrieved = store.search(question_embedding, limit=top_k or self.top_k)
        messages = prompt.build_messages(question, retrieved)
        logger.debug("calling ollama chat with %s messages", len(messages))
        answer = ollama.chat(messages)
        return RagResult(answer=answer, sources=retrieved)

    @staticmethod
    def build_metadata(sources: Sequence[RetrievedChunk]) -> dict[str, list[dict[str, object]]]:
        """Serialize retrieved sources into message metadata payload."""

        return {"sources": [source.to_source_metadata() for source in sources]}

