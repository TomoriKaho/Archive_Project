# -*- coding: utf-8 -*-
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.entities import Message
from app.services.rag_constants import CHUNK_MEMORY_PREFIX

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
            )
            .order_by(Message.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        return self.db.execute(stmt).scalars().all()

    def list_for_prompt(self, chat_id: int) -> list[Message]:
        """Return all non-memory messages for the chat ordered chronologically."""

        stmt = (
            select(Message)
            .where(
                Message.chat_id == chat_id,
                Message.content.not_like(f"{CHUNK_MEMORY_PREFIX}%"),
            )
            .order_by(Message.created_at.asc())
        )
        return self.db.execute(stmt).scalars().all()

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
        return self.db.execute(stmt).scalars().all()

    def delete_many(self, message_ids: Sequence[int]) -> None:
        """Bulk delete messages by id."""

        if not message_ids:
            return
        stmt = select(Message).where(Message.id.in_(message_ids))
        for message in self.db.execute(stmt).scalars().all():
            self.db.delete(message)
        self.db.flush()
