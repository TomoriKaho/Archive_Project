from types import SimpleNamespace
from unittest.mock import ANY, MagicMock

import pytest
from types import SimpleNamespace
from unittest.mock import ANY, MagicMock
from app.services.qdrant_client import QdrantSettings, QdrantVectorStore
from app.rag.types import RetrievedChunk


def make_store(client=None, vector_size=3):
    client = client or MagicMock()
    settings = QdrantSettings(collection_name="test", vector_size=vector_size)
    return QdrantVectorStore(client=client, settings=settings)


def test_ensure_collection_creates_when_missing():
    client = MagicMock()
    client.collection_exists.return_value = False
    store = make_store(client)
    store.ensure_collection()
    client.create_collection.assert_called_once()
    client.create_payload_index.assert_any_call("test", field_name="document_id", field_schema=ANY)


def test_upsert_document_chunks_builds_points():
    client = MagicMock()
    store = make_store(client)
    document = SimpleNamespace(id=1, uuid="doc-1", title="Doc", domain_id=2)
    chunk = SimpleNamespace(document_id=1, external_id="chunk-1", ordinal=0, content="hello world")
    store.upsert_document_chunks(document, [chunk], [[0.1, 0.2, 0.3]])
    client.upsert.assert_called_once()
    points = client.upsert.call_args.kwargs["points"]
    assert points[0].payload["chunk_id"] == "chunk-1"


def test_search_returns_retrieved_chunks():
    client = MagicMock()
    store = make_store(client)
    client.search.return_value = [
        SimpleNamespace(
            payload={
                "chunk_id": "chunk-42",
                "document_id": 1,
                "document_uuid": "uuid-1",
                "document_title": "Doc",
                "chunk_ordinal": 0,
                "chunk_text": "snippet",
            },
            score=0.75,
        )
    ]
    results = store.search([0.1, 0.2, 0.3])
    assert results == [
        RetrievedChunk(
            chunk_id="chunk-42",
            document_id=1,
            document_uuid="uuid-1",
            document_title="Doc",
            chunk_ordinal=0,
            content="snippet",
            score=0.75,
        )
    ]
