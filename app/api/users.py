"""用户管理接口，提供管理员控制与个人资料维护。"""  # 模块说明
from __future__ import annotations  # 支持前向引用

import logging  # 引入日志方便记录安全敏感操作
import os  # 用于读取环境变量
from typing import Literal

from dotenv import load_dotenv, find_dotenv  # 用于加载环境变量
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status  # FastAPI 路由与异常
from sqlalchemy.orm import Session  # SQLAlchemy 会话类型

from app.api.deps import get_current_admin, get_current_user, get_db  # 导入认证与数据库依赖
from app.core.security import hash_password  # 密码哈希工具
from app.models.entities import User  # 引入实体类型用于类型提示
from app.repositories.chat_repo import ChatRepository  # 聊天仓储用于列出聊天
from app.repositories.user_repo import UserRepository  # 用户仓储用于CURD
from app.schemas.chat import ChatOut  # 聊天响应模型
from app.schemas.user import (  # 用户相关Schema
    AdminUserCreate,
    UserListResponse,
    UserOut,
    UserUpdate,
)
from app.services.password_guard import (  # 密码复杂度检测
    PASSWORD_POLICY_MESSAGE,
    is_password_compromised,
)

logger = logging.getLogger(__name__)  # 模块日志记录器
load_dotenv(find_dotenv())
INITIAL_ADMIN_EMAIL: str = os.getenv("INITIAL_ADMIN_EMAIL", "admin@example.com")
router = APIRouter(prefix="/users", tags=["users"])  # 定义用户路由分组


@router.post(
    "",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(get_current_admin)],
    responses={
        400: {"description": "邮箱重复", "content": {"application/json": {"example": {"detail": "邮箱已存在"}}}},
        401: {"description": "未认证", "content": {"application/json": {"example": {"detail": "无效的认证凭证"}}}},
        403: {"description": "权限不足", "content": {"application/json": {"example": {"detail": "需要管理员权限"}}}},
    },
)
async def create_user(payload: AdminUserCreate, db: Session = Depends(get_db)) -> UserOut:  # 定义管理员创建用户接口
    """管理员创建新用户，可指定是否为管理员。"""  # 接口说明
    repo = UserRepository(db)  # 初始化仓储
    email = payload.email.strip().lower()
    if repo.get_by_email(email):  # 检查邮箱是否存在
        logger.info("创建用户失败：邮箱重复", extra={"email": email})  # 记录失败日志
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已存在")  # 抛出400
    if is_password_compromised(payload.password):  # 检查密码是否在泄露名单
        logger.warning("创建用户失败：密码不符合复杂度要求", extra={"email": email})  # 记录安全事件
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=PASSWORD_POLICY_MESSAGE)  # 拒绝使用
    full_name = payload.full_name.strip() if payload.full_name else None
    if full_name == "":
        full_name = None
    hashed = hash_password(payload.password)  # 将明文密码哈希化
    user = repo.create_user(  # 写入数据库
        email=email,
        hashed_password=hashed,
        is_admin=payload.is_admin,
        full_name=full_name,
    )
    logger.info("管理员创建用户成功", extra={"user_id": user.id})  # 记录成功日志
    return UserOut.model_validate(user)  # 返回用户信息


