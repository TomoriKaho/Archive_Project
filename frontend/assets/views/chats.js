import { getChats, createChat, updateChat, deleteChat, getMessages, createMessage, updateMessage, deleteMessage } from '../api.js'; // 导入聊天与消息接口
import { toast, spinner, confirmDialog } from '../ui/components.js'; // 引入提示、加载与确认组件
import { getCurrentUser, navigate } from '../app.js'; // 引入当前用户信息与导航能力

let containerRef = null; // 保存容器引用
let chatsContainer = null; // 缓存会话列表容器
let messagesContainer = null; // 缓存消息区域容器
let messageForm = null; // 缓存发送消息表单
let sendHandler = null; // 缓存发送事件处理器
let currentChatId = null; // 当前选中的会话 ID
let paginationState = { limit: 50, offset: 0 }; // 消息分页状态

export default { // 导出聊天视图
  async mount(container) { // 挂载逻辑
    containerRef = container; // 保存容器引用
    const title = document.createElement('h1'); // 创建标题
    title.textContent = '聊天记录'; // 设置标题文本
    container.appendChild(title); // 渲染标题
    const layout = document.createElement('div'); // 创建整体布局
    layout.style.display = 'grid'; // 使用网格布局
    layout.style.gridTemplateColumns = '280px 1fr'; // 定义列宽
    layout.style.gap = '16px'; // 设置列间距
    layout.style.marginTop = '16px'; // 设置顶部间距
    container.appendChild(layout); // 渲染布局
    chatsContainer = document.createElement('div'); // 创建会话容器
    chatsContainer.className = 'table-wrapper'; // 应用卡片样式
    layout.appendChild(chatsContainer); // 渲染会话容器
    const chatHeader = document.createElement('div'); // 创建会话头部
    chatHeader.style.display = 'flex'; // 使用弹性布局
    chatHeader.style.justifyContent = 'space-between'; // 两端对齐
    chatHeader.style.alignItems = 'center'; // 垂直居中
    const chatTitle = document.createElement('h2'); // 创建头部标题
    chatTitle.textContent = '会话'; // 设置文案
    chatHeader.appendChild(chatTitle); // 渲染标题
    const createBtn = document.createElement('button'); // 创建新建按钮
    createBtn.className = 'button'; // 主按钮样式
    createBtn.type = 'button'; // 指定类型
    createBtn.textContent = '新建会话'; // 按钮文本
    chatHeader.appendChild(createBtn); // 添加按钮
    chatsContainer.appendChild(chatHeader); // 渲染头部
    const chatList = document.createElement('div'); // 创建会话列表容器
    chatList.id = 'chat-list'; // 设置 ID
    chatList.style.marginTop = '12px'; // 设置顶部间距
    chatsContainer.appendChild(chatList); // 渲染列表容器
    messagesContainer = document.createElement('div'); // 创建消息容器
    messagesContainer.className = 'table-wrapper'; // 应用卡片样式
    layout.appendChild(messagesContainer); // 渲染消息容器
    const messageHeader = document.createElement('div'); // 创建消息头部
    messageHeader.style.display = 'flex'; // 使用弹性布局
    messageHeader.style.justifyContent = 'space-between'; // 两端对齐
    messageHeader.style.alignItems = 'center'; // 垂直居中
    const messageTitle = document.createElement('h2'); // 创建标题
    messageTitle.textContent = '消息'; // 设置文案
    messageHeader.appendChild(messageTitle); // 渲染标题
    messagesContainer.appendChild(messageHeader); // 渲染头部
    const messageList = document.createElement('div'); // 创建消息列表
    messageList.id = 'message-list'; // 设置 ID
    messageList.style.marginTop = '12px'; // 设置间距
    messageList.style.maxHeight = '480px'; // 限制高度
    messageList.style.overflowY = 'auto'; // 启用滚动
    messagesContainer.appendChild(messageList); // 渲染消息列表
    messageForm = document.createElement('form'); // 创建发送表单
    messageForm.style.marginTop = '16px'; // 设置间距
    messageForm.style.display = 'grid'; // 使用网格布局
    messageForm.style.gridTemplateColumns = '120px 1fr 100px'; // 定义列宽
    messageForm.style.gap = '8px'; // 设置间距
    const roleSelect = document.createElement('select'); // 创建角色选择器
    roleSelect.className = 'input'; // 应用样式
    roleSelect.name = 'role'; // 设置 name
    ['user', 'assistant', 'system'].forEach((role) => { // 初始化角色选项
      const option = document.createElement('option'); // 创建选项
      option.value = role; // 设置值
      option.textContent = role; // 设置文本
      roleSelect.appendChild(option); // 添加选项
    });
    const contentInput = document.createElement('input'); // 创建消息输入框
    contentInput.className = 'input'; // 应用样式
    contentInput.name = 'content'; // 设置 name
    contentInput.placeholder = '输入消息内容'; // 设置提示
    contentInput.required = true; // 设置必填
    const sendBtn = document.createElement('button'); // 创建发送按钮
    sendBtn.className = 'button'; // 主按钮样式
    sendBtn.type = 'submit'; // 指定提交类型
    sendBtn.textContent = '发送'; // 按钮文本
    messageForm.appendChild(roleSelect); // 添加角色选择器
    messageForm.appendChild(contentInput); // 添加输入框
    messageForm.appendChild(sendBtn); // 添加发送按钮
    messagesContainer.appendChild(messageForm); // 渲染发送表单
    const user = getCurrentUser(); // 获取当前用户
    await loadChats(user); // 加载会话列表
    createBtn.addEventListener('click', () => openCreateChat(user)); // 绑定新建会话
    sendHandler = async (event) => { // 定义发送消息处理器
      event.preventDefault(); // 阻止默认提交
      if (!currentChatId) { // 若未选择会话
        toast('请选择一个会话', 'info'); // 提示选择会话
        return; // 停止处理
      }
      const formData = new FormData(messageForm); // 读取表单数据
      const role = formData.get('role'); // 获取角色
      const content = formData.get('content'); // 获取内容
      if (!content) { // 内容为空时
        toast('消息内容不能为空', 'error'); // 提示错误
        return; // 停止处理
      }
      sendBtn.disabled = true; // 禁用发送按钮
      const loading = spinner(); // 创建加载指示器
      sendBtn.appendChild(loading); // 显示加载
      try { // 捕获异常
        const result = await createMessage(currentChatId, { role, content }); // 调用发送接口
        const hasAssistantReply = result && typeof result === 'object' && 'answer' in result; // 判断是否触发RAG
        toast(hasAssistantReply ? '助手已生成回答' : '消息已发送', 'success'); // 提示成功
        formData.set('content', ''); // 清空内容
        contentInput.value = ''; // 清空输入框
        await loadMessages(currentChatId); // 刷新消息列表
      } catch (error) { // 捕获错误
        toast(error.message || '发送失败', 'error'); // 显示错误
      } finally { // 收尾处理
        sendBtn.disabled = false; // 恢复按钮
        loading.remove(); // 移除加载动画
      }
    }; // sendHandler 定义结束
    messageForm.addEventListener('submit', sendHandler); // 绑定提交事件
  }, // mount 结束
  unmount() { // 卸载逻辑
    if (messageForm && sendHandler) messageForm.removeEventListener('submit', sendHandler); // 移除事件
    if (containerRef) containerRef.innerHTML = ''; // 清空容器
    containerRef = null; // 释放容器引用
    chatsContainer = null; // 清空会话容器
    messagesContainer = null; // 清空消息容器
    messageForm = null; // 清空表单引用
    sendHandler = null; // 清空处理器引用
    currentChatId = null; // 清空选中会话
    paginationState = { limit: 50, offset: 0 }; // 重置分页状态
  }, // unmount 结束
}; // 模块导出结束

