# -*- coding: utf-8 -*-
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from .base import Repository
from app.models.entities import Chat

class ChatRepository(Repository[Chat]):
    def __init__(self, db: Session):
        super().__init__(db, Chat)

    def list_by_user(self, user_id: int, offset: int = 0, limit: int = 50):
        stmt = (
            select(Chat)
            .where(Chat.user_id == user_id)
            .order_by(Chat.created_at.desc())
            .offset(offset).limit(limit)
        )
        return self.db.execute(stmt).scalars().all()

    def delete(self, id_: int) -> None:
        """Delete chat along with messages using bulk operations to reduce latency."""
        from app.models.entities import Message

        # remove associated messages in a single statement to avoid ORM cascade overhead
        self.db.execute(delete(Message).where(Message.chat_id == id_))
        super().delete(id_)
