from datetime import datetime
from .base import ORMModel

class ChunkCreate(ORMModel):
    document_id: int
    ordinal: int = 0
    content: str

class ChunkUpdate(ORMModel):
    content: str | None = None

class ChunkOut(ORMModel):
    id: int
    document_id: int
    external_id: str
    ordinal: int
    content: str
    created_at: datetime
    updated_at: datetime