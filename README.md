# Archive Project

为外国语学院开发的档案库RAG问答系统。
基于 **FastAPI** 的文档管理与对话服务 + **Vue 3 (Vue CLI)** 管理端（`frontend_admin`）与客户端（`frontend_client`）前端。

---

## 目录
- [Archive Project](#archive-project)
  - [目录](#目录)
  - [CentOS 一键启动（Docker Compose）](#centos-一键启动docker-compose)
    - [1) 安装 Docker 与 Compose](#1-安装-docker-与-compose)
    - [2) 放行防火墙端口](#2-放行防火墙端口)
    - [3) 快速启动](#3-快速启动)
    - [4) 常见问题排查](#4-常见问题排查)
    - [5) 停止与清理](#5-停止与清理)
  - [Ubuntu 一键启动（Docker Compose）](#ubuntu-一键启动docker-compose)
    - [1) 安装 Docker 与 Compose](#1-安装-docker-与-compose-1)
    - [2) 放行防火墙端口](#2-放行防火墙端口-1)
    - [3) 快速启动](#3-快速启动-1)
    - [4) 常见问题排查](#4-常见问题排查-1)
    - [5) 停止与清理](#5-停止与清理-1)
  - [零、新服务器初始化（Docker/Python/Node）](#零新服务器初始化dockerpythonnode)
  - [一、环境要求](#一环境要求)
  - [二、环境变量（统一清单）](#二环境变量统一清单)
    - [后端（根目录 `.env`）](#后端根目录-env)
    - [管理端前端（`frontend_admin/.env.local`）](#管理端前端frontend_adminenvlocal)
    - [客户端前端（`frontend_client/.env.local`）](#客户端前端frontend_clientenvlocal)
  - [三、快速启动（Docker Compose 一键启动）](#三快速启动docker-compose-一键启动)
    - [1) 准备环境变量](#1-准备环境变量)
    - [2) 一键启动](#2-一键启动)
    - [3) 停止或重启](#3-停止或重启)
  - [四、手动启动（后端 + 依赖服务 + 前端）](#四手动启动后端--依赖服务--前端)
    - [1) 克隆仓库 \& Python 依赖](#1-克隆仓库--python-依赖)
    - [2) 配置环境变量](#2-配置环境变量)
    - [3) 启动依赖服务（Docker）](#3-启动依赖服务docker)
    - [4) 迁移数据库](#4-迁移数据库)
    - [5) 启动后端（FastAPI）](#5-启动后端fastapi)
    - [6) 启动前端（Vue CLI）](#6-启动前端vue-cli)
  - [五、常用命令](#五常用命令)
  - [六、RAG 相关](#六rag-相关)
  - [七、故障排查速记](#七故障排查速记)

---

## CentOS 一键启动（Docker Compose）

> 适用于 CentOS 7/8/Stream。使用 `docker compose up -d --build` 一键拉起 PostgreSQL、Qdrant、Ollama、后端与两个前端。

### 1) 安装 Docker 与 Compose

**CentOS 7（yum）示例：**
```bash
sudo yum install -y yum-utils ca-certificates curl
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
```

**CentOS 8/Stream（dnf）示例：**
```bash
sudo dnf install -y dnf-plugins-core ca-certificates curl
sudo dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
```

> 可选：将当前用户加入 docker 组避免每次 sudo：
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### 2) 放行防火墙端口

按默认端口放行（如有修改请同步调整）：
- 后端：18000
- 管理端：8080
- 客户端：8081
- PostgreSQL：5432
- Qdrant：6333
- Ollama：11434

firewalld 示例：
```bash
sudo firewall-cmd --permanent --add-port=18000/tcp
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --permanent --add-port=8081/tcp
sudo firewall-cmd --permanent --add-port=5432/tcp
sudo firewall-cmd --permanent --add-port=6333/tcp
sudo firewall-cmd --permanent --add-port=11434/tcp
sudo firewall-cmd --reload
```

> 云服务器还需要在安全组中放行上述端口。

### 3) 快速启动

```bash
git clone git@github.com:TomoriKaho/Archive_Project.git
cd Archive_Project
cp .env.example .env
```

编辑 `.env`（必须与 compose 使用的 `../.env` 保持一致）：  
- 数据库：`DATABASE_URL`、`POSTGRES_*`
- Qdrant：`QDRANT_URL=http://qdrant:6333`
- Ollama：`OLLAMA_BASE_URL=http://ollama:11434`
- 模型列表：`OLLAMA_MODELS=qwen3-embedding:8b`（逗号分隔）
- 前端调用后端：`VUE_APP_API_BASE_URL=http://<服务器IP>:18000/api`

启动：
```bash
docker compose up -d --build
```

查看状态与日志：
```bash
docker compose ps
docker compose logs -f backend
```

### 4) 常见问题排查

- **后端连不上 postgres/qdrant/ollama**：确认 `.env` 中 `DATABASE_URL/QDRANT_URL/OLLAMA_BASE_URL` 均指向 compose 内服务名（postgres/qdrant/ollama），并查看 `backend` 日志。
- **alembic 迁移失败**：检查 `alembic.ini` 与 `migrations/versions` 是否存在，确保数据库账号权限正确。
- **Ollama 拉模型失败或过慢**：可再次运行 `docker compose up -d ollama_init` 触发重试；必要时更换更小模型或手动 `docker exec -it archive-ollama ollama pull <model>`.
- **前端访问不到后端**：确认 `VUE_APP_API_BASE_URL` 指向宿主机 IP（不要写 `backend:18000`），同时检查后端端口与 CORS 设置。
- **容器监听 127.0.0.1 的问题**：本仓库已强制监听 `0.0.0.0`，若自行改动请确保仍为 0.0.0.0。

### 5) 停止与清理

```bash
docker compose down
```

> 如需清空数据库/向量库/Ollama 模型，请谨慎使用（会删除卷数据）：
```bash
docker compose down -v
```

---

## Ubuntu 一键启动（Docker Compose）

> 适用于 Ubuntu 20.04/22.04/24.04。使用 `docker compose up -d --build` 一键拉起 PostgreSQL、Qdrant、Ollama、后端与两个前端。

### 1) 安装 Docker 与 Compose

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
```

> 可选：将当前用户加入 docker 组避免每次 sudo：
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### 2) 放行防火墙端口

如果启用了 UFW，请放行（如有修改请同步调整）：
```bash
sudo ufw allow 18000/tcp
sudo ufw allow 8080/tcp
sudo ufw allow 8081/tcp
sudo ufw allow 5432/tcp
sudo ufw allow 6333/tcp
sudo ufw allow 11434/tcp
sudo ufw reload
```

> 云服务器还需要在安全组中放行上述端口。

### 3) 快速启动

```bash
git clone git@github.com:TomoriKaho/Archive_Project.git
cd Archive_Project
cp .env.example .env
```

编辑 `.env`（必须与 compose 使用的 `../.env` 保持一致）：  
- 数据库：`DATABASE_URL`、`POSTGRES_*`
- Qdrant：`QDRANT_URL=http://qdrant:6333`
- Ollama：`OLLAMA_BASE_URL=http://ollama:11434`
- 模型列表：`OLLAMA_MODELS=qwen3-embedding:8b`（逗号分隔）
- 前端调用后端：`VUE_APP_API_BASE_URL=http://<服务器IP>:18000/api`

启动：
```bash
docker compose up -d --build
```

查看状态与日志：
```bash
docker compose ps
docker compose logs -f backend
```

### 4) 常见问题排查

- **后端连不上 postgres/qdrant/ollama**：确认 `.env` 中 `DATABASE_URL/QDRANT_URL/OLLAMA_BASE_URL` 均指向 compose 内服务名（postgres/qdrant/ollama），并查看 `backend` 日志。
- **alembic 迁移失败**：检查 `alembic.ini` 与 `migrations/versions` 是否存在，确保数据库账号权限正确。
- **Ollama 拉模型失败或过慢**：可再次运行 `docker compose up -d ollama_init` 触发重试；必要时更换更小模型或手动 `docker exec -it archive-ollama ollama pull <model>`.
- **前端访问不到后端**：确认 `VUE_APP_API_BASE_URL` 指向宿主机 IP（不要写 `backend:18000`），同时检查后端端口与 CORS 设置。
- **容器监听 127.0.0.1 的问题**：本仓库已强制监听 `0.0.0.0`，若自行改动请确保仍为 0.0.0.0。

### 5) 停止与清理

```bash
docker compose down
```

> 如需清空数据库/向量库/Ollama 模型，请谨慎使用（会删除卷数据）：
```bash
docker compose down -v
```

---

## 零、新服务器初始化（Docker/Python/Node）

以下命令假设使用 Ubuntu 22.04/24.04：

1. 更新基础软件并安装常用工具：
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y git curl build-essential ca-certificates
   ```
2. 安装 Python（本地调试或运行脚本时使用）：
   ```bash
   sudo apt install -y python3.11 python3.11-venv python3-pip
   ```
3. 安装 Docker Engine 与 Compose 插件：
   ```bash
   sudo install -m 0755 -d /etc/apt/keyrings
   curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
   echo \
     "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
     $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
     sudo tee /etc/apt/sources.list.d/docker.list
   sudo apt update
   sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

   # （国内可选）配置 Docker Hub 加速镜像
   sudo mkdir -p /etc/docker
   cat <<'EOF' | sudo tee /etc/docker/daemon.json
   {
     "registry-mirrors": ["https://mirror.ccs.tencentyun.com"]
   }
   EOF
   sudo systemctl restart docker

   # 可选：将当前用户加入 docker 组，避免每次 sudo
   sudo usermod -aG docker $USER
   newgrp docker
   ```
4. （可选）安装 Node.js 以在宿主机调试前端：
   ```bash
   curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
   sudo apt install -y nodejs
   ```

完成上述步骤后即可使用 `docker compose` 运行项目，或按需使用 Python/Node 进行本地开发。

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
# 云端聊天模型
CHAT_API_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
CHAT_API_KEY=HJpyYd3ZqeaWt5FN9rY9WURwqvZ5L8
CHAT_MODEL=qwen-plus
RAG_TOP_K=10
RAG_OLLAMA_TIMEOUT=60
RAG_CHUNK_MEMORY_WINDOW_MULTIPLIER=3

# 机器翻译（传统搜索启用中文搜索时使用）
TRANSLATION_API_URL=https://dashscope.aliyuncs.com/api/v1/services/aigc/machine-translation
TRANSLATION_API_KEY=sk-your-translation-api-key
TRANSLATION_MODEL=qwen-mt-lite
TRANSLATION_API_TIMEOUT=20

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
VUE_APP_API_BASE_URL=http://localhost:18000/api
# 前端本地存储的 Token 键名
VUE_APP_TOKEN_STORAGE_KEY=archive_ai_admin_token
```

### 客户端前端（`frontend_client/.env.local`）
```dotenv
# 后端 API 基地址（保持与后端 uvicorn 端口一致）
VUE_APP_API_BASE_URL=http://localhost:18000/api
# 前端本地存储的 Token 键名
VUE_APP_TOKEN_STORAGE_KEY=archive_ai_client_token
```

---

## 三、快速启动（Docker Compose 一键启动）

> 适合在新服务器上快速拉起整套服务（后端 + PostgreSQL + Qdrant + 两个前端）。

### 1) 准备环境变量

- 复制 `.env.example` 为 `.env`，并将数据库、向量库地址指向 compose 内的服务：
  ```dotenv
  DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/mydb
  QDRANT_URL=http://qdrant:6333
  ```
- 在 `frontend_admin/.env.local` 和 `frontend_client/.env.local` 中设置 API 地址指向后端容器：
  ```dotenv
  VUE_APP_API_BASE_URL=http://backend:18000/api
  VUE_APP_TOKEN_STORAGE_KEY=archive_ai_admin_token   # 管理端示例
  ```
  客户端可将 `VUE_APP_TOKEN_STORAGE_KEY` 改为 `archive_ai_client_token`（或保持默认）。

### 2) 一键启动

```bash
docker compose up -d
```

- 首次会自动拉取镜像并安装依赖，完成后服务端口：
  - 后端 API：`http://<服务器IP>:18000`（Swagger 文档在 `/docs`）
  - 管理端前端：`http://<服务器IP>:8080`
  - 客户端前端：`http://<服务器IP>:8081`
- 查看单个服务日志：`docker compose logs -f backend`（其他服务同理）。

### 3) 停止或重启

```bash
docker compose stop          # 停止所有容器
docker compose start         # 重新启动
docker compose down          # 停止并移除容器（保留卷数据）
```

> 需要更新依赖或代码时，可 `docker compose down` 后重新 `docker compose up -d`，卷会保留数据库与向量库数据。

---

## 四、手动启动（后端 + 依赖服务 + 前端）

### 1) 克隆仓库 & Python 依赖
```bash
git clone git@github.com:TomoriKaho/Archive_Project.git
cd Archive_Project
python3 -m venv .venv
source .venv/bin/activate
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

### 2) 配置环境变量
- 在仓库根目录创建并编辑 `.env`（见上文“后端 .env”示例）。
- 可选：`set -a && source .env && set +a` 让当前终端生效。

### 3) 启动依赖服务（Docker）
```bash
# PostgreSQL（一次性创建容器，后续仅需 docker start rag-pg）
docker run --name rag-pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d mirrors.tencent.com/library/postgres:15
# Qdrant（同理，一次性创建容器）
docker run -d --name qdrant \
  -p 6333:6333 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  -e QDRANT__SERVICE__USER__UID=$(id -u) \
  -e QDRANT__SERVICE__USER__GID=$(id -g) \
  mirrors.tencent.com/qdrant/qdrant:latest
```

> 之后重启服务可用：`docker start rag-pg && docker start qdrant`

### 4) 迁移数据库
```bash
alembic upgrade head
```

### 5) 启动后端（FastAPI）
```bash
uvicorn app.main:app --reload
# 默认监听 http://localhost:18000
```

### 6) 启动前端（Vue CLI）
```bash
# 管理端前端
cd frontend_admin
npm config set registry https://registry.npmmirror.com
npm install           # 首次安装依赖
npm run serve         # 启动管理端（默认 http://localhost:8080）

# 客户端前端（建议另开终端）
cd frontend_client
npm config set registry https://registry.npmmirror.com
npm install           # 首次安装依赖
npm run serve         # 启动客户端（默认 http://localhost:8081）
```

> 首次访问请确认后端已启动；如需同时运行两个前端，建议分别占用 8080/8081 端口。

---

## 五、常用命令

**后端**
```bash
# 运行后端
uvicorn app.main:app --reload --host 0.0.0.0 --port 18000

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

## 六、RAG 相关

```bash
# 启动/准备 Ollama（本机）
ollama serve &
ollama pull qwen3-embedding:8b
```

**示例调用**
```bash
# 将某文档向量写入 Qdrant（如实现了对应路由）
curl -X POST http://localhost:18000/rag/ingest/42

# 在 chat 中触发 RAG 生成
token="<Bearer JWT>"
curl -X POST http://localhost:18000/chats/7/messages \
     -H 'Content-Type: application/json' \
     -H "Authorization: Bearer $token" \
     -d '{"role":"user","content":"Ask something","top_k":8,"domain_ids":[3]}'
```

> `RAG_CHUNK_MEMORY_WINDOW_MULTIPLIER` 决定多轮对话中保留的历史检索片段数量，
> 其值会与 `top_k` 相乘，控制滑动窗口的大小。

> `DOCUMENT_INDEX_BATCH_SIZE` 控制单次向量化/入库的 chunk 批量大小，数值越大单次请求的向量越多；
> 若 Qdrant 或嵌入服务在大批量写入时容易超时，可适当调小该值。

---

## 七、故障排查速记
- **`npm: command not found`**：先安装 Node.js（推荐 nvm 安装 LTS），再进入对应前端目录执行 `npm install`。
- **前端 404 或无法登录**：确认 `frontend_admin/.env.local` / `frontend_client/.env.local` 的 `VUE_APP_API_BASE_URL` 指向后端；同时确认后端 `uvicorn` 正常运行。
- **数据库连接失败**：检查 `DATABASE_URL`、Postgres 容器是否启动、端口是否占用。
- **Qdrant 写入/查询失败**：检查 `QDRANT_URL`、容器是否正常、集合名与代码一致。
- **管理员缺失**：运行 `python -m app.scripts.bootstrap_admin` 重新注入。

---
