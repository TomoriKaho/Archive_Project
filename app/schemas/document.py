"""文档相关Pydantic模型，负责请求与响应的结构校验。"""
from datetime import datetime  # 导入datetime用于序列化时间戳字段
from typing import Any, Dict, List, Literal  # 引入List以描述列表字段
from uuid import UUID  # 导入UUID类型与数据库字段保持一致

from pydantic import Field  # 使用Field提供更丰富的校验与描述

from .base import ORMModel  # 引入项目自定义的ORMModel基类
from .chunk import ChunkOut


class DocumentCreate(ORMModel):
    """创建文档时使用的请求体模型。"""
    title: str = Field(..., description="文档标题，必填")  # 标题为必填项用于区分文档
    content: str = Field(..., description="原始文档内容字符串，用于切分")  # 内容用于切分chunk并不直接入库
    doc_metadata: Dict[str, Any] = Field(default_factory=dict, description="文档附加元数据")  # 使用默认工厂避免可变默认值复用
    # 设计说明：创建模型明确区分文档原文与元数据，方便同步切分并保留结构化标记。


class DocumentUpdate(ORMModel):
    """更新文档时使用的模型，仅支持局部更新。"""
    title: str | None = Field(default=None, description="可选的新标题")  # 标题允许按需修改
    doc_metadata: Dict[str, Any] | None = Field(default=None, description="可选的新元数据")  # 允许覆盖元数据信息
    domain_id: int | None = Field(default=None, description="可选的新domain ID，用于迁移文档")
    # 设计说明：更新模型保持可选字段以支撑PATCH语义，避免误清空。


class DocumentOut(ORMModel):
    """文档对外输出的响应模型。"""
    id: int  # 返回数据库自增主键便于内部调试
    uuid: UUID  # 暴露无序UUID供外部系统引用
    domain_id: int  # 告知文档所属的数据域
    title: str  # 返回标题供界面展示
    doc_metadata: Dict[str, Any]  # 保留元数据便于前端判断结构化类型
    vector_index_status: str = Field(
        description="向量入库状态：queued/processing/completed/failed/pending/cancelled/paused"
    )
    vector_indexed_chunks: int = Field(
        description="已完成向量化的chunk数量"
    )
    vector_total_chunks: int = Field(
        description="待向量化的chunk总数"
    )
    vector_index_error: str | None = Field(
        default=None, description="最近一次索引失败时的错误信息"
    )
    created_at: datetime  # 展示创建时间便于排序
    updated_at: datetime  # 展示更新时间便于排查差异
    # 设计说明：输出模型同时提供内部id与外部uuid，兼顾兼容性与安全性。


class DocumentListResponse(ORMModel):
    """文档分页列表响应模型。"""
    items: List[DocumentOut]  # 实际文档数据列表
    total: int  # 总记录数用于前端分页
    limit: int  # 本次查询的限制条数
    offset: int  # 本次查询的偏移量
    sort_by: str  # 当前排序字段
    order: str  # 当前排序方向
    # 设计说明：统一返回结构让前端在不同筛选下共享分页逻辑。


class ChunkListResponse(ORMModel):
    """文档片段分页列表响应模型。"""

    items: List[ChunkOut]  # 本页片段数据
    total: int  # 片段总数
    limit: int  # 本次请求的limit
    offset: int  # 本次请求的offset


class DocumentContentOut(ORMModel):
    """文档原始内容分页返回模型。"""

    mode: Literal["text", "csv", "json"]  # 内容类型：纯文本、CSV表格或JSON表格
    total: int  # 总行数或总记录数
    offset: int  # 当前页偏移
    limit: int  # 每页数量
    lines: List[str] = Field(default_factory=list)  # 文本模式下的内容行
    headers: List[str] = Field(default_factory=list)  # CSV表头
    rows: List[List[str]] = Field(default_factory=list)  # CSV数据行
