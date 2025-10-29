"""Document chunk indexing pipeline."""
from __future__ import annotations

import logging
from typing import Sequence

from app.models.entities import Chunk, Document
from app.services.ollama import get_ollama_client
from app.services.qdrant_client import get_vector_store

logger = logging.getLogger(__name__)


def index_document_chunks(document: Document, chunks: Sequence[Chunk]) -> None:
    """Generate embeddings for document chunks and store them in Qdrant."""

    if not chunks:
        logger.info("document id=%s has no chunks to index", document.id)
        return
    ollama = get_ollama_client()
    store = get_vector_store()
    logger.info("indexing %s chunks for document id=%s", len(chunks), document.id)
    texts = [chunk.content for chunk in chunks]
    embeddings = ollama.embed(texts)
    store.upsert_document_chunks(document, chunks, embeddings)

