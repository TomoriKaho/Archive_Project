"""对 user 表补充字段并写入初始管理员账号。"""  # 迁移说明
from __future__ import annotations  # 支持前向引用

import logging  # 输出迁移过程的提示信息
import os  # 读取环境变量以决定初始密码
from typing import Sequence, Union  # Alembic 所需类型声明

from alembic import op  # Alembic 操作接口
import sqlalchemy as sa  # SQLAlchemy 基础类型
from passlib.context import CryptContext  # Passlib 提供Argon2哈希
from sqlalchemy.dialects.postgresql import insert  # PostgreSQL特有的插入语句

# revision identifiers, used by Alembic.
revision: str = "8dca4f9d1b2d"  # 当前迁移版本号
down_revision: Union[str, Sequence[str], None] = "6d1bb8e5d3b1"  # 上一个迁移版本
branch_labels: Union[str, Sequence[str], None] = None  # 无分支
depends_on: Union[str, Sequence[str], None] = None  # 无依赖

logger = logging.getLogger(__name__)  # 初始化日志记录器
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")  # 配置Argon2密码哈希器


def upgrade() -> None:  # 升级入口
    """执行数据库升级：补充字段与初始数据。"""  # 函数说明
    op.add_column(  # 为用户表新增full_name列
        "user",
        sa.Column("full_name", sa.String(length=255), nullable=True, comment="用户全名"),
    )
    op.alter_column(  # 将密码哈希列扩展到512字符以适配Argon2摘要
        "user",
        "hashed_password",
        existing_type=sa.String(length=255),
        type_=sa.String(length=512),
        existing_nullable=False,
    )
    op.drop_constraint("user_email_key", "user", type_="unique")  # 删除旧的唯一约束
    op.create_index("ix_user_email", "user", ["email"], unique=True)  # 改用唯一索引以提升查询效率

    admin_password = os.getenv("ADMIN_INIT_PASSWORD", "ChangeMe123")  # 读取初始密码或默认值
    hashed_password = pwd_context.hash(admin_password)  # 使用Argon2生成哈希，避免在迁移中写入明文
    user_table = sa.table(  # 构造虚拟表对象用于插入
        "user",
        sa.column("email", sa.String(length=255)),
        sa.column("hashed_password", sa.String(length=512)),
        sa.column("full_name", sa.String(length=255)),
        sa.column("is_admin", sa.Boolean),
    )
    stmt = insert(user_table).values(  # 构造插入语句
        email="admin@example.com",
        hashed_password=hashed_password,
        full_name="Administrator",
        is_admin=True,
    ).on_conflict_do_nothing(index_elements=["email"])  # 若已存在则跳过避免重复
    op.execute(stmt)  # 执行插入
    logger.warning("已注入默认管理员 admin@example.com，请尽快修改密码")  # 输出修改密码提醒


def downgrade() -> None:  # 降级入口
    """执行数据库回滚：撤销字段与初始数据。"""  # 函数说明
    op.execute(  # 删除管理员账号，回滚数据迁移
        sa.text("DELETE FROM \"user\" WHERE email = :email"),
        {"email": "admin@example.com"},
    )
    op.drop_index("ix_user_email", table_name="user")  # 删除唯一索引
    op.create_unique_constraint("user_email_key", "user", ["email"])  # 恢复原有唯一约束
    op.alter_column(  # 将密码列恢复为255长度
        "user",
        "hashed_password",
        existing_type=sa.String(length=512),
        type_=sa.String(length=255),
        existing_nullable=False,
    )
    op.drop_column("user", "full_name")  # 移除新增的full_name列
