"""文档块仓储，集中管理chunks表的访问逻辑。"""
import logging  # 引入日志便于观察批量操作
from typing import Iterable, Sequence  # 提供类型注解

from sqlalchemy import Select, delete, select  # 使用select/delete构造SQL
from sqlalchemy.orm import Session, joinedload  # 操作文档块依赖Session

from .base import Repository  # 复用通用仓储能力
from app.models.entities import Chunk, Document  # 引入Chunk模型

logger = logging.getLogger(__name__)  # 初始化日志记录器


class ChunkRepository(Repository[Chunk]):
    """针对chunks表的专用操作集合。"""

    def __init__(self, db: Session):
        super().__init__(db, Chunk)  # 调用父类初始化
        # 设计说明：仓储层保持薄，仅封装常用查询与批处理。

    def list_by_document(self, document_id: int) -> Sequence[Chunk]:
        """按文档ID获取所有chunk，按顺序返回。"""
        stmt: Select = (
            select(Chunk)
            .options(joinedload(Chunk.document))
            .where(Chunk.document_id == document_id)  # 条件限定同一文档
            .order_by(Chunk.ordinal.asc())  # 维持顺序供前端显示
        )
        logger.info("list_chunks document_id=%s", document_id)  # 记录访问日志
        return self.db.execute(stmt).scalars().all()  # 执行查询并返回结果
        # 设计说明：始终按ordinal排序确保切片输出有序。

    def bulk_create_for_document(self, document_id: int, contents: Iterable[str]) -> Sequence[Chunk]:
        """将多段文本批量写入chunks表。"""
        chunks = [  # 根据传入顺序生成Chunk实例
            Chunk(document_id=document_id, ordinal=index, content=text)
            for index, text in enumerate(contents)
        ]
        logger.info(
            "bulk_create_chunks document_id=%s count=%s", document_id, len(chunks)
        )  # 打印批量写入数量
        if not chunks:
            return []  # 无chunk则直接返回空列表
        self.db.add_all(chunks)  # 批量加入session以减少多次flush
        self.db.flush()  # 立即刷新以获得外键校验
        return chunks  # 返回持久化后的Chunk对象
        # 设计说明：批量插入减少数据库往返，保持事务内原子性。

    def get_many(self, ids: Sequence[int], domain_ids: Sequence[int] | None = None) -> list[Chunk]:
        """根据 chunk 主键批量读取记录，可选按 domain 过滤。"""

        if not ids:  # 没有ID直接返回空列表
            return []
        stmt: Select = (
            select(Chunk)
            .options(joinedload(Chunk.document))  # 预加载 document 以便读取 domain_id
            .where(Chunk.id.in_(list(ids)))
        )
        if domain_ids:  # 在SQL层做domain过滤，避免应用层再判断
            stmt = stmt.join(Chunk.document).where(Document.domain_id.in_(list(domain_ids)))
        result = self.db.execute(stmt).scalars().unique().all()  # unique() 避免 join 造成重复
        logger.info(
            "get_many_chunks ids=%s filtered_domain=%s fetched=%s",
            len(ids),
            list(domain_ids) if domain_ids else None,
            len(result),
        )
        return result

    def delete_by_document(self, document_id: int) -> None:
        """按文档删除全部chunk，作为兜底清理。"""
        self.db.execute(delete(Chunk).where(Chunk.document_id == document_id))  # 构造并执行删除
        self.db.flush()  # 刷新以确保删除立即生效
        logger.info("delete_chunks_by_document document_id=%s", document_id)  # 记录清理操作
        # 设计说明：该操作通常由外键级联覆盖，此处保留以应对旧数据。 
