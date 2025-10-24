"""为documents表新增uuid列并填充历史数据。"""
from __future__ import annotations  # 支持前向注解

import uuid  # 用于生成uuid4
from typing import Sequence, Union  # Alembic需要的类型声明

from alembic import op  # Alembic操作接口
import sqlalchemy as sa  # SQLAlchemy工具
from sqlalchemy.dialects import postgresql  # PostgreSQL专用UUID类型

# revision identifiers, used by Alembic.
revision: str = "6d1bb8e5d3b1"  # 当前迁移的唯一ID
down_revision: Union[str, Sequence[str], None] = "c4e0bace8ba8"  # 指向上一版本
branch_labels: Union[str, Sequence[str], None] = None  # 无独立分支
depends_on: Union[str, Sequence[str], None] = None  # 无额外依赖


def upgrade() -> None:
    """升级操作：新增uuid列并填充历史数据。"""
    bind = op.get_bind()  # 获取数据库连接
    inspector = sa.inspect(bind)  # 读取当前数据库结构信息以做幂等处理
    columns = {col["name"] for col in inspector.get_columns("documents")}  # 收集documents现存列
    if "uuid" not in columns:  # 若不存在uuid列才执行新增，避免重复迁移时报错
        op.add_column(  # 新增uuid列，先允许为空以便回填
            "documents",
            sa.Column(
                "uuid",
                postgresql.UUID(as_uuid=True),  # 使用PostgreSQL原生UUID类型以保持类型一致
                nullable=True,  # 暂时允许空值
            ),
        )
    documents_table = sa.table(  # 构造临时表对象便于写SQL
        "documents",
        sa.column("id", sa.BigInteger),
        sa.column("uuid", postgresql.UUID(as_uuid=True)),
    )
    rows = list(  # 仅查询uuid为空的行，避免重复覆盖已有值
        bind.execute(
            sa.select(documents_table.c.id).where(documents_table.c.uuid.is_(None))
        )
    )
    for row in rows:
        bind.execute(  # 逐条写入uuid4
            documents_table.update()
            .where(documents_table.c.id == row.id)
            .values(uuid=uuid.uuid4())
        )
    op.alter_column("documents", "uuid", nullable=False)  # 回填完成后改为非空（重复执行也安全）
    inspector = sa.inspect(bind)  # 再次读取索引信息确保唯一索引存在
    indexes = {index["name"] for index in inspector.get_indexes("documents")}  # 收集现有索引
    if "ix_documents_uuid" not in indexes:  # 若尚未创建uuid索引则创建
        op.create_index(  # 为uuid建立唯一索引
            "ix_documents_uuid",
            "documents",
            ["uuid"],
            unique=True,
        )
    # 设计说明：uuid列作为对外标识，唯一索引保障幂等与冲突检测。


def downgrade() -> None:
    """回滚操作：移除uuid列与索引。"""
    bind = op.get_bind()  # 获取数据库连接
    inspector = sa.inspect(bind)  # 读取当前结构以幂等删除
    indexes = {index["name"] for index in inspector.get_indexes("documents")}  # 获取已有索引
    if "ix_documents_uuid" in indexes:  # 仅当索引存在时才删除
        op.drop_index("ix_documents_uuid", table_name="documents")  # 先删除索引避免悬挂
    columns = {col["name"] for col in inspector.get_columns("documents")}  # 获取列信息
    if "uuid" in columns:  # 仅当列存在时才删除
        op.drop_column("documents", "uuid")  # 再删除列
    # 设计说明：逆序撤销可保持数据库状态一致，并通过幂等判断避免重复执行失败。
