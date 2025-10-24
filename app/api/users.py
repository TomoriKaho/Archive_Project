"""用户管理接口，提供管理员控制与个人资料维护。"""  # 模块说明
from __future__ import annotations  # 支持前向引用

import logging  # 引入日志方便记录安全敏感操作
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

logger = logging.getLogger(__name__)  # 模块日志记录器

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
    if repo.get_by_email(payload.email):  # 检查邮箱是否存在
        logger.info("创建用户失败：邮箱重复", extra={"email": payload.email})  # 记录失败日志
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已存在")  # 抛出400
    hashed = hash_password(payload.password)  # 将明文密码哈希化
    user = repo.create_user(  # 写入数据库
        email=payload.email,
        hashed_password=hashed,
        is_admin=payload.is_admin,
        full_name=payload.full_name,
    )
    logger.info("管理员创建用户成功", extra={"user_id": user.id})  # 记录成功日志
    return UserOut.model_validate(user)  # 返回用户信息


@router.get(
    "",
    response_model=UserListResponse,
    dependencies=[Depends(get_current_admin)],
    responses={
        401: {"description": "未认证", "content": {"application/json": {"example": {"detail": "无效的认证凭证"}}}},
        403: {"description": "权限不足", "content": {"application/json": {"example": {"detail": "需要管理员权限"}}}},
    },
)
async def list_users(  # 定义管理员分页查询用户接口
    limit: int = Query(20, ge=1, le=100, description="返回条目数"),  # 默认20条并限制最大100
    offset: int = Query(0, ge=0, description="偏移量"),  # 指定分页偏移
    q: str | None = Query(None, description="邮箱或姓名关键词"),  # 可选的模糊搜索关键词
    db: Session = Depends(get_db),  # 注入数据库会话
) -> UserListResponse:  # 返回分页结构
    """管理员分页检索用户，可按关键词模糊查询。"""  # 接口说明
    repo = UserRepository(db)  # 初始化仓储
    items, total = repo.list_with_total(limit=limit, offset=offset, keyword=q)  # 执行查询
    logger.info("查询用户列表", extra={"limit": limit, "offset": offset, "keyword": q})  # 记录查询条件
    return UserListResponse(items=[UserOut.model_validate(u) for u in items], total=total, limit=limit, offset=offset)  # 构造响应


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
    update_data = {}  # 收集需要更新的字段
    if payload.full_name is not None:  # 提供新姓名
        update_data["full_name"] = payload.full_name  # 写入
    if payload.password is not None:  # 提供新密码
        update_data["hashed_password"] = hash_password(payload.password)  # 哈希后更新
    if current_user.is_admin and payload.is_admin is not None:  # 仅管理员可改权限
        update_data["is_admin"] = payload.is_admin  # 设置权限
    if not update_data:  # 若无可更新字段
        return UserOut.model_validate(user)  # 直接返回原数据
    updated = repo.update(user, **update_data)  # 执行更新
    logger.info("用户资料已更新", extra={"user_id": user_id, "by": current_user.id})  # 记录成功
    return UserOut.model_validate(updated)  # 返回最新信息


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_admin)],
    responses={
        401: {"description": "未认证", "content": {"application/json": {"example": {"detail": "无效的认证凭证"}}}},
        403: {"description": "权限不足", "content": {"application/json": {"example": {"detail": "需要管理员权限"}}}},
        404: {"description": "用户不存在", "content": {"application/json": {"example": {"detail": "用户不存在"}}}},
    },
)
async def delete_user(user_id: int, db: Session = Depends(get_db)) -> Response:  # 定义删除用户接口
    """管理员删除用户，触发级联清理聊天与消息。"""  # 接口说明
    repo = UserRepository(db)  # 仓储实例
    user = repo.get(user_id)  # 查询用户
    if not user:  # 未找到
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")  # 返回404保证幂等语义
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


# 设计说明：用户路由严格区分管理员与普通用户操作范围，删除时依赖级联策略保持数据一致，同时提供分页能力满足管理后台需求。
