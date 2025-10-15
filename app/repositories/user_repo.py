# -*- coding: utf-8 -*-
from sqlalchemy import select
from sqlalchemy.orm import Session
from .base import Repository
from app.models.entities import User

class UserRepository(Repository[User]):
    def __init__(self, db: Session):
        super().__init__(db, User)

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self.db.execute(stmt).scalar_one_or_none()

    def create_user(self, email: str, hashed_password: str, is_admin: bool = False) -> User:
        """
        注意：传入的是“已哈希密码”。哈希工作放到 Service/路由层，Repository 保持“纯数据库写入”。
        """
        return self.create(email=email, hashed_password=hashed_password, is_admin=is_admin)
