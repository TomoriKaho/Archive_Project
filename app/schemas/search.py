"""传统搜索响应模型。"""
from __future__ import annotations

from typing import Any, Dict, List

from pydantic import Field

from .base import ORMModel


class ArchiveSearchItem(ORMModel):
    """单条档案搜索结果。"""

    page: int = Field(description="结果序号，从1开始")
    archive_name: str = Field(description="档案名称，取文档首列或常见字段")
    document_name: str = Field(description="所属文档名称")
    domain_name: str = Field(description="所属知识域名称")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="档案元数据")


class ArchiveSearchResponse(ORMModel):
    """档案搜索响应。"""

    items: List[ArchiveSearchItem]
    total: int
    page: int
    page_size: int

