from datetime import datetime
from pydantic import Field
from .base import ORMModel

class ChatCreate(ORMModel):
    user_id: int = Field(..., description="归属用户 ID")
    title: str | None = None

class ChatUpdate(ORMModel):
    title: str | None = None

class ChatOut(ORMModel):
    id: int
    user_id: int
    title: str | None
    created_at: datetime
    updated_at: datetime