@router.get(
    "",
    response_model=UserListResponse,
    responses={
        401: {"description": "未认证", "content": {"application/json": {"example": {"detail": "无效的认证凭证"}}}},
        403: {"description": "权限不足", "content": {"application/json": {"example": {"detail": "需要管理员权限或本人访问"}}}},
    },
)
async def list_users(  # 定义管理员分页查询用户接口
    limit: int = Query(20, ge=1, le=100, description="返回条目数"),  # 默认20条并限制最大100
    offset: int = Query(0, ge=0, description="偏移量"),  # 指定分页偏移
    q: str | None = Query(None, description="邮箱或姓名关键词"),  # 可选的模糊搜索关键词
    sort_by: Literal["created_at", "name", "email", "admin", "updated_at"] = Query(
        "created_at", description="排序字段"
    ),
    order: Literal["asc", "desc"] = Query("desc", description="排序方向"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),  # 注入数据库会话
) -> UserListResponse:  # 返回分页结构
    """管理员分页检索用户，可按关键词模糊查询。"""  # 接口说明
    repo = UserRepository(db)  # 初始化仓储
    if not current_user.is_admin:
        viewer = repo.get(current_user.id) or current_user
        return UserListResponse(
            items=[UserOut.model_validate(viewer)],
            total=1,
            limit=1,
            offset=0,
            sort_by="created_at",
            order="desc",
        )
    items, total = repo.list_with_total(
        limit=limit, offset=offset, keyword=q, sort_by=sort_by, order=order
    )  # 执行查询
    logger.info(
        "查询用户列表",
        extra={
            "limit": limit,
            "offset": offset,
            "keyword": q,
            "sort_by": sort_by,
            "order": order,
        },
    )  # 记录查询条件
    return UserListResponse(
        items=[UserOut.model_validate(u) for u in items],
        total=total,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        order=order,
    )  # 构造响应


