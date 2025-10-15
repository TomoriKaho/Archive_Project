from datetime import datetime
from pydantic import Field
from .base import ORMModel

class DomainCreate(ORMModel):
    name: str = Field(..., min_length=1)
    description: str | None = None

class DomainUpdate(ORMModel):
    name: str | None = Field(None, min_length=1)
    description: str | None = None

class DomainOut(ORMModel):
    id: int
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime