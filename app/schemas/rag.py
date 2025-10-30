"""RAG 查询接口用到的 Pydantic Schema。"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from .base import ORMModel


class RagQueryRequest(BaseModel):
    """前端发起问答时提交的请求体。"""

    question: str = Field(..., min_length=1, description="用户提出的问题")
    top_k: int = Field(5, ge=1, le=20, description="返回多少条最相关的 chunk")
    domain_id: Optional[int] = Field(None, description="可选 domain 过滤条件")


class RagHit(ORMModel):
    """检索结果在接口中的展示形式。"""

    chunk_id: int
    external_id: str
    document_id: int
    document_title: str
    domain_id: int
    ordinal: int
    content: str
    score: float


class RagQueryResponse(BaseModel):
    """问答接口返回的数据结构。"""

    answer: str = Field(..., description="模型给出的回答")
    hits: list[RagHit] = Field(default_factory=list, description="参与回答的 chunk 列表")
