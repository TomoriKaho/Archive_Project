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
    op.add_column(  # 新增uuid列，先允许为空以便回填
        "documents",
        sa.Column(
            "uuid",
            postgresql.UUID(as_uuid=True),  # 使用PostgreSQL原生UUID类型以保持类型一致
            nullable=True,  # 暂时允许空值
        ),
    )
    bind = op.get_bind()  # 获取数据库连接
    documents_table = sa.table(  # 构造临时表对象便于写SQL
        "documents",
        sa.column("id", sa.BigInteger),
        sa.column("uuid", postgresql.UUID(as_uuid=True)),
    )
    rows = list(bind.execute(sa.select(documents_table.c.id)))  # 查询所有文档ID
    for row in rows:
        bind.execute(  # 逐条写入uuid4
            documents_table.update()
            .where(documents_table.c.id == row.id)
            .values(uuid=uuid.uuid4())
        )
    op.alter_column("documents", "uuid", nullable=False)  # 回填完成后改为非空
    op.create_index(  # 为uuid建立唯一索引
        "ix_documents_uuid",
        "documents",
        ["uuid"],
        unique=True,
    )
    # 设计说明：uuid列作为对外标识，唯一索引保障幂等与冲突检测。


def downgrade() -> None:
    """回滚操作：移除uuid列与索引。"""
    op.drop_index("ix_documents_uuid", table_name="documents")  # 先删除索引避免悬挂
    op.drop_column("documents", "uuid")  # 再删除列
    # 设计说明：逆序撤销可保持数据库状态一致。
