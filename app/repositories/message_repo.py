# -*- coding: utf-8 -*-
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.entities import Message
from app.services.rag_constants import CHUNK_MEMORY_PREFIX, CHAT_SUMMARY_PREFIX

from .base import Repository

class MessageRepository(Repository[Message]):
    def __init__(self, db: Session):
        super().__init__(db, Message)

    def list_by_chat(self, chat_id: int, offset: int = 0, limit: int = 100):
        stmt = (
            select(Message)
            .where(
                Message.chat_id == chat_id,
                Message.content.not_like(f"{CHUNK_MEMORY_PREFIX}%"),
                Message.content.not_like(f"{CHAT_SUMMARY_PREFIX}%"),
            )
            .order_by(Message.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        return self.db.execute(stmt).scalars().all()

    def list_for_prompt(self, chat_id: int, tail_limit: int = 20) -> list[Message]:
        """
        返回给 LLM 用的对话历史：
        - 最新一条对话摘要（CHAT_SUMMARY_PREFIX 开头的 system 消息）
        - 再加上最近 tail_limit 条非摘要的普通消息
        - 自动排除 chunk memory 消息
        """

        # 先把除了 chunk memory 的所有消息都取出来
        stmt = (
            select(Message)
            .where(
                Message.chat_id == chat_id,
                Message.content.not_like(f"{CHUNK_MEMORY_PREFIX}%"),
            )
            .order_by(Message.created_at.asc())
        )
        messages = self.db.execute(stmt).scalars().all()

        latest_summary: Message | None = None
        normal_messages: list[Message] = []

        for m in messages:
            content = m.content or ""
            # 把所有摘要消息记下来，但只保留“最新那一条”
            if content.startswith(CHAT_SUMMARY_PREFIX):
                latest_summary = m
                continue
            # 其他的就是正常对话
            normal_messages.append(m)

        # 最近 tail_limit 条非摘要消息
        tail = normal_messages[-tail_limit:]

        result: list[Message] = []

        if latest_summary is not None:
            # 可以在这里选择是否去掉前缀再喂给 LLM
            # 例如：
            latest_summary = Message(
                id=latest_summary.id,
                chat_id=latest_summary.chat_id,
                role=latest_summary.role,
                content=latest_summary.content[len(CHAT_SUMMARY_PREFIX):],
                created_at=latest_summary.created_at,
            )
            result.append(latest_summary)

        result.extend(tail)
        return result
    
    def list_memory(self, chat_id: int) -> list[Message]:
        """Return persisted chunk memory messages for the chat."""

        stmt = (
            select(Message)
            .where(
                Message.chat_id == chat_id,
                Message.content.like(f"{CHUNK_MEMORY_PREFIX}%"),
            )
            .order_by(Message.created_at.asc())
        )
        return list(self.db.execute(stmt).scalars().all())
    
    def delete_many(self, message_ids: Sequence[int]) -> None:
        """Bulk delete messages by id."""

        if not message_ids:
            return
        stmt = select(Message).where(Message.id.in_(message_ids))
        for message in self.db.execute(stmt).scalars().all():
            self.db.delete(message)
        self.db.flush()


