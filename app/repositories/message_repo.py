# -*- coding: utf-8 -*-
from sqlalchemy import select
from sqlalchemy.orm import Session
from .base import Repository
from app.models.entities import Message

class MessageRepository(Repository[Message]):
    def __init__(self, db: Session):
        super().__init__(db, Message)

    def list_by_chat(self, chat_id: int, offset: int = 0, limit: int = 100):
        stmt = (
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.created_at.asc())
            .offset(offset).limit(limit)
        )
        return self.db.execute(stmt).scalars().all()
