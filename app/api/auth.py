"""认证相关接口，实现注册、登录与查询当前用户。"""  # 模块说明
from __future__ import annotations  # 支持前向引用

import logging  # 日志记录便于追踪登录等安全操作
from fastapi import APIRouter, Depends, HTTPException, status  # FastAPI 核心对象和异常处理
from sqlalchemy.orm import Session  # 数据库会话类型

from app.api.deps import get_current_user, get_db  # 依赖：当前用户与数据库会话
from app.core.security import create_access_token, hash_password, verify_password  # 安全工具函数
from app.repositories.user_repo import UserRepository  # 用户数据访问层
from app.schemas.user import (  # 引入所需的Pydantic模型
    LoginRequest,
    Token,
    UserCreate,
    UserOut,
)
from app.services.password_guard import (  # 密码安全检测
    PASSWORD_POLICY_MESSAGE,
    is_password_compromised,
)

logger = logging.getLogger(__name__)  # 获取模块日志记录器

router = APIRouter(prefix="/auth", tags=["auth"])  # 定义认证路由分组


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "邮箱重复", "content": {"application/json": {"example": {"detail": "邮箱已存在"}}}},
    },
)
async def register(payload: UserCreate, db: Session = Depends(get_db)) -> UserOut:  # 定义注册接口
    """匿名注册新用户，始终以普通用户身份创建。"""  # 接口说明
    repo = UserRepository(db)  # 实例化仓储便于数据操作
    if repo.get_by_email(payload.email):  # 检查邮箱是否已存在
        logger.info("注册失败：邮箱重复", extra={"email": payload.email})  # 记录失败日志
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="邮箱已存在")  # 抛出409冲突错误
    if is_password_compromised(payload.password):  # 检查密码是否安全
        logger.warning("注册失败：密码不符合复杂度要求", extra={"email": payload.email})  # 记录安全事件
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=PASSWORD_POLICY_MESSAGE)  # 提示用户
    hashed = hash_password(payload.password)  # 对明文密码进行Argon2哈希，避免明文存储
    user = repo.create_user(  # 创建用户记录
        email=payload.email,
        hashed_password=hashed,
        is_admin=False,  # 注册接口禁止设置管理员防止越权
        full_name=payload.full_name,
    )
    logger.info("注册成功", extra={"user_id": user.id})  # 记录成功日志
    return UserOut.model_validate(user)  # 转换为Pydantic模型返回


@router.post(
    "/login",
    response_model=Token,
    responses={
        401: {"description": "登录失败", "content": {"application/json": {"example": {"detail": "邮箱或密码错误"}}}},
    },
)
async def login(payload: LoginRequest, db: Session = Depends(get_db)) -> Token:  # 定义登录接口
    """使用邮箱和密码换取JWT访问令牌。"""  # 接口说明
    repo = UserRepository(db)  # 创建仓储实例
    user = repo.get_by_email(payload.email)  # 根据邮箱查找用户
    if not user or not verify_password(payload.password, user.hashed_password):  # 校验账号与密码
        logger.warning("登录失败", extra={"email": payload.email})  # 记录失败日志
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误")  # 抛出401错误
    token = create_access_token({"sub": str(user.id)})  # 生成包含用户ID的JWT
    logger.info("登录成功", extra={"user_id": user.id})  # 记录成功日志
    return Token(access_token=token, token_type="bearer")  # 返回标准格式的令牌

@router.get(
    "/me",
    response_model=UserOut,
    responses={
        401: {"description": "未登录", "content": {"application/json": {"example": {"detail": "无效的认证凭证"}}}},
    },
)
async def read_current_user(current_user=Depends(get_current_user)) -> UserOut:  # 定义获取当前用户接口
    """返回当前登录用户的信息。"""  # 接口说明
    return UserOut.model_validate(current_user)  # 直接返回Pydantic模型
