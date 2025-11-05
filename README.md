# Archive Project

基于 FastAPI 的文档管理与对话服务，提供 domain、document、chunk、chat、message 等核心资源的 REST 接口。

## 环境准备与服务启动

1. 克隆仓库并进入目录
   ```bash
   git clone git@github.com:TomoriKaho/Archive_Project.git
   cd Archive_Project
   ```
2. 创建并激活虚拟环境
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```
4. 设置环境变量
    本项目使用`.env`文件来管理环境变量。请按照以下步骤设置和配置你的`.env`文件。
    确保在`.env`文件中设置以下环境变量：
    ```plaintext
    DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/mydb
    QDRANT_URL=http://localhost:6333
    JWT_SECRET_KEY=change-me
    JWT_ALGORITHM=HS256
    ACCESS_TOKEN_EXPIRE_MINUTES=60
    INITIAL_ADMIN_EMAIL=admin@example.com
    ADMIN_INIT_PASSWORD=ChangeMe123
    ```
   **环境变量配置示例**
    你可以使用以下命令来配置你的环境变量：
    ```bash
    set -a
    source .env
    set +a
    ```
    **注意事项:**

    - 安全性: 不要将真实的敏感信息提交到版本控制系统中。

    - 配置检查: 在启动项目之前，请确保.env文件中的所有环境变量已正确配置。
    <br>
5. 启动 PostgreSQL（可使用已有容器或服务）
   ```bash
   docker run --name rag-pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres
   # docker start rag-pg
   ```
6. 启动 Qdrant
   ```bash
   docker run -d --name qdrant \
  -p 6333:6333 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  -e QDRANT__SERVICE__USER__UID=$(id -u) \
  -e QDRANT__SERVICE__USER__GID=$(id -g) \
  qdrant/qdrant
   # docker start qdrant
   ```
7. 初始化数据库
   ```bash
   alembic upgrade head
   ```
8. 启动开发服务器
   ```bash
   uvicorn app.main:app --reload
   ```

## 前端启动指南（Vue CLI 应用）

新的前端代码位于 `frontend/` 目录，使用 Vue 3 + Pinia + Vue Router 搭建。下面给出从安装依赖到本地调试、构建的完整流程。

1. **进入前端目录并安装依赖**

   ```bash
   cd frontend
   npm install
   ```

   > 如果你在公司或内网环境，需要配置 npm 私有源，请先根据网络要求设置好 `npm config set registry`。

2. **配置前端环境变量**

   ```bash
   cp .env.example .env.local
   ```

   使用编辑器打开 `.env.local`，根据后端服务的访问地址调整变量：

   ```ini
   VUE_APP_API_BASE_URL=http://localhost:8000/api
   VUE_APP_TOKEN_STORAGE_KEY=archive_ai_token
   ```

   - `VUE_APP_API_BASE_URL`：指向后端 API 的基础路径，默认假设后端运行在本地 8000 端口。
   - `VUE_APP_TOKEN_STORAGE_KEY`：浏览器本地存储 JWT 的键名，如无特殊需求可保持默认。

3. **启动前端开发服务器**

   ```bash
   npm run serve
   ```

   Vue CLI 会在 <http://localhost:8080> 启动热更新开发服务器。首次访问时请确保后端服务已启动，并在登录页面使用后端允许的账号密码登录。

4. **运行代码检查与单元测试（可选）**

   - 代码格式检查：

     ```bash
     npm run lint
     ```

   - 单元测试：

     ```bash
     npm run test:unit
     ```

5. **构建生产版本（部署时使用）**

   ```bash
   npm run build
   ```

   构建产物输出到 `frontend/dist/`，可部署到任意静态资源服务器或反向代理中间件。

完成上述步骤后，即可在浏览器中访问新的 Vue 前端界面。旧的静态 HTML/CSS 前端已移除，不再需要。

## API 路由参考
以下内容按资源分组，所有路径均以 `http://localhost:8000` 为基准，实际部署时请替换主机名。

### 健康检查
#### GET /healthz
- **说明**：返回服务运行状态。
- **成功响应**：`200 OK`，`{"ok": true}`。

