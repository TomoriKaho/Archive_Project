export const BASE_URL = 'http://localhost:8000'; // 定义后端基础地址常量，部署时可统一修改

export async function request(path, { method = 'GET', auth = true, headers = {}, body } = {}) { // 封装统一请求逻辑，处理鉴权与错误
  const url = `${BASE_URL}${path}`; // 拼接完整的请求 URL
  const finalHeaders = { ...headers }; // 创建可变的请求头副本
  if (body && !(body instanceof FormData) && !finalHeaders['Content-Type']) { // 当发送 JSON 时确保携带正确的内容类型
    finalHeaders['Content-Type'] = 'application/json'; // 设置请求头为 JSON 格式
  }
  if (auth) { // 仅在需要鉴权时才附加 token
    const token = window.localStorage.getItem('access_token'); // 从本地存储读取 access_token
    if (token) { // 若存在有效 token
      finalHeaders.Authorization = `Bearer ${token}`; // 在请求头中写入 Authorization
    }
  }
  if (!finalHeaders['Cache-Control']) { // 默认禁用缓存以避免读到旧数据
    finalHeaders['Cache-Control'] = 'no-cache'; // 让浏览器不要使用缓存副本
  }
  const payload = body && !(body instanceof FormData) ? JSON.stringify(body) : body; // 根据请求体类型决定是否序列化
  const fetchOptions = { method, headers: finalHeaders, body: payload, cache: 'no-store' }; // 强制每次都向服务器请求最新数据
  try { // 捕获网络异常
    const response = await fetch(url, fetchOptions); // 发起实际的 fetch 请求
    if (response.status === 204) { // 对 204 空响应直接返回 null
      return null; // 无内容时返回空值
    }
    let data = null; // 预先定义响应数据
    const contentType = response.headers.get('Content-Type'); // 读取响应内容类型
    if (contentType && contentType.includes('application/json')) { // 若为 JSON 数据
      data = await response.json(); // 解析响应体
    }
    if (!response.ok) { // 状态码非 2xx 时视为错误
      const error = new Error(data?.detail || data?.message || '请求失败'); // 构造错误对象
      error.status = response.status; // 标记 HTTP 状态码
      error.payload = data; // 附带原始响应数据
      if (response.status === 401 && auth) { // 针对需要鉴权的请求统一处理未授权
        error.code = 'UNAUTHORIZED'; // 标记错误码
        window.dispatchEvent(new CustomEvent('app:unauthorized', { detail: { message: error.message } })); // 派发全局事件方便统一处理
      }
      throw error; // 抛出错误让上层捕获
    }
    return data; // 返回解析结果
  } catch (err) { // 捕捉网络错误
    if (!(err instanceof Error)) { // 若不是标准错误
      const networkError = new Error('网络异常，请稍后再试'); // 构造统一网络错误
      networkError.status = 0; // 标记为网络层问题
      throw networkError; // 抛出错误
    }
    throw err; // 直接抛出原始错误
  }
}

export function authLogin({ email, password }) { // 登录接口封装
  return request('/auth/login', { method: 'POST', auth: false, body: { email, password } }); // 匿名 POST 登录
}

export function authRegister({ email, password, full_name }) { // 注册接口封装
  return request('/auth/register', { method: 'POST', auth: false, body: { email, password, full_name } }); // 匿名注册普通用户
}

export function authMe() { // 获取当前用户信息
  return request('/auth/me', { method: 'GET' }); // 需要鉴权的 GET 请求
}

export function getUsers({ limit, offset, q } = {}) { // 用户分页查询
  const params = new URLSearchParams(); // 构建查询参数对象
  if (limit !== undefined) params.set('limit', String(limit)); // 写入 limit
  if (offset !== undefined) params.set('offset', String(offset)); // 写入 offset
  if (q) params.set('q', q); // 写入关键词
  const query = params.toString(); // 序列化查询字符串
  return request(`/users${query ? `?${query}` : ''}`, { method: 'GET' }); // 调用 GET /users 接口
}

export function createUser({ email, password, full_name, is_admin }) { // 创建用户
  return request('/users', { method: 'POST', body: { email, password, full_name, is_admin } }); // 管理员调用创建用户
}

export function getUser(id) { // 获取单个用户详情
  return request(`/users/${id}`, { method: 'GET' }); // 调用 GET /users/{id}
}

export function updateUser(id, { full_name, password, is_admin }) { // 更新用户信息
  return request(`/users/${id}`, { method: 'PATCH', body: { full_name, password, is_admin } }); // 提交部分更新
}

export function deleteUser(id) { // 删除用户
  return request(`/users/${id}`, { method: 'DELETE' }); // 调用 DELETE /users/{id}
}

export function getDomains({ limit, offset } = {}) { // 查询域列表
  const params = new URLSearchParams(); // 初始化查询参数
  if (limit !== undefined) params.set('limit', String(limit)); // 设置 limit
  if (offset !== undefined) params.set('offset', String(offset)); // 设置 offset
  const query = params.toString(); // 序列化参数
  return request(`/domains${query ? `?${query}` : ''}`, { method: 'GET' }); // 调用 GET /domains
}

export function createDomain({ name, description }) { // 创建域
  return request('/domains', { method: 'POST', body: { name, description } }); // POST 创建新域
}

export function getDomain(id) { // 获取单个域详情
  return request(`/domains/${id}`, { method: 'GET' }); // 调用 GET /domains/{id}
}

