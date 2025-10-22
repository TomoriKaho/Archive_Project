chunk存实际的文档chunk内容，向量数据库里只存id+向量，检索到向量后，再从postgresql里的chunk表里取string，domain就是指不同来源，方便做带有filter的检索
提供用户登录注册的api（需要区分admin权限，用一个字段标记admin，初始admin用sql强制写入就行）
api可能不好想齐全，那么可以让AI帮忙设计界面后，再反过来想需要什么样的api去满足界面交互

# 环境配置与服务启动

## 1. 克隆项目并进入目录

```sh
git clone git@github.com:TomoriKaho/Archive_Project.git
cd Archive_Project
```

## 2. 创建并激活 Python 虚拟环境

```sh
python3 -m venv .venv
source .venv/bin/activate
```

## 3. 安装依赖

```sh
pip install -r requirements.txt
```

## 4. 配置环境变量

编辑 `.env` 文件，内容示例：

```
DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/mydb
QDRANT_URL=http://localhost:6333
```

加载环境变量：

```sh
export $(cat .env | xargs)
```

## 5. 使用 Docker 启动 PostgreSQL

```sh
docker run --name rag-pg -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres
```
或使用已有容器：
```sh
docker start rag-pg
```

## 6. 启动 Qdrant

```sh
docker run -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant
```
或使用已有容器：
```sh
docker start qdrant
```

## 7. 初始化数据库

```sh
alembic upgrade head
```

## 8. 启动后端服务

```sh
uvicorn app.main:app --reload
```

## 9. 健康检查

```sh
curl http://localhost:8000/healthz
```

---

# API curl 示例

假设服务运行在 `http://localhost:8000`，如有 `/api` 前缀请自行加上。以下示例使用 `jq` 从 JSON 响应中提取字段，如未安装可忽略相关命令并手动复制响应数据。

```sh
BASE_URL=http://localhost:8000

# 可选：根据实际数据替换以下示例 ID
DOMAIN_ID=1
DOC_ID=1
CHUNK_ID=1
CHAT_ID=1
MESSAGE_ID=1
USER_ID=1
```

## 通用

### 健康检查
```sh
curl "$BASE_URL/healthz"
```

## 认证（Auth）

### 注册普通用户

```sh
curl -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"secret123"}'
```

### 登录并保存访问令牌

```sh
TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"secret123"}' | jq -r '.access_token')
```

### 管理员登录获取令牌（使用 `seed_admin.py` 预先创建的账号）

```sh
ADMIN_TOKEN=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin-secret"}' | jq -r '.access_token')
```

> 将示例邮箱与密码替换成数据库中真实存在的管理员凭据。

## 用户接口（需要 Bearer Token）

### 获取当前登录用户

```sh
curl "$BASE_URL/users/me" \
  -H "Authorization: Bearer $TOKEN"
```

### 管理员分页获取用户列表

```sh
curl "$BASE_URL/users?offset=0&limit=50" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### 管理员创建用户

```sh
curl -X POST "$BASE_URL/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"new.user@example.com","password":"secret123","is_admin":false}'
```

### 获取指定用户（管理员可查看任意用户，普通用户仅能查看自身）

```sh
curl "$BASE_URL/users/$USER_ID" \
  -H "Authorization: Bearer $TOKEN"
```

### 更新用户信息

```sh
curl -X PATCH "$BASE_URL/users/$USER_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"password":"newSecret456"}'
```

> 若需修改 `is_admin` 字段，请使用管理员令牌，并确保请求体中的 `is_admin` 不为 `null`。

### 管理员删除用户

```sh
curl -X DELETE "$BASE_URL/users/$USER_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

## 资料管理（Domains / Documents / Chunks）

### 创建 domain

```sh
curl -X POST "$BASE_URL/domains" \
  -H "Content-Type: application/json" \
  -d '{"name":"PKU-Archive","description":"test"}'
```

### 获取 domain 列表

