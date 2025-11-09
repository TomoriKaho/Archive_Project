from datetime import datetime
from typing import List

from pydantic import Field

from .base import ORMModel


class ChatCreate(ORMModel):
    user_id: int = Field(..., description="归属用户 ID")
    title: str | None = None
    domain_ids: List[int] | None = Field(
        default=None, description="会话限定检索的 domain 列表，留空表示使用全部"
    )



class ChatUpdate(ORMModel):
    title: str | None = None
    domain_ids: List[int] | None = Field(
        default=None, description="更新会话绑定的 domain 列表，空数组表示重置"
    )



class ChatOut(ORMModel):
    id: int
    user_id: int
    title: str | None
    domain_ids: List[int] | None
    created_at: datetime
    updated_at: datetime
