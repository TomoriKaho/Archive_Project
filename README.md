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
    本项目使用 `.env` 文件集中管理环境变量。仓库已经提供了一个示例 `.env`，核心字段说明如下：
    ```plaintext
    DATABASE_URL=postgresql+psycopg://rag_user:rag_password@localhost:5432/rag_db
    QDRANT_URL=http://localhost:6333
    QDRANT_COLLECTION=archives_chunks
    OLLAMA_URL=http://localhost:11434
    OLLAMA_EMBED_MODEL=qwen3-embedding:8b
    OLLAMA_CHAT_MODEL=llama3.1:8b
    JWT_SECRET_KEY=change-me
    JWT_ALGORITHM=HS256
    ACCESS_TOKEN_EXPIRE_MINUTES=60
    INITIAL_ADMIN_EMAIL=admin@example.com
    ADMIN_INIT_PASSWORD=ChangeMe123
    ```
    上述配置遵循“向量库仅保存 `external_id + 向量`，chunk 文本仍在 PostgreSQL 中维护”的约定：
    - `QDRANT_*` 控制向量数据库连接与集合名称；
    - `OLLAMA_*` 控制嵌入模型与对话模型；
    - 其余字段与认证、初始管理员等功能相关。

    你可以使用以下命令加载 `.env`：
    ```bash
    set -a
    source .env
    set +a
    ```
    **注意事项：**

    - 不要将真实敏感信息提交到版本控制系统。
    - 启动前务必确认 `.env` 已填写完整且对应服务已启动。
    <br>
5. 启动 PostgreSQL（可使用已有容器或服务）
   ```bash
   docker run --name rag-pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres
   # docker start rag-pg
   ```
6. 启动 Qdrant
   ```bash
   docker run -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant
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

9. 启动 Ollama 并拉取所需模型（示例）
   ```bash
   ollama serve &
   ollama pull qwen3-embedding:8b
   ollama pull llama3.1:8b
   ```

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
- **请求体**：`DocumentCreate`
  ```json
  {
    "title": "string",
    "content": "string",
    "doc_metadata": {}
  }
  ```
- **成功响应**：`201 Created`，`DocumentOut`。
- **错误**：`404 Not Found`（domain 不存在）。
- **RAG 自动索引**：文档创建成功后会立即调用 Ollama 生成 chunk 向量，并写入 Qdrant（仅保存 `external_id` 与向量）。chunk 正文仍位于 PostgreSQL，后续问答会基于 `external_id` 回表拼装上下文。

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

### RAG 问答
#### POST /rag/query
- **说明**：执行一次检索增强问答。后端会：
  1. 使用 Ollama 嵌入模型为问题生成向量并查询 Qdrant（仅返回 `external_id` 与相似度分数）；
  2. 根据 `external_id` 回表获取 chunk 文本及其所属文档、domain 信息，支持 `domain_id` 过滤；
  3. 将筛选后的 chunk 作为上下文交给 Ollama 对话模型生成回答。
- **请求体**：`RagQueryRequest`
  ```json
  {
    "question": "介绍 VOC 档案的数字化情况",
    "top_k": 5,
    "domain_id": 1
  }
  ```
- **成功响应**：`200 OK`，返回 `RagQueryResponse`
  ```json
  {
    "answer": "...",
    "hits": [
      {
        "chunk_id": 12,
        "external_id": "...",
        "document_id": 8,
        "document_title": "VOC 档案概览",
        "domain_id": 1,
        "ordinal": 0,
        "content": "...",
        "score": 0.92
      }
    ]
  }
  ```
- **错误**：`502 Bad Gateway`（向量检索或回答失败）、`500 Internal Server Error`（配置缺失）。

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
- **说明**：在指定 chat 下新增消息，路径中的 `chat_id` 会覆盖请求体中的同名字段。
- **请求体**：`MessageCreate`
  ```json
  {
    "chat_id": 0,
    "role": "user | assistant | system",
    "content": "string"
  }
  ```
- **成功响应**：`201 Created`，`MessageOut`。

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
