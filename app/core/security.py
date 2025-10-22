"""Security utilities for hashing and verifying user passwords."""

from passlib.context import CryptContext
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from jose import jwt
from jose.exceptions import JWTError

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev_only_change_me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

pwd_context = CryptContext(
    schemes=["bcrypt_sha256", "bcrypt"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    """Return the hashed representation of a plain text password."""

    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Validate a plain password against its hashed counterpart."""

    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str | int,
    extra: Optional[dict[str, Any]] = None,
    expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES,
) -> str:
    """根据用户ID（subject）签发短期访问令牌。"""
    to_encode: dict[str, Any] = {"sub": str(subject)}
    if extra:
        to_encode.update(extra)
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict[str, Any]:
    """解码并验证 JWT（含过期校验），返回 payload。"""
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
