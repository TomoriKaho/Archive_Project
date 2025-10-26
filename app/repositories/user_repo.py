"""用户仓储，封装针对 user 表的数据库访问逻辑。"""  # 模块说明
from __future__ import annotations  # 支持前向引用

from typing import List, Tuple  # 类型提示：列表与总数

from sqlalchemy import Select, func, or_, select  # 导入查询构造所需函数
from sqlalchemy.orm import Session  # SQLAlchemy 会话类型

from .base import Repository  # 引入通用仓储基类
from app.models.entities import User  # 导入用户实体类型


class UserRepository(Repository[User]):  # 用户仓储实现
    """针对 user 表的专用操作集合。"""  # 类文档

    def __init__(self, db: Session):  # 初始化仓储
        super().__init__(db, User)  # 调用父类构造函数保存会话和模型

    def _base_query(self, keyword: str | None) -> Select[tuple[User]]:  # 内部方法用于拼装查询
        stmt = select(User)  # 基础查询选择全部字段
        if keyword:  # 如果提供了搜索关键词
            pattern = f"%{keyword}%"  # 构造模糊匹配模式
            stmt = stmt.where(or_(User.email.ilike(pattern), User.full_name.ilike(pattern)))  # 在邮箱或姓名上做模糊匹配
        return stmt  # 返回构造好的语句

    def list_with_total(self, limit: int, offset: int, keyword: str | None = None) -> Tuple[List[User], int]:  # 分页查询接口
        """按分页返回用户列表以及总条数，支持关键词搜索。"""  # 方法描述
        stmt = self._base_query(keyword).order_by(User.created_at.desc())  # 按创建时间倒序排列
        result = self.db.execute(stmt.offset(offset).limit(limit))  # 执行分页查询
        items = list(result.scalars().all())  # 显式转换为列表
        count_stmt = select(func.count()).select_from(self._base_query(keyword).subquery())  # 子查询统计总量
        total = self.db.execute(count_stmt).scalar_one()  # 获取总数
        return items, total  # 返回列表与总数

    def get_by_email(self, email: str) -> User | None:  # 通过邮箱获取用户
        stmt = select(User).where(User.email == email)  # 构造精确匹配查询
        return self.db.execute(stmt).scalar_one_or_none()  # 执行并返回单条或None

    def create_user(self, email: str, hashed_password: str, is_admin: bool = False, full_name: str | None = None) -> User:  # 创建用户方法
        """创建用户记录，注意密码应为哈希值。"""  # 方法描述
        return self.create(email=email, hashed_password=hashed_password, is_admin=is_admin, full_name=full_name)  # 调用父类create


# 设计说明：仓储层集中实现分页与搜索逻辑，保证路由层不直接操作SQLAlchemy细节，便于测试与维护。