### 域（domains）
#### POST /domains
- **说明**：创建新的 domain。
- **请求体**：`DomainCreate`
  ```json
  {
    "name": "string",
    "description": "string | null"
  }
  ```
- **成功响应**：`201 Created`，返回 `DomainOut`（`id`, `name`, `description`, `created_at`, `updated_at`）。
- **错误**：`400 Bad Request`（名称重复）。

#### GET /domains
- **说明**：分页列出 domain。
- **查询参数**：
  - `offset`（int，默认 0）
  - `limit`（int，默认 100，最大 200）
- **成功响应**：`200 OK`，数组形式的 `DomainOut`。

#### GET /domains/{domain_id}
- **说明**：按 ID 获取 domain。
- **路径参数**：`domain_id`（int）。
- **成功响应**：`200 OK`，`DomainOut`。
- **错误**：`404 Not Found`（不存在）。

#### PATCH /domains/{domain_id}
- **说明**：部分更新 domain，仅修改请求体中出现的字段。
- **请求体**：`DomainUpdate`（`name`, `description` 均可为空表示不修改）。
- **成功响应**：`200 OK`，更新后的 `DomainOut`。
- **错误**：`404 Not Found`（不存在）。

#### DELETE /domains/{domain_id}
- **说明**：删除 domain，并级联清理关联 documents/chunks。
- **成功响应**：`204 No Content`。
- **错误**：`404 Not Found`（不存在）。

### 文档（documents）
#### GET /documents
- **说明**：分页检索文档，可按 domain 过滤并指定排序。
- **查询参数**：
  - `domain_id`（int，可选）
  - `limit`（int，默认 20，范围 1-100）
  - `offset`（int，默认 0，≥0）
  - `sort_by`（`created_at` | `title`，默认 `created_at`）
  - `order`（`asc` | `desc`，默认 `desc`）
- **成功响应**：`200 OK`，`DocumentListResponse`
  ```json
  {
    "items": [DocumentOut, ...],
    "total": 0,
    "limit": 0,
    "offset": 0,
    "sort_by": "created_at",
    "order": "desc"
  }
  ```

#### GET /documents/by-uuid/{doc_uuid}
- **说明**：按文档 UUID 获取详情。
- **路径参数**：`doc_uuid`（UUID）。
- **成功响应**：`200 OK`，`DocumentOut`。
- **错误**：`404 Not Found`。

#### DELETE /documents/by-uuid/{doc_uuid}
- **说明**：按 UUID 删除文档，未命中时亦返回成功以保证幂等。
- **成功响应**：`204 No Content`。

#### POST /domains/{domain_id}/documents
- **说明**：在指定 domain 下创建文档并自动生成 chunks。
- **路径参数**：`domain_id`（int）。
- **请求体**：
  - 纯文本：仍可发送 JSON 请求体 `DocumentCreate`，内容使用滑动窗口（大小 250、前后重叠 50）拆分。
  - 结构化 CSV：发送 `multipart/form-data`，字段包含：
    - `title`：文档标题；
    - `mode=csv`；
    - `file`：CSV 文件，首列 `entity`，其余列作为键值字段，服务端解析为 `entity:key:value` 形式的 chunks（每段 <250 字符，尽量容纳更多键值对）。
- **成功响应**：`201 Created`，`DocumentOut`。
- **错误**：`404 Not Found`（domain 不存在）。

#### GET /domains/{domain_id}/documents
- **说明**：列出某个 domain 下最近创建的文档（限制 50 条）。
- **路径参数**：`domain_id`（int）。
- **成功响应**：`200 OK`，`DocumentOut` 数组。
- **错误**：`404 Not Found`（domain 不存在）。

#### GET /domains/{domain_id}/documents/{doc_id}
- **说明**：在 domain 上下文中读取文档，确保归属关系一致。
- **路径参数**：`domain_id`、`doc_id`（int）。
- **成功响应**：`200 OK`，`DocumentOut`。
- **错误**：`404 Not Found`（domain 或 document 不存在 / 不匹配）。

#### PATCH /domains/{domain_id}/documents/{doc_id}
- **说明**：更新文档标题或元数据，不重新生成 chunks。
- **请求体**：`DocumentUpdate`。
- **成功响应**：`200 OK`，`DocumentOut`。
- **错误**：`404 Not Found`。

