"""轻量级 RAG 服务：负责向量化、写入 Qdrant 以及基于上下文的回答。"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import List, Sequence

import requests
from dotenv import find_dotenv, load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

load_dotenv(find_dotenv())  # 在模块加载时读取 .env，保持与数据库配置一致

logger = logging.getLogger(__name__)


class RagConfigurationError(RuntimeError):
    """配置缺失时抛出的异常，便于调用方捕获并提示。"""


@dataclass
class VectorHit:
    """向量检索返回的最小单元。"""

    external_id: str
    score: float


@dataclass
class ContextChunk:
    """构建回答时需要的上下文信息。"""

    external_id: str
    label: str
    content: str
    score: float


class RagService:
    """封装 Qdrant 与 Ollama 交互，提供索引与问答能力。"""

    def __init__(self) -> None:
        self.qdrant_url = os.getenv("QDRANT_URL")
        self.collection_name = os.getenv("QDRANT_COLLECTION", "archives_chunks")
        self.ollama_url = os.getenv("OLLAMA_URL")
        self.embed_model = os.getenv("OLLAMA_EMBED_MODEL")
        self.chat_model = os.getenv("OLLAMA_CHAT_MODEL")

        missing: list[str] = []
        if not self.qdrant_url:
            missing.append("QDRANT_URL")
        if not self.ollama_url:
            missing.append("OLLAMA_URL")
        if not self.embed_model:
            missing.append("OLLAMA_EMBED_MODEL")
        if not self.chat_model:
            missing.append("OLLAMA_CHAT_MODEL")
        if missing:
            raise RagConfigurationError(
                "Missing env var(s): " + ", ".join(missing)
            )

        self._requests = requests.Session()
        self._client: QdrantClient | None = None
        self._collection_checked = False
        self._vector_size: int | None = None

    # ---- 基础能力 ----
    def _client_instance(self) -> QdrantClient:
        if self._client is None:
            self._client = QdrantClient(url=self.qdrant_url)
        return self._client

    def _ensure_collection(self, dim: int) -> None:
        client = self._client_instance()
        if self._collection_checked:
            if self._vector_size and self._vector_size != dim:
                raise RagConfigurationError(
                    "Qdrant collection vector size mismatch: expected %s, got %s"
                    % (self._vector_size, dim)
                )
            return

        if not client.collection_exists(collection_name=self.collection_name):
            client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )
            logger.info(
                "qdrant_create_collection name=%s dim=%s distance=cosine",
                self.collection_name,
                dim,
            )
            self._vector_size = dim
            self._collection_checked = True
            return

        info = client.get_collection(collection_name=self.collection_name)
        existing_dim = info.config.params.vectors.size
        self._vector_size = existing_dim
        self._collection_checked = True
        if existing_dim != dim:
            raise RagConfigurationError(
                "Existing Qdrant collection vector size %s mismatches requested %s"
                % (existing_dim, dim)
            )

    # ---- 嵌入 & 向量检索 ----
    def embed_text(self, text: str) -> List[float]:
        """调用 Ollama 生成文本向量。"""

        resp = self._requests.post(
            f"{self.ollama_url}/api/embeddings",
            json={"model": self.embed_model, "prompt": text},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        if "embedding" not in data:
            raise RuntimeError("Ollama embeddings response missing 'embedding' field")
        return data["embedding"]

    def index_chunks(self, pairs: Sequence[tuple[str, str]]) -> None:
        """将 (external_id, content) 对写入向量库。"""

        if not pairs:
            return

        vectors: list[tuple[str, List[float]]] = []
        for external_id, content in pairs:
            vector = self.embed_text(content)
            vectors.append((external_id, vector))

        dim = len(vectors[0][1])
        self._ensure_collection(dim)

        points = [PointStruct(id=external_id, vector=vector) for external_id, vector in vectors]
        self._client_instance().upsert(
            collection_name=self.collection_name,
            points=points,
        )
        logger.info(
            "qdrant_upsert collection=%s count=%s",
            self.collection_name,
            len(points),
        )

    def vector_search(self, query: str, limit: int) -> List[VectorHit]:
        """使用向量检索最相似的 chunk external_id 列表。"""

        if limit <= 0:
            return []

        query_vec = self.embed_text(query)
        self._ensure_collection(len(query_vec))

        result = self._client_instance().query_points(
            collection_name=self.collection_name,
            query=query_vec,
            limit=limit,
            with_payload=False,
        )

        hits: list[VectorHit] = []
        for point in result.points:
            hits.append(VectorHit(external_id=str(point.id), score=point.score))
        return hits

    # ---- 基于上下文的回答 ----
    def build_answer(self, question: str, contexts: Sequence[ContextChunk]) -> str:
        """将检索到的上下文交给 Ollama Chat，生成回答。"""

        if contexts:
            blocks = [
                f"[{idx}] ({ctx.label})\n{ctx.content}"
                for idx, ctx in enumerate(contexts, start=1)
            ]
            context_text = "\n\n".join(blocks)
        else:
            context_text = "(no relevant context retrieved)"

        system_prompt = (
            "You are a retrieval-augmented assistant."
            " Answer the user's question using only the provided context chunks."
            " If the context is insufficient, reply that you do not have enough information."
        )
        user_prompt = (
            f"Context chunks:\n\n{context_text}\n\n"
            f"Question: {question}\n"
            "When referencing information, cite the chunk number in square brackets."
        )

        resp = self._requests.post(
            f"{self.ollama_url}/api/chat",
            json={
                "model": self.chat_model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        if "message" in data and isinstance(data["message"], dict):
            content = data["message"].get("content")
            if content:
                return content
        return data.get("response", "")


_service: RagService | None = None


def get_rag_service() -> RagService:
    """获取全局复用的 RagService 实例（惰性初始化）。"""

    global _service
    if _service is None:
        _service = RagService()
    return _service

