"""FastAPI 应用入口。"""
import logging  # 提前配置日志模块

from fastapi import FastAPI  # 导入FastAPI主体

from app.api import domains, chats  # 导入既有路由
from app.api import documents  # 新增文档路由

logging.basicConfig(level=logging.INFO)  # 简单配置日志等级方便调试

app = FastAPI(title="RAG Backend")  # 初始化应用实例
app.router.redirect_slashes = True  # 启用斜杠自动兼容，满足/domains与/domains/一致

app.include_router(domains.router)  # 注册domain相关接口
app.include_router(chats.router)  # 注册聊天相关接口
app.include_router(documents.router)  # 注册文档及chunk相关接口


@app.get("/healthz")
def healthz():
    """健康检查端点。"""
    return {"ok": True}  # 简单返回ok字段
    # 设计说明：健康检查用于k8s探活，保持实现极简。
