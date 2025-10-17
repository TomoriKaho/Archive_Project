from datetime import datetime
from typing import Optional
from pydantic import Field
from .base import ORMModel


class ChunkCreate(ORMModel):
    ordinal: int = Field(default=0, description="在文档中的序号")
    content: str = Field(..., description="文档块内容，必填")


class ChunkUpdate(ORMModel):
    content: Optional[str] = Field(None, description="更新后的文档块内容")


class ChunkOut(ORMModel):
    id: int
    document_id: int
    external_id: str
    ordinal: int
    content: str
    created_at: datetime
    updated_at: datetime
