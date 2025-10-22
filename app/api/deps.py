"""FastAPI dependency utilities."""
from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.entities import User
from app.repositories.user_repo import UserRepository
from app.schemas.token import TokenPayload


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：确保请求生命周期内提交或回滚事务。"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    """Return the authenticated user based on the provided JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        token_data = TokenPayload(**payload)
    except (JWTError, ValidationError) as exc:  # pragma: no cover - defensive branch
        raise credentials_exception from exc

    try:
        user_id = int(token_data.sub)
    except ValueError as exc:  # pragma: no cover - should never happen
        raise credentials_exception from exc

    repo = UserRepository(db)
    user = repo.get(user_id)
    if user is None:
        raise credentials_exception
    return user


async def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Ensure the current user has administrator privileges."""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user
