"""用户相关的Pydantic模型定义。"""  # 模块说明
from __future__ import annotations  # 支持前向引用

from datetime import datetime  # 时间字段类型
from typing import Optional  # 可选类型提示

from pydantic import EmailStr, Field  # Pydantic 字段类型与校验

from .base import ORMModel  # 统一的ORM模型基类


class UserCreate(ORMModel):  # 注册时使用的输入模型
    """注册或自助创建用户时的入参。"""  # 文档说明
    email: EmailStr = Field(..., description="邮箱地址，作为登录名")  # 邮箱必填并格式校验
    password: str = Field(..., min_length=8, description="明文密码，将在服务端转换为哈希存储")  # 密码最少8位确保安全
    full_name: Optional[str] = Field(
        None,
        description="可选的用户昵称或全名",
        max_length=30,
    )  # 可选全名字段，限制长度防止过长


class AdminUserCreate(UserCreate):  # 管理员创建用户的模型
    """管理员创建用户时允许指定是否为管理员。"""  # 文档说明
    is_admin: bool = Field(False, description="是否授予管理员权限，仅管理员可设置")  # 允许管理员设置权限


class UserUpdate(ORMModel):  # 更新用户信息的模型
    """用于PATCH部分更新用户资料。"""  # 文档说明
    email: Optional[EmailStr] = Field(
        None, description="新的邮箱地址，保持唯一性"
    )  # 可选更新邮箱
    full_name: Optional[str] = Field(
        None,
        description="新的全名，为None则不修改",
        max_length=30,
    )  # 可选更新全名
    password: Optional[str] = Field(None, min_length=8, description="新的明文密码")  # 可选更新密码
    is_admin: Optional[bool] = Field(None, description="是否提升为管理员，仅管理员可修改")  # 管理员控制权限


class UserOut(ORMModel):  # 对外返回的用户信息模型
    """响应中返回的用户概要信息。"""  # 文档说明
    id: int = Field(..., description="用户ID")  # 主键ID
    email: EmailStr = Field(..., description="邮箱")  # 邮箱
    full_name: Optional[str] = Field(None, description="全名", max_length=30)  # 全名
    is_admin: bool = Field(..., description="是否管理员")  # 管理员标志
    created_at: datetime = Field(..., description="创建时间")  # 创建时间戳
    updated_at: datetime = Field(..., description="更新时间")  # 更新时间戳


class UserListResponse(ORMModel):  # 分页列表响应模型
    """封装分页查询的响应结构。"""  # 文档说明
    items: list[UserOut] = Field(..., description="用户列表数据")  # 当前页用户数据
    total: int = Field(..., description="符合条件的总条数")  # 总条数
    limit: int = Field(..., description="每页条数")  # 分页大小
    offset: int = Field(..., description="偏移量")  # 偏移量
    sort_by: str = Field(..., description="当前排序字段")
    order: str = Field(..., description="排序方向")


class Token(ORMModel):  # 登录成功后返回的令牌结构
    """标准的OAuth2访问令牌响应。"""  # 文档说明
    access_token: str = Field(..., description="JWT 访问令牌")  # 令牌字符串
    token_type: str = Field("bearer", description="令牌类型，固定为bearer")  # 令牌类型


class TokenPayload(ORMModel):  # 解析JWT后的载荷模型
    """JWT 中保存的核心字段。"""  # 文档说明
    sub: str = Field(..., description="用户ID字符串形式")  # 主题字段保存用户ID
    exp: int = Field(..., description="过期时间戳")  # 过期时间戳


class LoginRequest(ORMModel):  # 登录接口的请求体
    """登录时提交的邮箱和密码。"""  # 文档说明
    email: EmailStr = Field(..., description="登录邮箱")  # 邮箱
    password: str = Field(..., description="明文密码")  # 密码


# 设计说明：Pydantic 模型将输入与输出分离，既防止哈希密码泄露，又集中描述字段校验逻辑，方便OpenAPI生成文档。
