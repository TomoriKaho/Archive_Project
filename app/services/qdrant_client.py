"""Wrapper utilities for interacting with a Qdrant vector database."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable, Sequence

from dotenv import find_dotenv, load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.models.entities import Chunk, Document
from app.rag.types import RetrievedChunk

load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class QdrantSettings:
    collection_name: str
    vector_size: int
    distance: qmodels.Distance = qmodels.Distance.COSINE


class QdrantVectorStore:
    """High level helper around Qdrant client for document chunk operations."""

    def __init__(self, client: QdrantClient, settings: QdrantSettings) -> None:
        self.client = client
        self.settings = settings

    def ensure_collection(self) -> None:
        """Ensure the configured collection exists with basic payload schema."""

        collection = self.settings.collection_name
        if self.client.collection_exists(collection):
            logger.debug("qdrant collection already exists name=%s", collection)
            return
        logger.info("creating qdrant collection name=%s", collection)
        vectors_config = qmodels.VectorParams(size=self.settings.vector_size, distance=self.settings.distance)
        self.client.create_collection(
            collection_name=collection,
            vectors_config=vectors_config,
        )
        # Declare payload schema for frequently filtered fields.
        payload_schema = {
            "document_id": qmodels.PayloadSchemaType.INTEGER,
            "document_uuid": qmodels.PayloadSchemaType.KEYWORD,
            "document_title": qmodels.PayloadSchemaType.TEXT,
            "chunk_ordinal": qmodels.PayloadSchemaType.INTEGER,
            "chunk_text": qmodels.PayloadSchemaType.TEXT,
            "chunk_id": qmodels.PayloadSchemaType.KEYWORD,
            "domain_id": qmodels.PayloadSchemaType.INTEGER,
        }
        self.client.create_payload_index(collection, field_name="document_id", field_schema=payload_schema["document_id"])
        self.client.create_payload_index(collection, field_name="document_uuid", field_schema=payload_schema["document_uuid"])
        self.client.create_payload_index(collection, field_name="domain_id", field_schema=payload_schema["domain_id"])
        logger.info("qdrant collection created name=%s vector_size=%s", collection, self.settings.vector_size)

    def upsert_document_chunks(
        self,
        document: Document,
        chunks: Sequence[Chunk],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        """Upsert embeddings for the provided document chunks."""

        if not chunks:
            return
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings length mismatch")
        points: list[qmodels.PointStruct] = []
        for chunk, vector in zip(chunks, embeddings):
            if not vector:
                logger.warning("skip empty embedding chunk_id=%s", chunk.external_id)
                continue
            payload = {
                "document_id": chunk.document_id,
                "document_uuid": str(document.uuid),
                "document_title": document.title,
                "chunk_ordinal": chunk.ordinal,
                "chunk_text": chunk.content,
                "chunk_id": chunk.external_id,
                "domain_id": document.domain_id,
            }
            point = qmodels.PointStruct(id=chunk.external_id, vector=list(vector), payload=payload)
            points.append(point)
        if not points:
            logger.info("no embeddings generated for document=%s", document.id)
            return
        self.client.upsert(collection_name=self.settings.collection_name, points=points)
        logger.info("upserted %s chunk vectors into qdrant", len(points))

    def delete_chunks_by_document_uuid(self, document_uuid: str) -> None:
        """Delete all vectors belonging to the specified document."""

        condition = qmodels.FieldCondition(
            key="document_uuid",
            match=qmodels.MatchValue(value=document_uuid),
        )
        flt = qmodels.Filter(must=[condition])
        self.client.delete(collection_name=self.settings.collection_name, points_selector=flt)
        logger.info("deleted qdrant vectors for document_uuid=%s", document_uuid)

    def delete_chunks_by_ids(self, chunk_external_ids: Iterable[str]) -> None:
        """Delete vectors by their chunk external ids."""

        ids = [cid for cid in chunk_external_ids]
        if not ids:
            return
        self.client.delete(collection_name=self.settings.collection_name, points_selector=qmodels.PointIdsList(points=ids))
        logger.info("deleted %s qdrant vectors", len(ids))

    def search(self, embedding: Sequence[float], limit: int = 5) -> list[RetrievedChunk]:
        """Perform a similarity search and return retrieved chunks."""

        results = self.client.search(
            collection_name=self.settings.collection_name,
            query_vector=list(embedding),
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        retrieved: list[RetrievedChunk] = []
        for result in results:
            payload = result.payload or {}
            chunk_id = payload.get("chunk_id")
            if not chunk_id:
                continue
            retrieved.append(
                RetrievedChunk(
                    chunk_id=str(chunk_id),
                    document_id=int(payload.get("document_id", 0)),
                    document_uuid=str(payload.get("document_uuid")),
                    document_title=str(payload.get("document_title", "")),
                    chunk_ordinal=int(payload.get("chunk_ordinal", 0)),
                    content=str(payload.get("chunk_text", "")),
                    score=float(result.score or 0.0),
                )
            )
        return retrieved


def _build_qdrant_client() -> QdrantClient:
    url = os.getenv("QDRANT_URL")
    api_key = os.getenv("QDRANT_API_KEY")
    prefer_grpc = os.getenv("QDRANT_PREFER_GRPC", "false").lower() == "true"
    if url:
        logger.info("connecting to qdrant via url=%s", url)
        return QdrantClient(url=url, api_key=api_key, prefer_grpc=prefer_grpc)
    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    logger.info("connecting to qdrant host=%s port=%s", host, port)
    return QdrantClient(host=host, port=port, api_key=api_key, prefer_grpc=prefer_grpc)


@lru_cache(maxsize=1)
def get_vector_store() -> QdrantVectorStore:
    """Return a cached QdrantVectorStore instance."""

    collection = os.getenv("QDRANT_COLLECTION", "document_chunks")
    vector_size = int(os.getenv("QDRANT_VECTOR_SIZE", "4096"))
    settings = QdrantSettings(collection_name=collection, vector_size=vector_size)
    store = QdrantVectorStore(client=_build_qdrant_client(), settings=settings)
    store.ensure_collection()
    return store

