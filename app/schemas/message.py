from datetime import datetime
from typing import Literal
from pydantic import Field
from .base import ORMModel

Role = Literal["user", "assistant", "system"]

class MessageCreate(ORMModel):
    chat_id: int
    role: Role
    content: str = Field(..., min_length=1)

class MessageUpdate(ORMModel):
    content: str | None = None

class MessageOut(ORMModel):
    id: int
    chat_id: int
    role: Role
    content: str
    created_at: datetime
    updated_at: datetime