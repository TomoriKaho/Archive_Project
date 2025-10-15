# -*- coding: utf-8 -*-
from sqlalchemy import select
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