@router.get(
    "/{user_id}",
    response_model=UserOut,
    responses={
        401: {"description": "未认证", "content": {"application/json": {"example": {"detail": "无效的认证凭证"}}}},
        403: {"description": "权限不足", "content": {"application/json": {"example": {"detail": "需要管理员权限或本人访问"}}}},
        404: {"description": "用户不存在", "content": {"application/json": {"example": {"detail": "用户不存在"}}}},
    },
)
async def read_user(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> UserOut:  # 定义读取单个用户接口
    """管理员或本人查询用户详情。"""  # 接口说明
    if not current_user.is_admin and current_user.id != user_id:  # 权限校验
        logger.warning("用户详情访问被拒绝", extra={"requester": current_user.id, "target": user_id})  # 记录权限拒绝
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限或本人访问")  # 抛出403
    repo = UserRepository(db)  # 初始化仓储
    user = repo.get(user_id)  # 查询用户
    if not user:  # 若不存在
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")  # 抛出404
    return UserOut.model_validate(user)  # 返回信息


@router.patch(
    "/{user_id}",
    response_model=UserOut,
    responses={
        401: {"description": "未认证", "content": {"application/json": {"example": {"detail": "无效的认证凭证"}}}},
        403: {"description": "权限不足", "content": {"application/json": {"example": {"detail": "无权修改该用户"}}}},
        404: {"description": "用户不存在", "content": {"application/json": {"example": {"detail": "用户不存在"}}}},
    },
)
async def update_user(
    user_id: int,  # 待更新的用户ID
    payload: UserUpdate,  # 更新数据载荷
    current_user: User = Depends(get_current_user),  # 当前登录用户用于权限判断
    db: Session = Depends(get_db),  # 注入数据库会话
) -> UserOut:  # 返回更新后的用户信息
    """管理员或本人更新资料，普通用户不能调整is_admin。"""  # 接口说明
    if not current_user.is_admin and current_user.id != user_id:  # 校验是否本人
        logger.warning("用户更新被拒绝", extra={"requester": current_user.id, "target": user_id})  # 记录失败
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改该用户")  # 抛出403
    if not current_user.is_admin and payload.is_admin is not None:  # 非管理员试图修改权限
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="普通用户不能修改权限")  # 拒绝操作
    repo = UserRepository(db)  # 仓储实例
    user = repo.get(user_id)  # 查询待更新用户
    if not user:  # 未找到
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")  # 抛出404
    changed = False
    if payload.email is not None:  # 更新邮箱
        email = payload.email.strip().lower()
        existing = repo.get_by_email(email)
        if existing and existing.id != user_id:
            logger.info(
                "更新用户失败：邮箱重复",
                extra={"target": user_id, "email": email},
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="邮箱已存在"
            )
        if email != user.email:
            user.email = email
            changed = True
    if payload.full_name is not None:  # 提供新姓名
        full_name = payload.full_name.strip()
        normalized_name = full_name or None
        if normalized_name != user.full_name:
            user.full_name = normalized_name
            changed = True
    if payload.password is not None:  # 提供新密码
        if is_password_compromised(payload.password):  # 校验密码安全性
            logger.warning("拒绝使用不符合复杂度的密码更新账号", extra={"user_id": user_id})  # 记录安全日志
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=PASSWORD_POLICY_MESSAGE)  # 拒绝
        user.hashed_password = hash_password(payload.password)  # 哈希后更新
        changed = True
    if current_user.is_admin and payload.is_admin is not None:  # 仅管理员可改权限
        if (
            user.id == current_user.id
            and user.is_admin
            and payload.is_admin is False
        ):  # 禁止管理员自降权限
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="管理员不能取消自己的管理员身份",
            )
        if user.is_admin != payload.is_admin:
            user.is_admin = payload.is_admin  # 设置权限
            changed = True
    if not changed:  # 若无可更新字段
        return UserOut.model_validate(user)  # 直接返回原数据
    repo.db.add(user)
    repo.db.flush()
    logger.info("用户资料已更新", extra={"user_id": user_id, "by": current_user.id})  # 记录成功
    return UserOut.model_validate(user)  # 返回最新信息


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"description": "未认证", "content": {"application/json": {"example": {"detail": "无效的认证凭证"}}}},
        403: {"description": "权限不足", "content": {"application/json": {"example": {"detail": "需要管理员权限"}}}},
        404: {"description": "用户不存在", "content": {"application/json": {"example": {"detail": "用户不存在"}}}},
    },
)
async def delete_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> Response:  # 定义删除用户接口
    """管理员删除用户，触发级联清理聊天与消息。"""  # 接口说明
    repo = UserRepository(db)  # 仓储实例
    user = repo.get(user_id)  # 查询用户
    if not user:  # 未找到
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")  # 返回404保证幂等语义
    if user.is_admin:  # 删除管理员需要额外限制
        if user.email == INITIAL_ADMIN_EMAIL:  # 初始管理员不允许删除
            logger.warning(
                "尝试删除初始管理员账号被拒绝", extra={"requester": current_admin.id, "target": user_id}
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="初始管理员账号不允许删除")
        if current_admin.email != INITIAL_ADMIN_EMAIL:  # 非初始管理员删除管理员账号
            logger.warning(
                "非初始管理员尝试删除管理员账号", extra={"requester": current_admin.id, "target": user_id}
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅初始管理员可以删除管理员账号")
    repo.delete(user_id)  # 删除用户，依赖数据库ON DELETE CASCADE清理聊天和消息
    logger.info("管理员删除用户", extra={"user_id": user_id})  # 记录日志
    return Response(status_code=status.HTTP_204_NO_CONTENT)  # 返回空响应


@router.get(
    "/{user_id}/chats",
    response_model=list[ChatOut],
    responses={
        401: {"description": "未认证", "content": {"application/json": {"example": {"detail": "无效的认证凭证"}}}},
        403: {"description": "权限不足", "content": {"application/json": {"example": {"detail": "需要管理员权限或本人访问"}}}},
    },
)
async def list_user_chats(
    user_id: int,  # 目标用户ID
    current_user: User = Depends(get_current_user),  # 当前用户用于权限校验
    db: Session = Depends(get_db),  # 注入数据库会话
    limit: int = Query(50, ge=1, le=200, description="最大返回聊天数"),  # 默认50条，最大200
    offset: int = Query(0, ge=0, description="偏移量"),  # 聊天记录偏移量
) -> list[ChatOut]:  # 返回聊天列表
    """根据用户ID列出聊天，会校验访问权限。"""  # 接口说明
    if not current_user.is_admin and current_user.id != user_id:  # 权限校验
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限或本人访问")  # 拒绝访问
    chats = ChatRepository(db).list_by_user(user_id=user_id, offset=offset, limit=limit)  # 查询聊天
    return [ChatOut.model_validate(chat) for chat in chats]  # 转换为响应模型