```sh
curl "$BASE_URL/domains"
```

### 获取指定 domain

```sh
curl "$BASE_URL/domains/$DOMAIN_ID"
```

### 更新 domain

```sh
curl -X PATCH "$BASE_URL/domains/$DOMAIN_ID" \
  -H "Content-Type: application/json" \
  -d '{"name":"NewName","description":"new desc"}'
```

### 删除 domain

```sh
curl -X DELETE "$BASE_URL/domains/$DOMAIN_ID"
```

### 在 domain 下创建 document

```sh
curl -X POST "$BASE_URL/domains/$DOMAIN_ID/documents" \
  -H "Content-Type: application/json" \
  -d '{"title":"doc1","doc_metadata":{"field1":"test"}}'
```

### 获取 domain 下所有 documents

```sh
curl "$BASE_URL/domains/$DOMAIN_ID/documents?offset=0&limit=50"
```

### 获取指定 document

```sh
curl "$BASE_URL/domains/$DOMAIN_ID/documents/$DOC_ID"
```

### 更新 document

```sh
curl -X PATCH "$BASE_URL/domains/$DOMAIN_ID/documents/$DOC_ID" \
  -H "Content-Type: application/json" \
  -d '{"title":"newdoc","doc_metadata":{"field1":"new value"}}'
```

### 删除 document

```sh
curl -X DELETE "$BASE_URL/domains/$DOMAIN_ID/documents/$DOC_ID"
```

### 在 document 下创建 chunk

```sh
curl -X POST "$BASE_URL/domains/$DOMAIN_ID/documents/$DOC_ID/chunks" \
  -H "Content-Type: application/json" \
  -d '{"ordinal":1,"content":"chunk content"}'
```

### 获取 document 下所有 chunks

```sh
curl "$BASE_URL/domains/$DOMAIN_ID/documents/$DOC_ID/chunks"
```

### 获取指定 chunk

```sh
curl "$BASE_URL/domains/$DOMAIN_ID/documents/$DOC_ID/chunks/$CHUNK_ID"
```

### 更新 chunk

```sh
curl -X PATCH "$BASE_URL/domains/$DOMAIN_ID/documents/$DOC_ID/chunks/$CHUNK_ID" \
  -H "Content-Type: application/json" \
  -d '{"content":"new chunk content"}'
```

### 删除 chunk

```sh
curl -X DELETE "$BASE_URL/domains/$DOMAIN_ID/documents/$DOC_ID/chunks/$CHUNK_ID"
```

## 聊天与消息（Chats / Messages）

### 创建 chat

```sh
curl -X POST "$BASE_URL/chats" \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"title":"chat1"}'
```

### 获取 chat 列表（按用户过滤）

```sh
curl "$BASE_URL/chats?user_id=1&offset=0&limit=50"
```

### 更新 chat

```sh
curl -X PATCH "$BASE_URL/chats/$CHAT_ID" \
  -H "Content-Type: application/json" \
  -d '{"title":"new title"}'
```

### 删除 chat

```sh
curl -X DELETE "$BASE_URL/chats/$CHAT_ID"
```

### 为 chat 添加 message

```sh
curl -X POST "$BASE_URL/chats/$CHAT_ID/messages" \
  -H "Content-Type: application/json" \
  -d "{\"chat_id\":$CHAT_ID,\"role\":\"user\",\"content\":\"hello\"}"
```

> JSON 体中的 `chat_id` 应与路径参数保持一致。

### 获取 chat 下所有 messages

```sh
curl "$BASE_URL/chats/$CHAT_ID/messages?offset=0&limit=200"
```

### 更新 message

```sh
curl -X PATCH "$BASE_URL/chats/messages/$MESSAGE_ID" \
  -H "Content-Type: application/json" \
  -d '{"content":"new content"}'
```

### 删除 message

```sh
curl -X DELETE "$BASE_URL/chats/messages/$MESSAGE_ID"
```
