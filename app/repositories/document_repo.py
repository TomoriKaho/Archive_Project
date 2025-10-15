# -*- coding: utf-8 -*-
from sqlalchemy import select
from sqlalchemy.orm import Session
from .base import Repository
from app.models.entities import Document

class DocumentRepository(Repository[Document]):
    def __init__(self, db: Session):
        super().__init__(db, Document)

    def list_by_domain(self, domain_id: int, offset: int = 0, limit: int = 50):
        stmt = (
            select(Document)
            .where(Document.domain_id == domain_id)
            .order_by(Document.created_at.desc())
            .offset(offset).limit(limit)
        )
        return self.db.execute(stmt).scalars().all()
