from fastapi import FastAPI
from app.api import domains, chats

app = FastAPI(title="RAG Backend (Minimal)")

# 路由分组
app.include_router(domains.router)
app.include_router(chats.router)

@app.get("/healthz")
def healthz():
    return {"ok": True}