#### DELETE /domains/{domain_id}/documents/{doc_id}
- **说明**：删除指定文档并级联清理 chunks。
- **成功响应**：`204 No Content`。
- **错误**：`404 Not Found`。

### 文档块（chunks）
#### GET /domains/{domain_id}/documents/{doc_id}/chunks
- **说明**：按 domain 与文档 ID 获取 chunk 列表（Deprecated，保留兼容）。
- **成功响应**：`200 OK`，`ChunkOut` 数组。
- **错误**：`404 Not Found`（domain 或 document 不存在 / 不匹配）。

#### GET /documents/{doc_id}/chunks
- **说明**：通过文档 ID 获取 chunk 列表。
- **成功响应**：`200 OK`，`ChunkOut` 数组。
- **错误**：`404 Not Found`（document 不存在）。

#### GET /documents/by-uuid/{doc_uuid}/chunks
- **说明**：通过文档 UUID 获取 chunk 列表。
- **成功响应**：`200 OK`，`ChunkOut` 数组。
- **错误**：`404 Not Found`（document 不存在）。

#### POST /domains/{domain_id}/documents/{doc_id}/chunks
- **说明**：禁止手动创建 chunk，接口固定返回 405。
- **响应**：`405 Method Not Allowed`，`{"detail": "chunk are generated automatically and cannot be created manually"}`。

#### PATCH /domains/{domain_id}/documents/{doc_id}/chunks/{chunk_id}
- **说明**：禁止修改 chunk 内容，接口固定返回 405。
- **响应**：`405 Method Not Allowed`，`{"detail": "chunk modification is disabled to keep consistency with source content"}`。

### 对话（chats）
#### POST /chats/
- **说明**：创建 chat 会话。
- **请求体**：`ChatCreate`
  ```json
  {
    "user_id": 0,
    "title": "string | null"
  }
  ```
- **成功响应**：`201 Created`，`ChatOut`。

#### GET /chats/
- **说明**：按用户列出 chat。
- **查询参数**：
  - `user_id`（int，必填）
  - `offset`（int，默认 0）
  - `limit`（int，默认 50，最大 200）
- **成功响应**：`200 OK`，`ChatOut` 数组。

#### PATCH /chats/{chat_id}
- **说明**：更新 chat 标题。
- **请求体**：`ChatUpdate`。
- **成功响应**：`200 OK`，`ChatOut`。
- **错误**：`404 Not Found`。

#### DELETE /chats/{chat_id}
- **说明**：删除 chat 及其关联消息。
- **成功响应**：`204 No Content`。
- **错误**：`404 Not Found`。

### 消息（messages）
#### POST /chats/{chat_id}/messages
- **说明**：在指定 chat 下新增消息，路径中的 `chat_id` 会覆盖请求体中的同名字段；当 `role` 为 `user` 时会自动触发 RAG 检索并生成对应的助手回复。
- **请求体**：`MessageCreate`
  ```json
  {
    "chat_id": 0,
    "role": "user | assistant | system",
    "content": "string",
    "top_k": 10,
    "domain_ids": [1, 2]
  }
  ```
  `top_k`、`domain_ids` 字段可选，用于调整单次检索的 chunk 数量与 domain 过滤。
- **成功响应**：`201 Created`，`MessageCreateResponse`，包含 `user`、`assistant` 与 `references` 三个字段方便前端一次性渲染问答结果。

#### GET /chats/{chat_id}/messages
- **说明**：分页列出 chat 下的消息。
- **查询参数**：
  - `offset`（int，默认 0）
  - `limit`（int，默认 200，最大 500）
- **成功响应**：`200 OK`，`MessageOut` 数组。

#### PATCH /chats/messages/{msg_id}
- **说明**：更新消息内容。
- **请求体**：`MessageUpdate`。
- **成功响应**：`200 OK`，`MessageOut`。
- **错误**：`404 Not Found`。

#### DELETE /chats/messages/{msg_id}
- **说明**：删除指定消息。
- **成功响应**：`204 No Content`。
- **错误**：`404 Not Found`。