async function loadChats(user) { // 加载会话列表
  if (!chatsContainer) return; // 若容器不存在则退出
  const list = chatsContainer.querySelector('#chat-list'); // 查找列表容器
  if (!list) return; // 若不存在则返回
  list.innerHTML = ''; // 清空列表
  const loading = spinner(); // 创建加载指示器
  list.appendChild(loading); // 显示加载
  try { // 捕获异常
    const response = await getChats({ user_id: user?.id, limit: 50, offset: 0 }); // 请求会话列表
    list.innerHTML = ''; // 清空加载状态
    const chats = response || []; // 获取数组数据
    if (chats.length === 0) { // 无会话时
      const empty = document.createElement('p'); // 创建提示
      empty.className = 'table-empty'; // 应用样式
      empty.textContent = '暂无会话'; // 设置文本
      list.appendChild(empty); // 渲染提示
      return; // 停止处理
    }
    chats.forEach((chat) => { // 遍历会话
      const item = document.createElement('div'); // 创建会话卡片
      item.className = 'table-wrapper'; // 应用样式
      item.style.padding = '12px'; // 设置内边距
      item.style.marginBottom = '8px'; // 设置间距
      item.style.cursor = 'pointer'; // 显示可点击
      item.addEventListener('click', () => { // 点击卡片
        currentChatId = chat.id; // 记录当前会话
        loadMessages(chat.id); // 加载消息
      });
      const title = document.createElement('div'); // 创建标题节点
      title.textContent = chat.title || '未命名会话'; // 显示会话名称
      item.appendChild(title); // 渲染标题
      const actions = document.createElement('div'); // 创建操作区域
      actions.style.display = 'flex'; // 使用弹性布局
      actions.style.gap = '8px'; // 设置间距
      actions.style.marginTop = '8px'; // 设置顶部间距
      const renameBtn = document.createElement('button'); // 创建改名按钮
      renameBtn.className = 'button button--ghost'; // 次级样式
      renameBtn.type = 'button'; // 指定类型
      renameBtn.textContent = '改名'; // 按钮文本
      renameBtn.addEventListener('click', async (event) => { // 绑定改名逻辑
        event.stopPropagation(); // 阻止冒泡
        const newTitle = window.prompt('请输入新的会话标题', chat.title || ''); // 弹出输入框
        if (newTitle === null) return; // 用户取消时结束
        try {
          await updateChat(chat.id, { title: newTitle }); // 更新标题
          toast('标题已更新', 'success'); // 提示成功
          await loadChats(user); // 重新加载会话
        } catch (error) {
          toast(error.message || '更新失败', 'error'); // 提示错误
        }
      });
      actions.appendChild(renameBtn); // 添加改名按钮
      const deleteBtn = document.createElement('button'); // 创建删除按钮
      deleteBtn.className = 'button button--ghost'; // 次级样式
      deleteBtn.type = 'button'; // 指定类型
      deleteBtn.textContent = '删除'; // 按钮文本
      deleteBtn.addEventListener('click', (event) => { // 绑定删除逻辑
        event.stopPropagation(); // 阻止冒泡
        confirmDialog('确定删除该会话及其消息吗？', async () => { // 弹出确认框
          try { // 捕获异常
            await deleteChat(chat.id); // 调用删除接口
            toast('会话已删除', 'success'); // 提示成功
            if (currentChatId === chat.id) { // 若删除的是当前会话
              currentChatId = null; // 清空当前会话
              clearMessages(); // 清空消息列表
            }
            await loadChats(user); // 重新加载会话
          } catch (error) { // 捕获错误
            toast(error.message || '删除失败', 'error'); // 提示错误
          }
        });
      });
      actions.appendChild(deleteBtn); // 添加删除按钮
      item.appendChild(actions); // 渲染操作区域
      list.appendChild(item); // 渲染会话项
    });
  } catch (error) { // 请求失败
    list.innerHTML = ''; // 清空列表
    toast(error.message || '加载会话失败', 'error'); // 提示错误
  }
}