export function updateDomain(id, { name, description }) { // 更新域信息
  return request(`/domains/${id}`, { method: 'PATCH', body: { name, description } }); // PATCH 更新域
}

export function deleteDomain(id) { // 删除域
  return request(`/domains/${id}`, { method: 'DELETE' }); // DELETE 域
}

export function getDocuments({ domain_id, limit, offset, sort_by, order } = {}) { // 获取文档列表
  const params = new URLSearchParams(); // 构建查询参数
  if (domain_id !== undefined && domain_id !== '') params.set('domain_id', String(domain_id)); // 传入 domain 过滤
  if (limit !== undefined) params.set('limit', String(limit)); // 设置分页大小
  if (offset !== undefined) params.set('offset', String(offset)); // 设置偏移量
  if (sort_by) params.set('sort_by', sort_by); // 设置排序字段
  if (order) params.set('order', order); // 设置排序方向
  const query = params.toString(); // 序列化查询字符串
  return request(`/documents${query ? `?${query}` : ''}`, { method: 'GET' }); // GET /documents
}

export function getDocumentByUUID(uuid) { // 根据 UUID 获取文档
  return request(`/documents/by-uuid/${uuid}`, { method: 'GET' }); // 调用详情接口
}

export function createDocument(domain_id, payload) { // 创建文档
  return request(`/domains/${domain_id}/documents`, { method: 'POST', body: payload }); // 在指定域下创建文档
}

export function deleteDocumentByUUID(uuid) { // 删除文档
  return request(`/documents/by-uuid/${uuid}`, { method: 'DELETE' }); // DELETE 文档
}

export function getChunksByDocId(doc_id) { // 根据文档 ID 获取 chunks
  return request(`/documents/${doc_id}/chunks`, { method: 'GET' }); // GET chunks by doc id
}

export function getChunksByUUID(uuid) { // 根据文档 UUID 获取 chunks
  return request(`/documents/by-uuid/${uuid}/chunks`, { method: 'GET' }); // GET chunks by uuid
}

export function getChunksByDomainDoc(domain_id, doc_id) { // 根据域与文档 ID 获取 chunks（兼容旧接口）
  return request(`/domains/${domain_id}/documents/${doc_id}/chunks`, { method: 'GET' }); // 调用兼容接口
}

export function createChat({ user_id, title }) { // 创建会话
  return request('/chats/', { method: 'POST', body: { user_id, title } }); // POST 创建聊天
}

export function getChats({ user_id, limit, offset } = {}) { // 获取会话列表
  const params = new URLSearchParams(); // 创建查询参数
  if (user_id !== undefined) params.set('user_id', String(user_id)); // 指定用户 ID
  if (limit !== undefined) params.set('limit', String(limit)); // 设置 limit
  if (offset !== undefined) params.set('offset', String(offset)); // 设置 offset
  const query = params.toString(); // 序列化参数
  return request(`/chats/${query ? `?${query}` : ''}`, { method: 'GET' }); // GET /chats
}

export function updateChat(chat_id, { title }) { // 更新会话标题
  return request(`/chats/${chat_id}`, { method: 'PATCH', body: { title } }); // PATCH 更新标题
}

export function deleteChat(chat_id) { // 删除会话
  return request(`/chats/${chat_id}`, { method: 'DELETE' }); // DELETE 会话
}

export function createMessage(chat_id, { role = 'user', content, top_k, domain_ids } = {}) { // 创建消息
  const body = { chat_id, role, content };
  if (Number.isFinite(top_k)) body.top_k = top_k;
  if (Array.isArray(domain_ids) && domain_ids.length > 0) body.domain_ids = domain_ids;
  return request(`/chats/${chat_id}/messages`, { method: 'POST', body }); // POST 消息
}

export function getMessages(chat_id, { limit, offset } = {}) { // 获取消息列表
  const params = new URLSearchParams(); // 构建查询参数
  if (limit !== undefined) params.set('limit', String(limit)); // 设置 limit
  if (offset !== undefined) params.set('offset', String(offset)); // 设置 offset
  const query = params.toString(); // 序列化参数
  return request(`/chats/${chat_id}/messages${query ? `?${query}` : ''}`, { method: 'GET' }); // GET 消息列表
}

export function updateMessage(msg_id, { content }) { // 更新消息内容
  return request(`/chats/messages/${msg_id}`, { method: 'PATCH', body: { content } }); // PATCH 消息
}

export function deleteMessage(msg_id) { // 删除消息
  return request(`/chats/messages/${msg_id}`, { method: 'DELETE' }); // DELETE 消息
}

export function ingestDocumentToRag(document_id) { // 将指定文档的 chunks 写入向量库
  return request(`/rag/ingest/${document_id}`, { method: 'POST' }); // POST /rag/ingest/{document_id}
}

export function previewRag({ q, top_k, domain_id } = {}) { // 调试用的 RAG 预览接口
  const params = new URLSearchParams(); // 初始化查询参数
  if (q) params.set('q', q); // 写入问题内容
  if (top_k !== undefined) params.set('top_k', String(top_k)); // 写入召回数量
  if (domain_id !== undefined && domain_id !== null && domain_id !== '') {
    params.set('domain_id', String(domain_id)); // 写入 domain 过滤
  }
  const query = params.toString(); // 序列化查询参数
  return request(`/rag/preview${query ? `?${query}` : ''}`, { method: 'GET' }); // GET /rag/preview
}