### 认证（auth）
#### POST /auth/register
- **说明**：匿名注册普通用户，`is_admin` 固定为 `false`。
- **请求体**：`UserCreate`
  ```json
  {
    "email": "user@example.com",
    "password": "StrongPass1",
    "full_name": "string | null"
  }
  ```
- **成功响应**：`201 Created`，返回注册用户的 `UserOut`（不含 `hashed_password`）。
- **错误**：`400 Bad Request`（邮箱重复）。

#### POST /auth/login
- **说明**：凭邮箱与密码换取访问令牌。
- **请求体**
  ```json
  {
    "email": "user@example.com",
    "password": "StrongPass1"
  }
  ```
- **成功响应**：`200 OK`，`{"access_token": "<JWT>", "token_type": "bearer"}`。
- **错误**：`401 Unauthorized`（邮箱或密码错误）。

#### GET /auth/me
- **说明**：需携带 Bearer Token，返回当前用户信息。
- **请求头**：`Authorization: Bearer <token>`。
- **成功响应**：`200 OK`，`UserOut`。
- **错误**：`401 Unauthorized`（缺少/过期/无效 token）。

### 用户（users）
#### POST /users
- **说明**：仅管理员可创建用户，可设定 `is_admin`。
- **请求头**：`Authorization: Bearer <admin_token>`。
- **请求体**：`UserCreate`（管理员扩展 `is_admin` 字段）
  ```json
  {
    "email": "alice@example.com",
    "password": "AlicePass1",
    "full_name": "Alice",
    "is_admin": false
  }
  ```
- **成功响应**：`201 Created`，`UserOut`。
- **错误**：`400 Bad Request`（邮箱重复），`403 Forbidden`（非管理员）。

#### GET /users
- **说明**：仅管理员可分页列出用户，可按邮箱/姓名模糊查询。
- **请求头**：`Authorization: Bearer <admin_token>`。
- **查询参数**：
  - `limit`（int，默认 20，最大 100）
  - `offset`（int，默认 0，≥0）
  - `q`（string，可选，搜索关键词）
- **成功响应**：`200 OK`，`UserListResponse`
  ```json
  {
    "items": [UserOut, ...],
    "total": 0,
    "limit": 20,
    "offset": 0
  }
  ```
- **错误**：`403 Forbidden`（非管理员）。

#### GET /users/{user_id}
- **说明**：管理员或本人可查看用户详情。
- **请求头**：`Authorization: Bearer <token>`。
- **路径参数**：`user_id`（int）。
- **成功响应**：`200 OK`，`UserOut`。
- **错误**：`403 Forbidden`（非本人且非管理员），`404 Not Found`（用户不存在）。

#### PATCH /users/{user_id}
- **说明**：管理员或本人可更新资料，仅管理员能修改 `is_admin`。
- **请求头**：`Authorization: Bearer <token>`。
- **请求体**：`UserUpdate`
  ```json
  {
    "full_name": "Alice L.",
    "password": "NewPass#2",
    "is_admin": true
  }
  ```
- **成功响应**：`200 OK`，`UserOut`。
- **错误**：`403 Forbidden`（越权操作），`404 Not Found`。

#### DELETE /users/{user_id}
- **说明**：仅管理员可删除用户，并级联删除其 chats/messages。
- **请求头**：`Authorization: Bearer <admin_token>`。
- **路径参数**：`user_id`（int）。
- **成功响应**：`204 No Content`。
- **错误**：`403 Forbidden`（非管理员），`404 Not Found`（用户不存在或已删除）。

## Auth 使用说明
- 在 `.env` 中新增 `JWT_SECRET_KEY`、`JWT_ALGORITHM`（默认 `HS256`）与 `ACCESS_TOKEN_EXPIRE_MINUTES`（默认 `60`）。
- 调用 `POST /auth/register` 可匿名注册普通用户，或由管理员调用 `POST /users` 创建并指定 `is_admin`。
- 登录接口 `POST /auth/login` 需提交邮箱和密码，成功后返回 `{"access_token": "<JWT>", "token_type": "bearer"}`。
- 后续请求在 `Authorization` 请求头中附带 `Bearer <token>` 即可访问需要鉴权的接口。

