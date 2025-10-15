目前的项目需求：
第一步是先尝试把后端接口写完，推荐用fastapi+postgresql的技术栈，建议用vibe coding配合着写，后端人工写，前端AI写。
数据表建议这么设计：
user——chat——message，各自都有增删查改的接口，一对多的关系
domain——document——chunk，同样，各自有增删查改。然后这里的chunk存实际的文档chunk内容，向量数据库里只存id+向量，检索到向量后，再从postgresql里的chunk表里取string，domain就是指不同来源，方便做带有filter的检索
大概需要提供的api有：
用户登录注册（需要区分admin权限，用一个字段标记admin，初始admin用sql强制写入就行）
问答的增删查改
资料管理的增删查改
api可能不好想齐全，那么可以让AI帮忙设计界面后，再反过来想需要什么样的api去满足界面交互

# 环境配置与服务启动

## 1. 克隆项目并进入目录

```sh
git clone <your-repo-url>
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

## 6. 启动 Qdrant（如需）

```sh
docker run -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant
```
或使用已有容器：
```sh
docker start qdrant
```

## 7. 初始化数据库（可选）

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

假设服务运行在 `http://localhost:8000`，如有 `/api` 前缀请自行加上。

---

## 通用

### 健康检查

```sh
curl http://localhost:8000/healthz
```

---

## domains 相关

### 创建 domain

```sh
curl -X POST http://localhost:8000/domains/ \
  -H "Content-Type: application/json" \
  -d '{"name":"PKU-Archive","description":"test"}'
```

### 获取 domain 列表

```sh
curl http://localhost:8000/domains/
```

### 获取指定 domain

```sh
curl http://localhost:8000/domains/1
```

### 更新 domain

```sh
curl -X PATCH http://localhost:8000/domains/1 \
  -H "Content-Type: application/json" \
  -d '{"name":"NewName","description":"new desc"}'
```

### 删除 domain

```sh
curl -X DELETE http://localhost:8000/domains/1
```

---

## documents 相关

### 为 domain 添加 document

```sh
curl -X POST http://localhost:8000/domains/1/documents \
  -H "Content-Type: application/json" \
  -d '{"name":"doc1","description":"desc"}'
```

### 获取 domain 下所有 documents

```sh
curl http://localhost:8000/domains/1/documents
```

### 更新 document

```sh
curl -X PATCH http://localhost:8000/domains/documents/1 \
  -H "Content-Type: application/json" \
  -d '{"name":"newdoc","description":"newdesc"}'
```

### 删除 document

```sh
curl -X DELETE http://localhost:8000/domains/documents/1
```

---

## chunks 相关

### 获取 document 下所有 chunks

```sh
curl http://localhost:8000/domains/documents/1/chunks
```

---

## chats 相关

### 创建 chat

```sh
curl -X POST http://localhost:8000/chats/ \
  -H "Content-Type: application/json" \
  -d '{"user_id":1,"title":"chat1"}'
```

### 获取 chat 列表

```sh
curl "http://localhost:8000/chats/?user_id=1"
```

### 更新 chat

```sh
curl -X PATCH http://localhost:8000/chats/1 \
  -H "Content-Type: application/json" \
  -d '{"title":"new title"}'
```

### 删除 chat

```sh
curl -X DELETE http://localhost:8000/chats/1
```

---

## messages 相关

### 为 chat 添加 message

```sh
curl -X POST http://localhost:8000/chats/1/messages \
  -H "Content-Type: application/json" \
  -d '{"content":"hello"}'
```

### 获取 chat 下所有 messages

```sh
curl http://localhost:8000/chats/1/messages
```

### 更新 message

```sh
curl -X PATCH http://localhost:8000/chats/messages/1 \
  -H "Content-Type: application/json" \
  -d '{"content":"new content"}'
```

### 删除 message

```sh
curl -X DELETE http://localhost:8000/chats/messages/1
```

---

> 如有参数或字段不同，请根据实际 schema 调整。如有 `/api` 前缀，请将所有路径改为 `/api/xxx`。