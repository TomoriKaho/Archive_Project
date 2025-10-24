"""FastAPI 依赖定义，提供数据库会话与身份校验。"""  # 模块注释概述职责
from __future__ import annotations  # 启用未来注解以支持类型前向引用

import logging  # 引入日志模块便于记录认证相关操作
from collections.abc import Generator  # 导入生成器类型用于描述依赖返回值

from fastapi import Depends, HTTPException, status  # FastAPI 提供依赖注入与错误响应的工具
from fastapi.security import OAuth2PasswordBearer  # OAuth2 密码模式实现，用于解析 Authorization 头
from sqlalchemy.orm import Session  # SQLAlchemy 会话类型

from app.core.security import decode_access_token  # JWT 解析工具
from app.db.session import SessionLocal  # 数据库会话工厂
from app.models.entities import User  # 用户实体类型，用于类型提示
from app.repositories.user_repo import UserRepository  # 用户仓储封装数据库操作

logger = logging.getLogger(__name__)  # 获取模块级日志记录器

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")  # 定义OAuth2密码模式入口，供依赖读取token


def get_db() -> Generator[Session, None, None]:  # 定义数据库会话依赖
    """在请求生命周期内提供一个数据库会话，并保证提交或回滚。"""  # 说明依赖作用
    db = SessionLocal()  # 从会话工厂创建新的Session实例
    try:  # 尝试执行调用方逻辑
        yield db  # 将数据库会话提供给依赖消费者
        db.commit()  # 若上层无异常则提交事务
    except Exception:  # 捕获所有异常以进行回滚
        db.rollback()  # 发生错误时回滚事务保持数据一致性
        raise  # 继续向外抛出异常让FastAPI处理
    finally:  # 无论是否异常都执行善后
        db.close()  # 关闭会话释放连接资源


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:  # 定义获取当前用户依赖
    """从Bearer Token解析并返回当前登录用户。"""  # 描述依赖的职责
    try:  # 捕获可能的token解析异常
        payload = decode_access_token(token)  # 调用安全工具解析JWT
    except ValueError:  # 若解析失败
        logger.warning("token 解码失败，拒绝访问")  # 记录警告便于审计
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证凭证")  # 返回401提示需要认证
    user_id = payload.get("sub")  # 从JWT载荷中提取用户ID
    if user_id is None:  # 如果不存在sub声明
        logger.warning("token 缺少 sub 字段")  # 记录问题
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="认证信息不完整")  # 返回401
    repo = UserRepository(db)  # 初始化用户仓储执行查询
    user = repo.get(int(user_id))  # 根据主键获取用户对象
    if user is None:  # 如果用户不存在（可能已被删除）
        logger.warning("token 对应的用户已不存在")  # 记录该安全异常
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已被删除")  # 返回401以提示重新登录
    return user  # 返回通过认证的用户对象


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:  # 定义管理员校验依赖
    """校验当前用户是否具备管理员权限，未通过则抛出403。"""  # 描述依赖功能
    if not current_user.is_admin:  # 检查用户的管理员标志
        logger.warning("非管理员访问受限接口被拒绝")  # 记录权限拒绝事件
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")  # 抛出403禁止访问
    return current_user  # 返回管理员用户供路由继续使用


# 设计说明：通过依赖拆分数据库和认证逻辑，既复用Session管理又集中处理权限控制，保持路由层代码简洁可测。
