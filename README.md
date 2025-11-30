# Archive Project

为外国语学院开发的档案库RAG问答系统。
基于 **FastAPI** 的文档管理与对话服务 + **Vue 3 (Vue CLI)** 管理端（`frontend_admin`）与客户端（`frontend_client`）前端。

---

## 目录
- [Archive Project](#archive-project)
  - [目录](#目录)
  - [一、环境要求](#一环境要求)
  - [二、环境变量（统一清单）](#二环境变量统一清单)
    - [后端（根目录 `.env`）](#后端根目录-env)
    - [管理端前端（`frontend_admin/.env.local`）](#管理端前端frontend_adminenvlocal)
    - [客户端前端（`frontend_client/.env.local`）](#客户端前端frontend_clientenvlocal)
  - [三、快速启动（后端 + 依赖服务 + 前端）](#三快速启动后端--依赖服务--前端)
    - [1) 克隆仓库 \& Python 依赖](#1-克隆仓库--python-依赖)
    - [2) 配置环境变量](#2-配置环境变量)
    - [3) 启动依赖服务（Docker）](#3-启动依赖服务docker)
    - [4) 迁移数据库](#4-迁移数据库)
    - [5) 启动后端（FastAPI）](#5-启动后端fastapi)
    - [6) 启动前端（Vue CLI）](#6-启动前端vue-cli)
  - [四、常用命令](#四常用命令)
  - [五、RAG 相关](#五rag-相关)
  - [六、故障排查速记](#六故障排查速记)

---

## 一、环境要求
- **Python** ≥ 3.11（建议 3.11/3.12）
- **Node.js / npm**（建议使用 nvm 安装 LTS 版）
- **Docker**（用于 PostgreSQL / Qdrant）

---

## 二、环境变量（统一清单）

> 后端读取项目根目录的 `.env`；管理端前端读取 `frontend_admin/.env.local`；客户端前端读取 `frontend_client/.env.local`。

### 后端（根目录 `.env`）
```dotenv
# 数据库 & 向量库
DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/mydb
QDRANT_URL=http://localhost:6333

# 认证
JWT_SECRET_KEY=change-me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
INITIAL_ADMIN_EMAIL=admin@example.com
ADMIN_INIT_PASSWORD=ChangeMe123

# RAG（如未使用可先保留默认）
QDRANT_COLLECTION=VOC_Archives
OLLAMA_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=qwen3-embedding:8b
OLLAMA_CHAT_MODEL=llama3.1:8b
RAG_TOP_K=10
RAG_OLLAMA_TIMEOUT=60
RAG_CHUNK_MEMORY_WINDOW_MULTIPLIER=3

# 向量入库批量配置
DOCUMENT_INDEX_BATCH_SIZE=32

# CSV 解析
CSV_FIELD_SIZE_LIMIT=10485760
```

> 使 `.env` 生效（仅当前 shell）：
```bash
set -a && source .env && set +a
```

### 管理端前端（`frontend_admin/.env.local`）
```dotenv
# 后端 API 基地址（保持与后端 uvicorn 端口一致）
VUE_APP_API_BASE_URL=http://localhost:8000/api
# 前端本地存储的 Token 键名
VUE_APP_TOKEN_STORAGE_KEY=archive_ai_admin_token
```

### 客户端前端（`frontend_client/.env.local`）
```dotenv
# 后端 API 基地址（保持与后端 uvicorn 端口一致）
VUE_APP_API_BASE_URL=http://localhost:8000/api
# 前端本地存储的 Token 键名
VUE_APP_TOKEN_STORAGE_KEY=archive_ai_client_token
```

---

## 三、快速启动（后端 + 依赖服务 + 前端）

### 1) 克隆仓库 & Python 依赖
```bash
git clone git@github.com:TomoriKaho/Archive_Project.git
cd Archive_Project
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) 配置环境变量
- 在仓库根目录创建并编辑 `.env`（见上文“后端 .env”示例）。
- 可选：`set -a && source .env && set +a` 让当前终端生效。

### 3) 启动依赖服务（Docker）
```bash
# PostgreSQL（一次性创建容器，后续仅需 docker start rag-pg）
docker run --name rag-pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres
# Qdrant（同理，一次性创建容器）
docker run -d --name qdrant \
  -p 6333:6333 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  -e QDRANT__SERVICE__USER__UID=$(id -u) \
  -e QDRANT__SERVICE__USER__GID=$(id -g) \
  qdrant/qdrant
```

> 之后重启服务可用：`docker start rag-pg && docker start qdrant`

### 4) 迁移数据库
```bash
alembic upgrade head
```

### 5) 启动后端（FastAPI）
```bash

# 默认监听 http://localhost:8000
```

### 6) 启动前端（Vue CLI）
```bash
# 管理端前端
cd frontend_admin
npm install           # 首次安装依赖
npm run serve         # 启动管理端（默认 http://localhost:8080）

# 客户端前端（建议另开终端）
cd frontend_client
npm install           # 首次安装依赖
npm run serve         # 启动客户端（默认 http://localhost:8081）
```

> 首次访问请确认后端已启动；如需同时运行两个前端，建议分别占用 8080/8081 端口。

---

## 四、常用命令

**后端**
```bash
# 运行后端
uvicorn app.main:app --reload

# 重新应用迁移
alembic upgrade head

# 恢复初始管理员（如误删）
python -m app.scripts.bootstrap_admin
```

**管理端前端（在 `frontend_admin/` 目录）**
```bash
npm run serve     # 开发
npm run build     # 生产打包（输出到 frontend_admin/dist/）
```

**客户端前端（在 `frontend_client/` 目录）**
```bash
npm run serve     # 开发
npm run build     # 生产打包（输出到 frontend_client/dist/）
```

**容器**
```bash
docker start rag-pg qdrant
docker logs -f rag-pg
docker logs -f qdrant
```

---

## 五、RAG 相关

```bash
# 启动/准备 Ollama（本机）
ollama serve &
ollama pull qwen3-embedding:8b
ollama pull llama3.1:8b
```

**示例调用**
```bash
# 将某文档向量写入 Qdrant（如实现了对应路由）
curl -X POST http://localhost:8000/rag/ingest/42

# 在 chat 中触发 RAG 生成
token="<Bearer JWT>"
curl -X POST http://localhost:8000/chats/7/messages \
     -H 'Content-Type: application/json' \
     -H "Authorization: Bearer $token" \
     -d '{"role":"user","content":"Ask something","top_k":8,"domain_ids":[3]}'
```

> `RAG_CHUNK_MEMORY_WINDOW_MULTIPLIER` 决定多轮对话中保留的历史检索片段数量，
> 其值会与 `top_k` 相乘，控制滑动窗口的大小。

> `DOCUMENT_INDEX_BATCH_SIZE` 控制单次向量化/入库的 chunk 批量大小，数值越大单次请求的向量越多；
> 若 Qdrant 或嵌入服务在大批量写入时容易超时，可适当调小该值。

---

## 六、故障排查速记
- **`npm: command not found`**：先安装 Node.js（推荐 nvm 安装 LTS），再进入对应前端目录执行 `npm install`。
- **前端 404 或无法登录**：确认 `frontend_admin/.env.local` / `frontend_client/.env.local` 的 `VUE_APP_API_BASE_URL` 指向后端；同时确认后端 `uvicorn` 正常运行。
- **数据库连接失败**：检查 `DATABASE_URL`、Postgres 容器是否启动、端口是否占用。
- **Qdrant 写入/查询失败**：检查 `QDRANT_URL`、容器是否正常、集合名与代码一致。
- **管理员缺失**：运行 `python -m app.scripts.bootstrap_admin` 重新注入。

---
