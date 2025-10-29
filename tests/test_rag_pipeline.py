import pytest

from app.rag.pipeline import RAGPipeline
from app.rag.types import RetrievedChunk


class DummyOllama:
    def __init__(self):
        self.embedded = []
        self.chats = []

    def embed(self, texts):
        self.embedded.extend(texts)
        return [[0.1, 0.2, 0.3]]

    def chat(self, messages):
        self.chats.append(messages)
        return "answer"


class DummyVectorStore:
    def __init__(self, results):
        self.results = results

    def search(self, embedding, limit=5):  # noqa: ARG002
        return self.results


def test_pipeline_run(monkeypatch):
    sources = [
        RetrievedChunk(
            chunk_id="chunk-1",
            document_id=1,
            document_uuid="uuid-1",
            document_title="Doc",
            chunk_ordinal=0,
            content="context",
            score=0.9,
        )
    ]
    dummy_ollama = DummyOllama()
    dummy_store = DummyVectorStore(sources)
    monkeypatch.setattr("app.rag.pipeline.get_ollama_client", lambda: dummy_ollama)
    monkeypatch.setattr("app.rag.pipeline.get_vector_store", lambda: dummy_store)
    pipeline = RAGPipeline(top_k=3)
    result = pipeline.run("question?")
    assert result.answer == "answer"
    assert result.sources == sources
    metadata = pipeline.build_metadata(result.sources)
    assert metadata["sources"][0]["chunk_id"] == "chunk-1"
    assert dummy_ollama.embedded == ["question?"]


def test_pipeline_rejects_empty_question():
    pipeline = RAGPipeline()
    with pytest.raises(ValueError):
        pipeline.run("   ")