## 管理员初始账号与密码修改建议
- 数据迁移会自动创建 `admin@example.com`，默认密码 `ChangeMe123`（或环境变量 `ADMIN_INIT_PASSWORD`）。
- 该密码仅用于首次登陆，请在登录后立刻调用 `PATCH /users/{id}` 更新密码，或直接修改数据库。
- 若不再需要该账号，可由另一位管理员登录后删除，系统将同步清理其聊天与消息。
- 如果误删了初始管理员，重启后端服务即可自动重新注入；也可以手动执行 `python -m app.scripts.bootstrap_admin` 立即恢复。

## User API 权限矩阵
| 操作 | 匿名 | 登录用户 | 管理员 |
| --- | --- | --- | --- |
| 注册 /auth/register | ✅ | ✅ | ✅ |
| 登录 /auth/login | ✅ | ✅ | ✅ |
| 我是谁 /auth/me | ❌ | ✅ | ✅ |
| 列表 /users | ❌ | ❌ | ✅ |
| 查看 /users/{id} | ❌ | 仅本人 | ✅ |
| 创建 /users | ❌ | ❌ | ✅ |
| 更新 /users/{id} | ❌ | 仅本人（不可改 is_admin） | ✅（可改 is_admin） |
| 删除 /users/{id} | ❌ | ❌ | ✅ |

## 级联删除的影响与数据备份提醒
- 删除用户会自动触发其聊天与消息的级联删除，确保系统不留下孤儿记录。
- 若某些历史对话需要保留，建议在删除前进行备份，或考虑改为软删除策略。
- 同样地，删除聊天或文档也会同步清理其下属消息与文档块，避免数据不一致。

## 前端自测剧本
1. 启动后端服务并确保已有管理员账号（admin@example.com / ChangeMe123），在终端运行 `cd frontend && python -m http.server 8080` 启动静态前端。  
2. 使用浏览器访问 `http://localhost:8080`，确认默认跳转至登录页，输入管理员账号密码登录后进入仪表盘，看到 Admin 徽章与文档统计。  
3. 进入 “用户管理” 页创建普通用户 `alice@example.com`，搜索关键字 `alice` 可以看到新用户，然后使用新账号重新登录，访问 `#/users` 时收到权限不足的 toast。  
4. 进入 “域管理” 页创建、编辑并删除一条域记录，观察列表实时刷新。  
5. 打开 “文档列表” 页，在不同域间切换筛选，创建一篇普通文本文档和一篇结构化 JSON 文档，进入详情页查看 Chunks 标签与原始内容，再删除文档并确认列表为空。  
6. （可选）进入 “聊天记录” 页，新建会话、发送消息、编辑消息并删除会话，验证消息区会随会话切换刷新。  
7. 点击右上角 “登出” 按钮，确认返回登录页面。

## RAG 快速开始

### `.env` 关键配置

```dotenv
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=VOC_Archives
OLLAMA_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=qwen3-embedding:8b
OLLAMA_CHAT_MODEL=llama3.1:8b
RAG_TOP_K=10
RAG_OLLAMA_TIMEOUT=60
```

### 启动 Qdrant 与 Ollama（示例）

```bash
# Qdrant（单节点）
docker run -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant

# Ollama（需要预先拉取所需模型）
ollama serve &
ollama pull qwen3-embedding:8b
ollama pull llama3.1:8b
```

### 常用调试命令

```bash
# 1) 手动重新把指定文档的向量写入 Qdrant（通常无需调用）
curl -X POST http://localhost:8000/rag/ingest/42

# 2) 在 chat 中问问题（并得到 RAG 的回答）
curl -X POST http://localhost:8000/chats/7/messages \
     -H 'Content-Type: application/json' \
     -H 'Authorization: Bearer <token>' \
     -d '{"role": "user", "content": "What is the access code of ...?", "top_k": 8, "domain_ids": [3]}'

# 3) 预览检索命中（开发调试）
curl 'http://localhost:8000/rag/preview?q=VOC+Batavia&top_k=5&domain_id=3'
```

## Frontend

The Vue-based client lives in [`frontend/`](frontend/README.md). Refer to its README for setup, environment variables, and available npm scripts.
