"""Utilities to interact with an Ollama instance for embeddings and chat."""
from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from typing import Iterable, Sequence

try:  # pragma: no cover - optional dependency resolution
    import httpx  # type: ignore
except ImportError as exc:  # pragma: no cover - fallback for tests
    httpx = None  # type: ignore
    _HTTPX_IMPORT_ERROR = exc
else:  # pragma: no cover - executed in production when httpx is available
    _HTTPX_IMPORT_ERROR = None
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)


class OllamaClient:
    """Small sync client around Ollama's HTTP API."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        embed_model: str | None = None,
        chat_model: str | None = None,
        timeout: float | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.embed_model = embed_model or os.getenv("OLLAMA_EMBED_MODEL", "llama2")
        self.chat_model = chat_model or os.getenv("OLLAMA_CHAT_MODEL", os.getenv("OLLAMA_MODEL", "llama2"))
        timeout_value = timeout or float(os.getenv("OLLAMA_TIMEOUT", "60"))
        if http_client is not None:
            self._client = http_client
        else:
            if httpx is None:
                raise RuntimeError("httpx is required unless a custom http_client is provided") from _HTTPX_IMPORT_ERROR
            self._client = httpx.Client(base_url=self.base_url, timeout=timeout_value)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Generate embeddings for the provided texts using the configured model."""

        embeddings: list[list[float]] = []
        for text in texts:
            if not text:
                embeddings.append([])
                continue
            payload = {"model": self.embed_model, "input": text}
            logger.debug("ollama.embed payload=%s", payload)
            response = self._client.post("/api/embeddings", json=payload)
            try:
                response.raise_for_status()
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.exception("ollama embeddings request failed")
                raise RuntimeError("failed to generate embeddings from Ollama") from exc
            data = response.json()
            embedding = data.get("embedding")
            if not isinstance(embedding, list):
                raise RuntimeError("ollama embeddings response missing 'embedding'")
            embeddings.append(embedding)
        return embeddings

    def chat(self, messages: Iterable[dict[str, str]]) -> str:
        """Send chat messages to Ollama and return the final response text."""

        payload = {"model": self.chat_model, "messages": list(messages), "stream": False}
        logger.debug("ollama.chat payload=%s", json.dumps(payload, ensure_ascii=False))
        response = self._client.post("/api/chat", json=payload)
        try:
            response.raise_for_status()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("ollama chat request failed")
            raise RuntimeError("failed to request chat completion from Ollama") from exc
        data = response.json()
        message = data.get("message") or {}
        content = message.get("content")
        if not isinstance(content, str):
            raise RuntimeError("ollama chat response missing content")
        return content


@lru_cache(maxsize=1)
def get_ollama_client() -> OllamaClient:
    """Return a cached Ollama client instance."""

    client = OllamaClient()
    logger.info(
        "ollama client initialized base_url=%s embed_model=%s chat_model=%s",
        client.base_url,
        client.embed_model,
        client.chat_model,
    )
    return client

