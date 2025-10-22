from fastapi import FastAPI

from app.api import auth, chats, domains, users

app = FastAPI(title="RAG Backend")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(domains.router)
app.include_router(chats.router)

@app.get("/healthz")
def healthz():
    return {"ok": True}

