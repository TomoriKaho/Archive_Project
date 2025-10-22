from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_auth import get_current_user, get_current_admin
from app.core.security import hash_password
from app.repositories.user_repo import UserRepository
from app.schemas.user import UserCreate, UserUpdate, UserOut

router = APIRouter(prefix="/users", tags=["users"])

# ---------- 管理员：列表 ----------
@router.get("/", response_model=list[UserOut])
def list_users(
    q: str | None = Query(None, description="按邮箱模糊搜索"),
    offset: int = 0,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _admin = Depends(get_current_admin),
):
    return UserRepository(db).search(q=q, offset=offset, limit=limit)

# ---------- 管理员：创建用户（可指定 is_admin） ----------
@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user_admin(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _admin = Depends(get_current_admin),
):
    repo = UserRepository(db)
    if repo.get_by_email(payload.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "email already registered")
    hashed = hash_password(payload.password)
    user = repo.create_user(email=payload.email.lower(), hashed_password=hashed, is_admin=payload.is_admin)
    return UserOut.model_validate(user)

# ---------- 管理员：按 ID / 按邮箱 获取 ----------
@router.get("/{user_id}", response_model=UserOut)
def get_user_by_id(user_id: int, db: Session = Depends(get_db), _admin = Depends(get_current_admin)):
    user = UserRepository(db).get(user_id)
    if not user:
        raise HTTPException(404, "user not found")
    return user

@router.get("/by-email/{email}", response_model=UserOut)
def get_user_by_email(email: str, db: Session = Depends(get_db), _admin = Depends(get_current_admin)):
    user = UserRepository(db).get_by_email(email.lower())
    if not user:
        raise HTTPException(404, "user not found")
    return user

# ---------- 管理员：更新/删除 任意用户 ----------
@router.patch("/{user_id}", response_model=UserOut)
def update_user_admin(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    _admin = Depends(get_current_admin),
):
    repo = UserRepository(db)
    user = repo.get(user_id)
    if not user:
        raise HTTPException(404, "user not found")

    data = payload.model_dump(exclude_unset=True, exclude_none=True)

    # 改邮箱需要校验唯一
    if "email" in data:
        if (other := repo.get_by_email(data["email"].lower())) and other.id != user_id:
            raise HTTPException(409, "email already registered")
        user.email = data["email"].lower()

    # 改密码要哈希
    if "password" in data:
        user.hashed_password = hash_password(data.pop("password"))

    # 改 is_admin（管理员才走到这里）
    if "is_admin" in data:
        user.is_admin = bool(data["is_admin"])

    repo.db.add(user)
    repo.db.flush()
    return user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_admin(user_id: int, db: Session = Depends(get_db), _admin = Depends(get_current_admin)):
    UserRepository(db).delete(user_id)

# ---------- 登录用户自助：/users/me ----------
@router.get("/me", response_model=UserOut)
def get_me(cur = Depends(get_current_user)):
    return cur

@router.patch("/me", response_model=UserOut)
def update_me(payload: UserUpdate, db: Session = Depends(get_db), cur = Depends(get_current_user)):
    repo = UserRepository(db)
    user = repo.get(cur.id)
    if not user:
        raise HTTPException(404, "user not found")

    data = payload.model_dump(exclude_unset=True, exclude_none=True)

    # 普通用户不可自行变更 is_admin
    if "is_admin" in data:
        raise HTTPException(403, "cannot change is_admin")

    # 改邮箱（检查唯一）
    if "email" in data:
        if (other := repo.get_by_email(data["email"].lower())) and other.id != cur.id:
            raise HTTPException(409, "email already registered")
        user.email = data["email"].lower()

    # 改密码
    if "password" in data:
        user.hashed_password = hash_password(data.pop("password"))

    repo.db.add(user)
    repo.db.flush()
    return user
