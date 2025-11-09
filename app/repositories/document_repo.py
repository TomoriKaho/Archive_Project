"""文档仓储，封装所有与documents表相关的数据库操作。"""
from __future__ import annotations  # 允许在类型注解中使用前置声明

import logging  # 引入日志记录便于排查
from typing import Sequence  # 使用Sequence表达查询结果集合
from uuid import UUID  # UUID用于按无序标识查询

from sqlalchemy import Select, func, select  # 引入select构造查询
from sqlalchemy.orm import Session  # 使用Session执行SQL

from .base import Repository  # 基类提供通用CRUD
from app.models.entities import Document, Domain  # 引入Document模型

logger = logging.getLogger(__name__)  # 初始化模块级日志记录器


def _escape_like_pattern(value: str) -> str:
    """对LIKE模式中的特殊字符进行转义，确保搜索作为字面量处理。"""
    return (
        value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )


class DocumentRepository(Repository[Document]):
    """针对文档的高级查询接口。"""

    def __init__(self, db: Session):
        # 构造函数仅传递会话与模型类型
        super().__init__(db, Document)  # 复用通用仓储逻辑
        # 设计说明：仓储保持轻量，主要负责构造SQL表达式。

    def list_by_domain(self, domain_id: int, offset: int = 0, limit: int = 50) -> Sequence[Document]:
        """按domain筛选文档列表。"""
        stmt: Select[tuple[Document]] = (  # 构建select语句
            select(Document)  # 查询Document表
            .where(Document.domain_id == domain_id)  # 按domain过滤
            .order_by(Document.created_at.desc())  # 按创建时间倒序展示最新文档
            .offset(offset)  # 支持分页偏移
            .limit(limit)  # 支持分页限制
        )
        logger.info("list_by_domain domain=%s offset=%s limit=%s", domain_id, offset, limit)  # 记录查询行为便于追踪
        return self.db.execute(stmt).scalars().all()  # 执行SQL并返回对象列表
        # 设计说明：domain维度常规查询保持简单，便于后续叠加排序需求。

    def list_all(self) -> Sequence[Document]:
        """获取全量文档列表，供全局接口使用。"""
        return self.list_with_filters(limit=50, offset=0, sort_by="created_at", order="desc")  # 调用统一入口
        # 设计说明：复用分页入口避免两套排序逻辑。

    def list_with_filters(
        self,
        *,
        limit: int,
        offset: int,
        sort_by: str,
        order: str,
        domain_id: int | None = None,
        search: str | None = None,
    ) -> Sequence[Document]:
        """支持分页与排序的通用查询。"""
        stmt = select(Document)  # 基础查询
        if domain_id is not None:
            stmt = stmt.where(Document.domain_id == domain_id)  # 按domain过滤
        if search:
            escaped = _escape_like_pattern(search)
            stmt = stmt.where(Document.title.ilike(f"%{escaped}%", escape="\\"))
        if sort_by == "domain":
            stmt = stmt.join(Domain, Document.domain_id == Domain.id)
            sort_column = Domain.name
        elif sort_by == "title":
            sort_column = Document.title
        elif sort_by == "updated_at":
            sort_column = Document.updated_at
        else:
            sort_column = Document.created_at
        sort_expression = sort_column.asc() if order == "asc" else sort_column.desc()
        stmt = (
            stmt.order_by(sort_expression, Document.id.asc())
            .offset(offset)
            .limit(limit)
        )  # 应用排序与分页
        logger.info(
            "list_with_filters domain=%s limit=%s offset=%s sort_by=%s order=%s",
            domain_id,
            limit,
            offset,
            sort_by,
            order,
        )  # 记录查询参数
        return self.db.execute(stmt).scalars().all()  # 执行SQL返回结果
        # 设计说明：统一的分页查询接口为API层提供复用能力。

    def get_by_uuid(self, doc_uuid: UUID) -> Document | None:
        """按UUID查询单条文档。"""
        stmt = select(Document).where(Document.uuid == doc_uuid)  # 构造uuid过滤条件
        logger.info("get_by_uuid uuid=%s", doc_uuid)  # 打印查询参数
        return self.db.execute(stmt).scalar_one_or_none()  # 返回匹配的文档或None
        # 设计说明：uuid查询用于外部接口，实现幂等删除等需求。

    def delete_by_uuid(self, doc_uuid: UUID) -> bool:
        """按UUID删除文档，返回是否真的删除。"""
        doc = self.get_by_uuid(doc_uuid)  # 先查再删避免盲删
        if not doc:
            logger.info("delete_by_uuid miss uuid=%s", doc_uuid)  # 记录未命中便于幂等说明
            return False  # 未找到返回False供上层决定响应
        self.db.delete(doc)  # 删除记录
        self.db.flush()  # 立即同步到事务缓冲
        logger.info("delete_by_uuid success uuid=%s", doc_uuid)  # 记录删除成功
        return True  # 返回删除成功
        # 设计说明：通过先查后删我们可复用SQLAlchemy级联能力并统一幂等处理。

    def count_all(self) -> int:
        """统计文档总数，供后续分页元数据使用。"""
        return self.count_with_filters()  # 复用带过滤统计
        # 设计说明：复用逻辑避免两份实现。

    def count_with_filters(
        self, *, domain_id: int | None = None, search: str | None = None
    ) -> int:
        """根据过滤条件统计文档数量。"""
        stmt = select(func.count()).select_from(Document)  # 构造COUNT(*)
        if domain_id is not None:
            stmt = stmt.where(Document.domain_id == domain_id)  # 按domain过滤
        if search:
            escaped = _escape_like_pattern(search)
            stmt = stmt.where(Document.title.ilike(f"%{escaped}%", escape="\\"))
        total = self.db.execute(stmt).scalar_one()  # 执行统计
        logger.info("count_with_filters domain=%s total=%s", domain_id, total)  # 输出统计信息
        return total  # 返回计数
        # 设计说明：COUNT(*)在当前规模成本可接受，在数据量增长时可考虑缓存。
