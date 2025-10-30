"""Tests for the lightweight Qdrant HTTP helper module."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

import app.services.qdrant_service as qdrant_service


class DummyClient:
    """Stub HTTP client returning canned responses."""

    def __init__(self, status: int, body):
        self.calls: list[tuple[str, str, dict | None]] = []
        self._status = status
        self._body = body

    def request(self, method: str, path: str, payload=None, *, allow_404: bool = False):
        self.calls.append((method, path, payload))
        return self._status, self._body


def test_search_with_scores_handles_missing_collection(monkeypatch):
    """A 404 response from Qdrant should be treated as empty result set."""

    dummy = DummyClient(status=404, body=None)
    monkeypatch.setattr(qdrant_service, "_client", dummy)
    results = qdrant_service.search_with_scores([0.1, 0.2], top_k=5)
    assert results == []
    assert dummy.calls == [
        (
            "POST",
            f"/collections/{qdrant_service.QDRANT_COLLECTION}/points/search",
            {"vector": [0.1, 0.2], "limit": 5},
        )
    ]


def test_search_with_scores_applies_domain_filter(monkeypatch):
    """Domain filters should be forwarded to Qdrant using match-any semantics."""

    dummy = DummyClient(status=200, body={"result": []})
    monkeypatch.setattr(qdrant_service, "_client", dummy)
    qdrant_service.search_with_scores([0.3, 0.4], top_k=3, domain_ids=[2, 2, 7])
    assert dummy.calls == [
        (
            "POST",
            f"/collections/{qdrant_service.QDRANT_COLLECTION}/points/search",
            {
                "vector": [0.3, 0.4],
                "limit": 3,
                "filter": {
                    "must": [
                        {
                            "key": "domain_id",
                            "match": {
                                "any": [2, 7],
                            },
                        }
                    ]
                },
            },
        )
    ]
