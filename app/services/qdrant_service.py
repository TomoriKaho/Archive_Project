"""Minimal HTTP client helpers for interacting with Qdrant."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any
from urllib import error, request

logger = logging.getLogger(__name__)


QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
"""Base URL for the Qdrant service."""

QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "Archive_Project_Collection")
"""Target collection name that stores chunk vectors."""

RAG_OLLAMA_TIMEOUT = int(os.getenv("RAG_OLLAMA_TIMEOUT", "60"))
"""Timeout shared with Ollama settings for outbound HTTP requests."""


@dataclass
class _QdrantHttpClient:
    """Lightweight wrapper storing base URL and timeout."""

    base_url: str
    timeout: int

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None, *, allow_404: bool = False) -> tuple[int, Any]:
        """Send an HTTP request to Qdrant and return status code plus JSON body."""

        url = f"{self.base_url.rstrip('/')}{path}"
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = request.Request(
            url=url,
            data=data,
            headers={"Content-Type": "application/json"},
            method=method,
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
                body = json.loads(raw.decode("utf-8")) if raw else None
                return resp.status, body
        except error.HTTPError as exc:
            raw_error = exc.read().decode("utf-8", "ignore")
            if exc.code == 404 and allow_404:
                return exc.code, None
            logger.error("Qdrant 请求失败 %s %s: %s", method, path, raw_error)
            raise RuntimeError("qdrant request failed") from exc
        except error.URLError as exc:
            logger.error("无法连接到 Qdrant 服务: %s", exc)
            raise RuntimeError("unable to reach qdrant") from exc


_client: _QdrantHttpClient | None = None


def get_client() -> _QdrantHttpClient:
    """Return a cached HTTP client configured from environment variables."""

    global _client
    if _client is None:
        _client = _QdrantHttpClient(base_url=QDRANT_URL, timeout=RAG_OLLAMA_TIMEOUT)
    return _client


def ensure_collection(dim: int) -> None:
    """Ensure the configured collection exists with the expected vector dimension."""

    client = get_client()
    status, body = client.request("GET", f"/collections/{QDRANT_COLLECTION}", allow_404=True)
    if status == 200:
        vectors_cfg = (
            body.get("result", {})
            .get("config", {})
            .get("params", {})
            .get("vectors", {})
            if isinstance(body, dict)
            else {}
        )
        current_dim = vectors_cfg.get("size")
        if current_dim == dim:
            return  # 维度匹配，直接复用现有集合
        # 维度不匹配需要重建集合以避免插入失败
        client.request("DELETE", f"/collections/{QDRANT_COLLECTION}")
        status = 404  # 删除后按不存在处理，方便重新创建
    if status != 404:
        raise RuntimeError("unexpected response when checking qdrant collection")
    payload = {
        "vectors": {
            "size": dim,
            "distance": "Cosine",
        }
    }
    client.request("PUT", f"/collections/{QDRANT_COLLECTION}", payload)


def upsert_vectors(point_ids: list[int], vectors: list[list[float]]) -> None:
    """Upsert points into Qdrant with chunk ids as vector identifiers."""

    if not point_ids:
        return
    if len(point_ids) != len(vectors):
        raise ValueError("point ids and vectors length mismatch")
    client = get_client()
    points = [{"id": int(pid), "vector": vec} for pid, vec in zip(point_ids, vectors)]
    payload = {"points": points, "wait": True}
    client.request("PUT", f"/collections/{QDRANT_COLLECTION}/points", payload)


def search(query_vec: list[float], top_k: int) -> list[int]:
    """Search the configured Qdrant collection and return chunk ids ordered by similarity."""

    results = search_with_scores(query_vec, top_k)
    return [chunk_id for chunk_id, _ in results]


def search_with_scores(query_vec: list[float], top_k: int) -> list[tuple[int, float]]:
    """Perform a vector similarity search and keep similarity scores."""

    client = get_client()
    payload = {"vector": query_vec, "limit": top_k}
    _, body = client.request("POST", f"/collections/{QDRANT_COLLECTION}/points/search", payload)
    points = body.get("result", []) if isinstance(body, dict) else []
    ordered: list[tuple[int, float]] = []
    for point in points:
        point_id = point.get("id")
        score = point.get("score")
        if point_id is None or score is None:
            continue
        ordered.append((int(point_id), float(score)))
    return ordered
