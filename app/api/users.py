"""User management endpoints with administrator protection."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_current_user, get_db
from app.core.security import get_password_hash
from app.models.entities import User
from app.repositories.user_repo import UserRepository
from app.schemas.user import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    """Return the currently authenticated user."""
    return current_user


@router.get("/", response_model=list[UserOut])
async def list_users(
    offset: int = 0,
    limit: int = Query(50, ge=1, le=200),
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> list[User]:
    """List users with pagination (admin only)."""
    repo = UserRepository(db)
    return list(repo.list(offset=offset, limit=limit))


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> User:
    """Create a new user (admin only)."""
    repo = UserRepository(db)
    if repo.get_by_email(payload.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    return repo.create_user(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        is_admin=payload.is_admin,
    )


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Retrieve a user by id. Non-admins may only access themselves."""
    if not current_user.is_admin and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")

    repo = UserRepository(db)
    user = repo.get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Update a user. Admins can update anyone, regular users only themselves."""
    if not current_user.is_admin and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")

    repo = UserRepository(db)
    user = repo.get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    update_data = payload.model_dump(exclude_unset=True)

    if "is_admin" in update_data:
        if update_data["is_admin"] is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="is_admin cannot be null")
        if not current_user.is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges to change role")

    if "email" in update_data:
        new_email = update_data["email"]
        if new_email is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email cannot be null")
        existing = repo.get_by_email(new_email)
        if existing and existing.id != user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    if "password" in update_data:
        password = update_data.pop("password")
        if password is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password cannot be null")
        update_data["hashed_password"] = get_password_hash(password)

    user = repo.update(user, **update_data)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> None:
    """Delete a user (admin only)."""
    repo = UserRepository(db)
    user = repo.get(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    repo.delete(user_id)
