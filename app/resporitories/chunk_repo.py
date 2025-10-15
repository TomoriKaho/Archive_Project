# -*- coding: utf-8 -*-
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from .base import Repository
from app.models.entities import Chunk

class ChunkRepository(Repository[Chunk]):
    def __init__(self, db: Session):
        super().__init__(db, Chunk)

    def list_by_document(self, document_id: int):
        stmt = (
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.ordinal.asc())
        )
        return self.db.execute(stmt).scalars().all()

    def delete_by_document(self, document_id: int):
        self.db.execute(delete(Chunk).where(Chunk.document_id == document_id))
        self.db.flush()

