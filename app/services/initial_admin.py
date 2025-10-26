"""Helpers for ensuring the initial administrator account exists."""
from __future__ import annotations

import logging
import os
from dotenv import load_dotenv, find_dotenv  # 用于加载环境变量
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)
load_dotenv(find_dotenv())
INITIAL_ADMIN_EMAIL: str = os.getenv("INITIAL_ADMIN_EMAIL", "admin@example.com")
ADMIN_INIT_PASSWORD: str = os.getenv("ADMIN_INIT_PASSWORD", "ChangeMe123")


def ensure_initial_admin(db: Session) -> None:
    """Create the initial administrator if it does not exist."""

    repo = UserRepository(db)
    admin = repo.get_by_email(INITIAL_ADMIN_EMAIL)

    if admin is None:
        password = ADMIN_INIT_PASSWORD
        hashed_password = hash_password(password)
        repo.create_user(
            email=INITIAL_ADMIN_EMAIL,
            hashed_password=hashed_password,
            is_admin=True,
            full_name="Administrator",
        )
        logger.info("已创建初始管理员账号 %s", INITIAL_ADMIN_EMAIL)
        return

    if not admin.is_admin:
        repo.update(admin, is_admin=True)
        logger.info("已恢复账号 %s 的管理员权限", INITIAL_ADMIN_EMAIL)
