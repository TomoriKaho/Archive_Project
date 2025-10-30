"""FastAPI 应用入口。"""
import logging  # 提前配置日志模块

from fastapi import FastAPI  # 导入FastAPI主体
from fastapi.middleware.cors import CORSMiddleware  # 引入CORS中间件处理跨域预检请求

from app.api import domains, chats, documents, auth, users  # 导入各功能路由模块
from app.api import rag as rag_router  # RAG 相关路由
from app.db.schema_compat import ensure_document_uuid_column  # 旧库兼容补丁
from app.db.session import SessionLocal, engine  # 提供数据库连接引擎
from app.services.initial_admin import ensure_initial_admin  # 启动时确保初始管理员存在

logging.basicConfig(level=logging.INFO)  # 简单配置日志等级方便调试

app = FastAPI(title="RAG Backend")  # 初始化应用实例
app.router.redirect_slashes = True  # 启用斜杠自动兼容，满足/domains与/domains/一致

# CORS配置允许浏览器发送OPTIONS预检请求，避免前端出现405错误
app.add_middleware(
    CORSMiddleware,  # 使用Starlette提供的中间件
    allow_origins=["*"],  # 允许任意来源访问，前后端分离调试更方便
    allow_credentials=True,  # 允许携带Cookie或认证头，配合JWT使用
    allow_methods=["*"],  # 允许所有HTTP方法，确保POST/DELETE等均可跨域
    allow_headers=["*"]  # 允许所有自定义请求头，满足Authorization等需求
)

app.include_router(domains.router)
app.include_router(chats.router)
app.include_router(documents.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(rag.router)


@app.on_event("startup")
def _ensure_schema_compatibility() -> None:
    """在服务启动时自动修补旧版本数据库缺失的列。"""
    ensure_document_uuid_column(engine)


@app.on_event("startup")
def _ensure_initial_admin() -> None:
    """服务启动时自动注入初始管理员账号（若不存在）。"""
    session = SessionLocal()
    try:
        ensure_initial_admin(session)
        session.commit()
    except Exception:  # pragma: no cover - 保留完整回滚流程
        session.rollback()
        raise
    finally:
        session.close()


@app.get("/healthz")
def healthz():
    """健康检查端点。"""
    return {"ok": True}  # 简单返回ok字段
