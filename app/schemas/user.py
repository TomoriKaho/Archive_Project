from datetime import datetime
from pydantic import EmailStr, Field
from .base import ORMModel

class UserBase(ORMModel):
    email: EmailStr = Field(..., description="用户邮箱")
    is_admin: bool = Field(False, description="是否管理员")

class UserCreate(ORMModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="明文密码")
    is_admin: bool = False

class UserUpdate(ORMModel):
    email: EmailStr | None = None
    password: str | None = Field(None, min_length=6)
    is_admin: bool | None = None

class UserOut(UserBase):
    id: int
    email: EmailStr
    is_admin: bool
    created_at: datetime
    updated_at: datetime