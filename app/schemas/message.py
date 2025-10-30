"""Schemas for chat messages, extended with optional RAG parameters."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .base import ORMModel

Role = Literal["user", "assistant", "system"]


class MessageCreate(ORMModel):
    """Payload for creating a chat message.

    When role 为 ``user`` 时，可携带 RAG 相关的可选参数 ``top_k`` 与 ``domain_ids``，
    后端会基于该问题自动生成助手回复。
    """

    chat_id: int
    role: Role
    content: str = Field(..., min_length=1)
    top_k: int | None = Field(
        default=None,
        ge=1,
        le=100,
        description="可选的召回 chunk 数量，缺省使用环境变量设置",
    )
    domain_ids: list[int] | None = Field(
        default=None,
        description="可选的 domain 过滤列表，留空表示不限制",
    )


class MessageUpdate(ORMModel):
    """Partial update payload for existing messages."""

    content: str | None = None


class MessageOut(ORMModel):
    """Serialized chat message."""

    id: int
    chat_id: int
    role: Role
    content: str
    created_at: datetime
    updated_at: datetime


class MessageReference(BaseModel):
    """Source reference returned alongside assistant replies."""

    chunk_id: int
    score: float


class MessageCreateResponse(BaseModel):
    """Response after creating a message.

    ``assistant`` 字段在用户提问触发 RAG 时返回生成的助手消息，
    同时附带检索引用，便于前端直接渲染。
    """

    user: MessageOut
    assistant: MessageOut | None = None
    references: list[MessageReference] = Field(default_factory=list)