async function loadMessages(chatId) { // 加载消息列表
  if (!messagesContainer) return; // 若容器不存在则退出
  const list = messagesContainer.querySelector('#message-list'); // 查找消息列表
  if (!list) return; // 若不存在则返回
  list.innerHTML = ''; // 清空列表
  const loading = spinner(); // 创建加载指示器
  list.appendChild(loading); // 显示加载
  try { // 捕获异常
    const response = await getMessages(chatId, paginationState); // 请求消息列表
    list.innerHTML = ''; // 移除加载状态
    const messages = Array.isArray(response) ? response : response || []; // 获取数组数据
    if (messages.length === 0) { // 无消息时
      const empty = document.createElement('p'); // 创建提示
      empty.className = 'table-empty'; // 应用样式
      empty.textContent = '暂无消息'; // 设置文本
      list.appendChild(empty); // 渲染提示
      return; // 停止处理
    }
    messages.forEach((msg) => { // 遍历消息
      const item = document.createElement('div'); // 创建消息卡片
      item.className = 'table-wrapper'; // 应用样式
      item.style.marginBottom = '8px'; // 设置间距
      const header = document.createElement('div'); // 创建头部文本
      header.textContent = `${msg.role?.toUpperCase() || 'UNKNOWN'} · ID ${msg.id}`; // 显示角色与 ID
      item.appendChild(header); // 渲染头部
      const content = document.createElement('p'); // 创建内容文本
      content.textContent = msg.content || ''; // 显示消息内容
      item.appendChild(content); // 渲染内容
      appendSources(item, msg.message_metadata); // 渲染引用信息
      const actions = document.createElement('div'); // 创建操作区域
      actions.style.display = 'flex'; // 使用弹性布局
      actions.style.gap = '8px'; // 设置间距
      const editBtn = document.createElement('button'); // 创建编辑按钮
      editBtn.className = 'button button--ghost'; // 次级样式
      editBtn.type = 'button'; // 指定类型
      editBtn.textContent = '编辑'; // 按钮文本
      editBtn.addEventListener('click', async () => { // 绑定编辑逻辑
        const newContent = window.prompt('修改消息内容', msg.content || ''); // 弹出输入框
        if (newContent === null) return; // 取消时退出
        try {
          await updateMessage(msg.id, { content: newContent }); // 更新消息
          toast('消息已更新', 'success'); // 提示成功
          await loadMessages(chatId); // 重新加载消息
        } catch (error) {
          toast(error.message || '更新失败', 'error'); // 提示错误
        }
      });
      actions.appendChild(editBtn); // 添加编辑按钮
      const deleteBtn = document.createElement('button'); // 创建删除按钮
      deleteBtn.className = 'button button--ghost'; // 次级样式
      deleteBtn.type = 'button'; // 指定类型
      deleteBtn.textContent = '删除'; // 按钮文本
      deleteBtn.addEventListener('click', () => { // 绑定删除逻辑
        confirmDialog('确定删除该消息吗？', async () => { // 弹出确认框
          try { // 捕获异常
            await deleteMessage(msg.id); // 调用删除接口
            toast('消息已删除', 'success'); // 提示成功
            await loadMessages(chatId); // 重新加载消息
          } catch (error) { // 捕获错误
            toast(error.message || '删除失败', 'error'); // 提示错误
          }
        });
      });
      actions.appendChild(deleteBtn); // 添加删除按钮
      item.appendChild(actions); // 渲染操作区域
      list.appendChild(item); // 渲染消息项
    });
  } catch (error) { // 请求失败
    list.innerHTML = ''; // 清空列表
    toast(error.message || '加载消息失败', 'error'); // 提示错误
  }
}

