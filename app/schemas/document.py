from datetime import datetime
from typing import Any, Dict
from .base import ORMModel

class DocumentCreate(ORMModel):
    domain_id: int
    title : str
    doc_metadata : Dict[str, Any] = {}

class DocumentUpdate(ORMModel):
    title: str | None = None
    doc_metadata: Dict[str, Any] | None = None

class DocumentOut(ORMModel):
    id: int
    domain_id: int
    title: str
    doc_metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime