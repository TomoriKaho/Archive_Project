"""Centralized application configuration powered by environment variables."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Expose strongly-typed access to .env configuration values."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    QDRANT_URL: str = "http://localhost:6333"  # Qdrant 服务地址
    QDRANT_COLLECTION: str = "VOC_Archives"  # 默认集合名称
    OLLAMA_URL: str = "http://localhost:11434"  # Ollama 服务地址
    OLLAMA_EMBED_MODEL: str = "qwen3-embedding:8b"  # 使用的嵌入模型名称
    OLLAMA_CHAT_MODEL: str = "llama3.1:8b"  # 回答问题的聊天模型
    RAG_TOP_K: int = 10  # 默认召回数量
    RAG_OLLAMA_TIMEOUT: int = 60  # 与 Ollama 交互的超时时间（秒）


settings = Settings()
