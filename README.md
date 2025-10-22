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
4. 配置环境变量（示例）
   ```bash
   cat > .env <<'ENV'
   DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/mydb
   QDRANT_URL=http://localhost:6333
   ENV
   export $(cat .env | xargs)
   ```
5. 启动 PostgreSQL（可使用已有容器或服务）
   ```bash
   docker run --name rag-pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres
   # docker start rag-pg
   ```
6. （可选）启动 Qdrant
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