async function openCreateChat(user) { // 创建会话
  const title = window.prompt('请输入会话标题', '新会话'); // 弹出输入框
  if (title === null) return; // 用户取消时退出
  try {
    await createChat({ user_id: user?.id, title }); // 调用创建接口
    toast('会话已创建', 'success'); // 提示成功
    await loadChats(user); // 重新加载会话
  } catch (error) {
    toast(error.message || '创建会话失败', 'error'); // 提示错误
  }
}

function clearMessages() { // 清空消息列表
  if (!messagesContainer) return; // 若容器不存在则退出
  const list = messagesContainer.querySelector('#message-list'); // 查找消息列表
  if (list) list.innerHTML = ''; // 清空列表内容
}

function appendSources(container, messageMetadata) { // 渲染引用信息
  const sources = messageMetadata && Array.isArray(messageMetadata.sources) ? messageMetadata.sources : []; // 读取引用列表
  if (sources.length === 0) return; // 无引用则不渲染
  const block = document.createElement('div'); // 创建引用块容器
  block.className = 'message-sources'; // 应用样式
  const title = document.createElement('div'); // 创建标题
  title.className = 'message-sources__title'; // 设置标题样式
  title.textContent = '引用来源'; // 标题文本
  block.appendChild(title); // 添加标题
  const list = document.createElement('ul'); // 创建引用列表
  list.className = 'message-sources__list'; // 应用列表样式
  sources.forEach((source, index) => { // 遍历引用
    const item = document.createElement('li'); // 创建列表项
    item.className = 'message-sources__item'; // 应用样式
    const link = document.createElement('a'); // 创建跳转链接
    link.href = `#/documents/${source.document_uuid}`; // 指向文档详情
    const displayIndex = index + 1; // 人类友好编号
    const docTitle = source.document_title || '未命名文档'; // 文档标题
    const ordinalValue = Number(source.chunk_ordinal); // 转换片段序号
    const chunkOrdinal = Number.isFinite(ordinalValue) ? ordinalValue + 1 : 1; // 片段序号
    link.textContent = `[${displayIndex}] ${docTitle} · 段落 ${chunkOrdinal}`; // 链接文本
    link.addEventListener('click', (event) => { // 绑定导航
      event.preventDefault(); // 阻止默认跳转
      navigate(link.href); // 使用应用内导航
    });
    item.appendChild(link); // 添加链接
    if (typeof source.score === 'number') { // 显示相似度
      const score = document.createElement('span'); // 创建分值标签
      score.className = 'message-sources__score'; // 应用样式
      score.textContent = `相关度 ${source.score.toFixed(3)}`; // 格式化分值
      item.appendChild(score); // 添加分值
    }
    if (source.content) { // 显示摘要
      const snippet = document.createElement('div'); // 创建摘要块
      snippet.className = 'message-sources__snippet'; // 应用样式
      const text = String(source.content); // 转换为字符串
      snippet.textContent = text.length > 160 ? `${text.slice(0, 160)}…` : text; // 截断摘要
      item.appendChild(snippet); // 添加摘要
    }
    list.appendChild(item); // 加入列表
  });
  block.appendChild(list); // 添加列表
  container.appendChild(block); // 将引用块加入消息
}
