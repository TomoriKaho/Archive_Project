"""Wrapper around Ollama embedding endpoint."""
from __future__ import annotations

import json
import logging
from urllib import error, request

from app.core.config import settings

logger = logging.getLogger(__name__)


def embed(text: str) -> list[float]:
    """Embed the given text using Ollama's /api/embeddings endpoint."""

    payload = json.dumps({
        "model": settings.OLLAMA_EMBED_MODEL,
        "prompt": text,
    }).encode("utf-8")  # 将请求体编码为字节流
    req = request.Request(
        url=f"{settings.OLLAMA_URL.rstrip('/')}/api/embeddings",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=settings.RAG_OLLAMA_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))  # 解析JSON响应
    except error.HTTPError as exc:  # 处理HTTP错误
        body = exc.read().decode("utf-8", "ignore")
        logger.error("Ollama embeddings 请求失败: %s", body)
        raise RuntimeError("failed to call Ollama embeddings API") from exc
    except error.URLError as exc:  # 网络异常
        logger.error("无法连接到 Ollama 服务: %s", exc)
        raise RuntimeError("failed to reach Ollama embeddings API") from exc
    embedding = data.get("embedding")
    if not isinstance(embedding, list):  # 响应格式校验
        logger.error("Ollama 返回的 embedding 格式异常: %s", data)
        raise RuntimeError("invalid embedding response from Ollama")
    return [float(x) for x in embedding]  # 确保返回浮点列表
