import pytest

from app.services.ollama import OllamaClient


class FakeResponse:
    def __init__(self, json_data=None, status_code=200):
        self._json = json_data or {}
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")

    def json(self):
        return self._json


class FakeClient:
    def __init__(self, handler):
        self.handler = handler

    def post(self, path, json=None):
        return self.handler(path, json)

    def close(self):  # pragma: no cover - compatibility shim
        pass


def test_embed_returns_vectors():
    calls = []

    def handler(path, payload):
        calls.append({"path": path, "payload": payload})
        return FakeResponse({"embedding": [0.1, 0.2]})

    client = OllamaClient(http_client=FakeClient(handler))
    result = client.embed(["hello"])
    assert result == [[0.1, 0.2]]
    assert calls[0]["payload"]["input"] == "hello"


def test_chat_returns_response():
    def handler(path, payload):
        assert path.endswith("/api/chat")
        assert payload["messages"][-1]["role"] == "user"
        return FakeResponse({"message": {"content": "hi"}})

    client = OllamaClient(http_client=FakeClient(handler))
    message = client.chat([{"role": "user", "content": "hello"}])
    assert message == "hi"


def test_embed_raises_on_missing_embedding():
    def handler(path, payload):
        return FakeResponse({})

    client = OllamaClient(http_client=FakeClient(handler))
    with pytest.raises(RuntimeError):
        client.embed(["oops"])
