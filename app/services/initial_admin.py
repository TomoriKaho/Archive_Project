"""Helpers for ensuring the initial administrator account exists."""
from __future__ import annotations

import logging
import os

from sqlalchemy.orm import Session

from app.core.config import INITIAL_ADMIN_EMAIL
from app.core.security import hash_password
from app.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)

DEFAULT_ADMIN_PASSWORD = "ChangeMe123"


def _load_initial_password() -> str:
    """Fetch the password used when seeding the initial administrator."""

    password = os.getenv("ADMIN_INIT_PASSWORD")
    if password:
        return password
    logger.warning(
        "环境变量 ADMIN_INIT_PASSWORD 未设置，将使用默认密码 %s，请尽快修改。",
        DEFAULT_ADMIN_PASSWORD,
    )
    return DEFAULT_ADMIN_PASSWORD


def ensure_initial_admin(db: Session) -> None:
    """Create the initial administrator if it does not exist."""

    repo = UserRepository(db)
    admin = repo.get_by_email(INITIAL_ADMIN_EMAIL)

    if admin is None:
        password = _load_initial_password()
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
