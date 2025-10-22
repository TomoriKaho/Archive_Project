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

## 6. （可选）启动 Qdrant

> 当前“无向量库模式”无需启动向量服务，可跳过本步骤；若后续接入向量检索，可按需启动。

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

假设服务运行在 `http://localhost:8000`，如有 `/api` 前缀请自行加上。

---

## 通用

### 健康检查

```sh
curl http://localhost:8000/healthz
```

---

## 资料管理相关

### 创建 domain

```sh
curl -X POST http://localhost:8000/domains \
  -H "Content-Type: application/json" \
  -d '{"name":"PKU-Archive","description":"test"}'
```

### 获取 domain 列表

```sh
curl http://localhost:8000/domains
```

### 获取指定 domain

```sh
curl http://localhost:8000/domains/{domain_id}
```

### 更新 domain

```sh
curl -X PATCH http://localhost:8000/domains/{domain_id} \
  -H "Content-Type: application/json" \
  -d '{"name":"NewName","description":"new desc"}'
```

### 删除 domain

```sh
curl -X DELETE http://localhost:8000/domains/{domain_id}
```

---

## documents 相关

### 在 domain 下创建 document

```sh
curl -X POST http://localhost:8000/domains/{domain_id}/documents \
  -H "Content-Type: application/json" \
  -d '{"title":"doc1", "doc_metadata": {"field1": "test"}}'
```

### 获取 domain 下所有 documents

```sh
curl http://localhost:8000/domains/{domain_id}/documents
```

### 获取指定 document

```sh
curl http://localhost:8000/domains/{domain_id}/documents/{doc_id}
```

### 更新 document

```sh
curl -X PATCH http://localhost:8000/domains/{domain_id}/documents/{doc_id} \
  -H "Content-Type: application/json" \
  -d '{"name":"newdoc","description":"newdesc"}'
```

### 删除 document

```sh
curl -X DELETE http://localhost:8000/domains/{domain_id}/documents/{doc_id}
```

---

## 无向量库模式验收指南

以下命令覆盖本次提交新增能力，均默认服务运行在 `http://localhost:8000`。

1. **斜杠兼容性**（`/domains` 与 `/domains/` 等价）：

   ```sh
   curl -i http://localhost:8000/domains
   curl -i http://localhost:8000/domains/
   ```

   预期：两次响应均为 `200 OK`，body 列表内容一致。

2. **创建结构化文档并自动分片**：

   ```sh
   curl -X POST http://localhost:8000/domains/1/documents \
     -H 'Content-Type: application/json' \
     -d '{
       "title":"Books",
       "content":"{\"entities\":[{\"entity\":\"Book\",\"data\":{\"title\":\"A\",\"author\":\"B\",\"year\":\"2020\",\"isbn\":\"X\",\"publisher\":\"Y\"}}]}",
       "doc_metadata":{"type":"structured"}
     }'
   ```

   预期：返回体包含 `"uuid": "..."` 字段。

   ```sh
   curl http://localhost:8000/documents/by-uuid/<UUID>
   curl http://localhost:8000/domains/1/documents/<DOC_ID>/chunks
   ```

   预期：chunks 列表包含 `Book:title:A,author:B,year:2020,isbn:X,publisher:Y` 字符串，且每段长度 < 250。

3. **创建非结构化文档并自动滑窗分片**：

   ```sh
   curl -X POST http://localhost:8000/domains/1/documents \
     -H 'Content-Type: application/json' \
     -d '{
       "title":"LongText",
       "content":"<构造超过350字符的文本>",
       "doc_metadata":{}
     }'
   curl http://localhost:8000/domains/1/documents/<DOC_ID>/chunks
   ```

   预期：相邻 chunk 存在 50 字符重叠，可通过截取首尾片段人工核对。

4. **按 UUID 删除文档并依赖级联清理 chunks**：

   ```sh
   curl -i -X DELETE http://localhost:8000/documents/by-uuid/<UUID>
   curl http://localhost:8000/domains/1/documents/<DOC_ID>/chunks
   curl -i -X DELETE http://localhost:8000/documents/by-uuid/<UUID>
   ```

   预期：首次删除返回 `204 No Content`，随后查询 chunk 为空或 404；重复删除仍返回 `204 No Content`。

---

## 分页与排序参数说明

- `limit`：默认 20，最大 100，用于控制单页数据量，避免一次性扫描整表。
- `offset`：默认 0，支持从任意位置翻页，需为非负整数。
- `sort_by`：可选 `created_at` 或 `title`，默认按创建时间排序。
- `order`：可选 `asc` 或 `desc`，默认降序。

示例：

```sh
curl "http://localhost:8000/documents?limit=5&offset=0&sort_by=created_at&order=desc"
curl "http://localhost:8000/documents?limit=5&offset=5&sort_by=title&order=asc"
```

预期：响应格式为 `{"items":[...],"total":N,"limit":5,"offset":X,"sort_by":"...","order":"..."}`；不同排序方式应导致 items 顺序变化而 `total` 不变。

参数校验示例：

```sh
curl -i "http://localhost:8000/documents?limit=1000"
curl -i "http://localhost:8000/documents?order=sideways"
```

预期：均返回 `422 Unprocessable Entity`，body 中说明允许的取值范围。

---

## 多路由等价约定

- 推荐使用 `/documents/{doc_id}/chunks` 或 `/documents/by-uuid/{uuid}/chunks` 获取切片数据，保留 `/domains/{domain_id}/documents/{doc_id}/chunks` 作为兼容入口。
- 三条路由底层共享统一服务逻辑，返回的 JSON 内容完全一致。

示例：

```sh
curl http://localhost:8000/documents/10/chunks
curl http://localhost:8000/documents/by-uuid/<UUID>/chunks
curl http://localhost:8000/domains/1/documents/10/chunks
```

预期：三次响应的数组长度、 `chunk.content` 与 `ordinal` 均相同。

---

## chunks 相关

### 在 document 下创建 chunk
（实际使用中，由于chunk会根据document自动生成，一般不会使用）
```sh
curl -X POST http://localhost:8000/domains/{domain_id}/documents/{doc_id}/chunks \
  -H "Content-Type: application/json" \
  -d '{"ordinal":1, "content":"chunk content"}'
```

### 获取 document 下所有 chunks

```sh
curl http://localhost:8000/domains/{domain_id}/documents/{doc_id}/chunks
```

### 获取指定 chunk

```sh
curl http://localhost:8000/domains/{domain_id}/documents/{doc_id}/chunks/{chunk_id}
```

### 更新 chunk

```sh
curl -X PATCH http://localhost:8000/{domain_id}/documents/{doc_id}/chunks/{chunk_id} \
  -H "Content-Type: application/json" \
  -d '{"content":"new chunk content"}'
```

### 删除 chunk

```sh
curl -X DELETE http://localhost:8000/{domain_id}/documents/{doc_id}/chunks/{chunk_id}
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
