from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.security import hash_password, verify_password
from app.repositories.user_repo import UserRepository
from app.schemas.user import AuthResponse, UserCreate, UserLogin, UserOut


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate, db: Session = Depends(get_db)) -> UserOut:
    repo = UserRepository(db)
    if repo.get_by_email(payload.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "email already registered")

    data = payload.model_dump()
    hashed = hash_password(data.pop("password"))
    user = repo.create_user(
        email=data["email"],
        hashed_password=hashed,
        is_admin=data.get("is_admin", False),
    )
    return UserOut.model_validate(user)


@router.post("/login", response_model=AuthResponse)
def login_user(payload: UserLogin, db: Session = Depends(get_db)) -> AuthResponse:
    repo = UserRepository(db)
    user = repo.get_by_email(payload.email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid email or password")

    return AuthResponse(user=UserOut.model_validate(user))