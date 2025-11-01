import {
  getChats,
  createChat,
  updateChat,
  deleteChat,
  getMessages,
  createMessage,
  updateMessage,
  deleteMessage,
  getDomains,
} from '../api.js'; // 导入聊天、消息接口
import { toast, spinner, confirmDialog } from '../ui/components.js'; // 引入提示、加载与确认组件
import { getCurrentUser } from '../app.js'; // 引入当前用户信息

let containerRef = null; // 保存容器引用
let chatsContainer = null; // 缓存会话列表容器
let messagesContainer = null; // 缓存消息区域容器
let messageForm = null; // 缓存发送消息表单
let sendHandler = null; // 缓存发送事件处理器
let currentChatId = null; // 当前选中的会话 ID
let paginationState = { limit: 50, offset: 0 }; // 消息分页状态
let questionInput = null; // 用户问题输入框
let topKInput = null; // RAG top_k 输入框
let domainSelect = null; // domain 多选框
let sendBtn = null; // 发送按钮引用
let domainHintText = null; // domain 选择提示
let cachedDomains = []; // 缓存 domain 列表供多处复用
const ragReferenceCache = new Map(); // 记录最近一次 ask 的引用结果
const messageOptionsCache = new Map(); // 记录用户问题使用的 top_k 与 domain 选项

export default { // 导出聊天视图
  async mount(container) { // 挂载逻辑
    containerRef = container; // 保存容器引用
    ragReferenceCache.clear(); // 进入视图时清空引用缓存
    cachedDomains = []; // 重置 domain 缓存
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
    messageForm = document.createElement('form'); // 创建问答表单
    messageForm.style.marginTop = '16px'; // 设置间距
    messageForm.style.display = 'flex'; // 使用纵向布局
    messageForm.style.flexDirection = 'column';
    messageForm.style.gap = '12px'; // 设置间距

    const questionGroup = document.createElement('div'); // 问题输入区域
    questionGroup.className = 'form-group';
    const questionLabel = document.createElement('label');
    questionLabel.className = 'label';
    questionLabel.textContent = '向知识库提问';
    questionLabel.setAttribute('for', 'chat-question');
    questionGroup.appendChild(questionLabel);
    questionInput = document.createElement('textarea');
    questionInput.className = 'input';
    questionInput.id = 'chat-question';
    questionInput.name = 'question';
    questionInput.placeholder = '请输入要咨询的内容，系统会结合知识库作答';
    questionInput.required = true;
    questionInput.style.minHeight = '140px';
    questionGroup.appendChild(questionInput);
    messageForm.appendChild(questionGroup);

    const optionsRow = document.createElement('div'); // 选项区域
    optionsRow.style.display = 'flex';
    optionsRow.style.flexWrap = 'wrap';
    optionsRow.style.gap = '12px';

    const domainGroup = document.createElement('div');
    domainGroup.style.flex = '1 1 260px';
    domainGroup.style.minWidth = '240px';
    const domainLabel = document.createElement('label');
    domainLabel.className = 'label';
    domainLabel.textContent = '限定 Domain (可多选)';
    domainLabel.setAttribute('for', 'chat-domains');
    domainGroup.appendChild(domainLabel);
    domainSelect = document.createElement('select');
    domainSelect.className = 'input';
    domainSelect.id = 'chat-domains';
    domainSelect.multiple = true;
    domainSelect.size = 6;
    domainGroup.appendChild(domainSelect);
    domainHintText = document.createElement('p');
    domainHintText.textContent = '按住 Ctrl/⌘ 可多选，留空表示在全部知识库中检索。';
    domainHintText.style.marginTop = '4px';
    domainHintText.style.fontSize = '12px';
    domainHintText.style.color = '#666';
    domainGroup.appendChild(domainHintText);
    optionsRow.appendChild(domainGroup);

    const topkGroup = document.createElement('div');
    topkGroup.style.flex = '0 0 160px';
    const topkLabel = document.createElement('label');
    topkLabel.className = 'label';
    topkLabel.textContent = 'Top K (可选)';
    topkLabel.setAttribute('for', 'chat-topk');
    topkGroup.appendChild(topkLabel);
    topKInput = document.createElement('input');
    topKInput.className = 'input';
    topKInput.type = 'number';
    topKInput.min = '1';
    topKInput.max = '100';
    topKInput.id = 'chat-topk';
    topKInput.placeholder = '默认使用环境变量';
    topkGroup.appendChild(topKInput);
    optionsRow.appendChild(topkGroup);

    messageForm.appendChild(optionsRow);

    const actionRow = document.createElement('div');
    actionRow.style.display = 'flex';
    actionRow.style.justifyContent = 'flex-end';
    sendBtn = document.createElement('button');
    sendBtn.className = 'button';
    sendBtn.type = 'submit';
    sendBtn.textContent = '发送问题';
    actionRow.appendChild(sendBtn);
    messageForm.appendChild(actionRow);

    messagesContainer.appendChild(messageForm); // 渲染问答表单

    const user = getCurrentUser(); // 获取当前用户
    await loadChats(user); // 加载会话列表
    await loadRagDomains(); // 加载 domain 列表
    createBtn.addEventListener('click', () => openCreateChat(user)); // 绑定新建会话
    sendHandler = async (event) => { // 定义发送消息处理器
      event.preventDefault(); // 阻止默认提交
      if (!currentChatId) { // 若未选择会话
        toast('请选择一个会话', 'info'); // 提示选择会话
        return; // 停止处理
      }
      const question = questionInput?.value?.trim(); // 读取问题
      if (!question) { // 内容为空时
        toast('请输入要咨询的问题', 'error'); // 提示错误
        return; // 停止处理
      }
      const topkRaw = topKInput?.value?.trim(); // 读取 top_k 输入
      const topKValue = topkRaw ? Number(topkRaw) : undefined;
      const domainIds = domainSelect
        ? Array.from(domainSelect.selectedOptions)
            .map((option) => Number(option.value))
            .filter((id) => Number.isFinite(id))
        : [];
      sendBtn.disabled = true; // 禁用发送按钮
      const loading = spinner(); // 创建加载指示器
      sendBtn.appendChild(loading); // 显示加载
      try { // 捕获异常
        const response = await createMessage(currentChatId, {
          role: 'user',
          content: question,
          top_k: Number.isFinite(topKValue) ? topKValue : undefined,
          domain_ids: domainIds.length > 0 ? domainIds : undefined,
        }); // 调用发送接口
        toast('问题已提交，RAG 回答即将生成', 'success'); // 提示成功
        questionInput.value = ''; // 清空输入
        if (topKInput) topKInput.value = ''; // 清空 top_k 输入
        if (response?.assistant?.id && Array.isArray(response.references)) {
          ragReferenceCache.set(response.assistant.id, response.references); // 缓存引用
        }
        if (response?.user?.id) {
          const cachedOptions = {
            top_k: Number.isFinite(topKValue) ? topKValue : undefined,
            domain_ids: domainIds.length > 0 ? domainIds : undefined,
          };
          messageOptionsCache.set(response.user.id, cachedOptions);
        }
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
    if (messageForm && sendHandler) messageForm.removeEventListener('submit', sendHandler); // 移除问答提交事件
    if (containerRef) containerRef.innerHTML = ''; // 清空容器
    containerRef = null; // 释放容器引用
    chatsContainer = null; // 清空会话容器
    messagesContainer = null; // 清空消息容器
    messageForm = null; // 清空表单引用
    sendHandler = null; // 清空处理器引用
    questionInput = null; // 清空问题输入
    topKInput = null; // 清空 top_k 输入
    domainSelect = null; // 清空 domain 多选
    sendBtn = null; // 清空按钮引用
    domainHintText = null; // 清空提示文本
    cachedDomains = []; // 清空缓存的 domain 列表
    ragReferenceCache.clear(); // 清理引用缓存
    messageOptionsCache.clear(); // 清空问题选项缓存
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
    let shouldLoadMessages = false;
    if (currentChatId && !chats.some((chat) => chat.id === currentChatId)) {
      currentChatId = null;
    }
    if (!currentChatId && chats.length > 0) {
      currentChatId = chats[0].id;
      shouldLoadMessages = true;
    }
    chats.forEach((chat) => { // 遍历会话
      const item = document.createElement('div'); // 创建会话卡片
      item.className = 'table-wrapper'; // 应用样式
      item.style.padding = '12px'; // 设置内边距
      item.style.marginBottom = '8px'; // 设置间距
      item.style.cursor = 'pointer'; // 显示可点击
      item.dataset.chatId = String(chat.id);
      item.addEventListener('click', () => { // 点击卡片
        currentChatId = chat.id; // 记录当前会话
        updateChatHighlight(list, currentChatId);
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
    updateChatHighlight(list, currentChatId);
    if (shouldLoadMessages && currentChatId) {
      await loadMessages(currentChatId);
    }
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
    const messages = Array.isArray(response) ? response : response?.items || response || []; // 获取数组数据
    if (messages.length === 0) { // 无消息时
      const empty = document.createElement('p'); // 创建提示
      empty.className = 'table-empty'; // 应用样式
      empty.textContent = '暂无消息'; // 设置文本
      list.appendChild(empty); // 渲染提示
      return; // 停止处理
    }
    const groups = groupMessages(messages);
    const seenUserIds = new Set();
    const seenAssistantIds = new Set();
    groups.forEach((group) => {
      const card = document.createElement('div');
      card.className = 'table-wrapper';
      card.style.marginBottom = '12px';

      if (group.user) {
        seenUserIds.add(group.user.id);
        const userSection = document.createElement('div');
        userSection.style.display = 'flex';
        userSection.style.flexDirection = 'column';
        const headerRow = document.createElement('div');
        headerRow.style.display = 'flex';
        headerRow.style.alignItems = 'flex-start';
        headerRow.style.justifyContent = 'space-between';
        const header = document.createElement('div');
        header.textContent = 'USER';
        header.style.fontWeight = '600';
        headerRow.appendChild(header);
        const content = document.createElement('p');
        content.textContent = group.user.content || '';
        const actions = document.createElement('div');
        actions.style.display = 'flex';
        actions.style.gap = '8px';
        const editBtn = document.createElement('button');
        editBtn.className = 'button button--ghost';
        editBtn.type = 'button';
        editBtn.textContent = '编辑问题';
        editBtn.addEventListener('click', async () => {
          const newContent = window.prompt('修改消息内容', group.user.content || '');
          if (newContent === null) return;
          const trimmedContent = newContent.trim();
          const originalContent = group.user.content || '';
          if (!trimmedContent) {
            toast('内容不能为空', 'error');
            return;
          }
          if (trimmedContent === originalContent) {
            toast('内容未发生变化', 'info');
            return;
          }
          editBtn.disabled = true;
          try {
            await updateMessage(group.user.id, { content: trimmedContent });
            toast('问题已更新', 'success');
            const options = getOptionsForMessage(group.user.id);
            messageOptionsCache.set(group.user.id, options);
            const payload = buildAskPayload(trimmedContent, options);
            let regenResponse = null;
            try {
              regenResponse = await createMessage(chatId, payload);
            } catch (error) {
              toast(error.message || '生成新回答失败', 'error');
            }
            if (regenResponse?.assistant) {
              const references = Array.isArray(regenResponse.references)
                ? regenResponse.references
                : [];
              if (group.assistant) {
                try {
                  await updateMessage(group.assistant.id, {
                    content: regenResponse.assistant.content,
                  });
                  ragReferenceCache.set(group.assistant.id, references);
                  toast('回答已更新', 'success');
                } catch (error) {
                  toast(error.message || '更新回答失败', 'error');
                }
                await safeDeleteMessage(regenResponse.user?.id);
                await safeDeleteMessage(regenResponse.assistant?.id);
              } else {
                await safeDeleteMessage(regenResponse.user?.id);
                if (regenResponse.assistant?.id) {
                  ragReferenceCache.set(regenResponse.assistant.id, references);
                  toast('已生成新的回答', 'success');
                }
              }
            }
          } catch (error) {
            toast(error.message || '更新失败', 'error');
          } finally {
            editBtn.disabled = false;
            await loadMessages(chatId);
          }
        });
        actions.appendChild(editBtn);
        const deleteBtn = document.createElement('button');
        deleteBtn.className = 'button button--ghost';
        deleteBtn.type = 'button';
        deleteBtn.textContent = '删除问答';
        deleteBtn.addEventListener('click', () => {
          confirmDialog('确定删除该问题及其回答吗？', async () => {
            try {
              const tasks = [deleteMessage(group.user.id)];
              if (group.assistant) {
                tasks.push(deleteMessage(group.assistant.id));
                ragReferenceCache.delete(group.assistant.id);
              }
              messageOptionsCache.delete(group.user.id);
              await Promise.all(tasks);
              toast('消息已删除', 'success');
              await loadMessages(chatId);
            } catch (error) {
              toast(error.message || '删除失败', 'error');
            }
          });
        });
        actions.appendChild(deleteBtn);
        headerRow.appendChild(actions);
        userSection.appendChild(headerRow);
        userSection.appendChild(content);
        card.appendChild(userSection);
      }

      if (group.assistant) {
        seenAssistantIds.add(group.assistant.id);
        const divider = document.createElement('hr');
        divider.style.margin = '12px 0';
        card.appendChild(divider);

        const assistantSection = document.createElement('div');
        assistantSection.style.display = 'flex';
        assistantSection.style.flexDirection = 'column';
        const header = document.createElement('div');
        header.textContent = 'ASSISTANT';
        header.style.fontWeight = '600';
        assistantSection.appendChild(header);
        const content = document.createElement('p');
        content.textContent = group.assistant.content || '';
        assistantSection.appendChild(content);
        if (Array.isArray(group.assistant.references) && group.assistant.references.length > 0) {
          ragReferenceCache.set(group.assistant.id, group.assistant.references);
        }
        const references = Array.isArray(group.assistant.references) && group.assistant.references.length > 0
          ? group.assistant.references
          : ragReferenceCache.get(group.assistant.id);
        if (references && references.length > 0) {
          const refTitle = document.createElement('div');
          refTitle.className = 'label';
          refTitle.textContent = '引用 chunks';
          refTitle.style.marginTop = '8px';
          assistantSection.appendChild(refTitle);
          const refList = document.createElement('ul');
          refList.style.margin = '4px 0 0';
          refList.style.paddingLeft = '20px';
          references.forEach((ref) => {
            const refItem = document.createElement('li');
            const chunkId = typeof ref.chunk_id === 'number' ? ref.chunk_id : Number(ref.chunk_id);
            const score = typeof ref.score === 'number' ? ref.score : Number(ref.score);
            const scoreText = Number.isFinite(score) ? score.toFixed(4) : String(ref.score ?? '');
            refItem.textContent = `Chunk #${Number.isFinite(chunkId) ? chunkId : ref.chunk_id} · Score ${scoreText}`;
            refList.appendChild(refItem);
          });
          assistantSection.appendChild(refList);
        }
        card.appendChild(assistantSection);
      }

      list.appendChild(card);
    });
    messageOptionsCache.forEach((_, key) => {
      if (!seenUserIds.has(key)) {
        messageOptionsCache.delete(key);
      }
    });
    ragReferenceCache.forEach((_, key) => {
      if (!seenAssistantIds.has(key)) {
        ragReferenceCache.delete(key);
      }
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
    const created = await createChat({ user_id: user?.id, title }); // 调用创建接口
    toast('会话已创建', 'success'); // 提示成功
    if (created?.id) {
      currentChatId = created.id;
    }
    await loadChats(user); // 重新加载会话
    if (currentChatId) {
      await loadMessages(currentChatId);
    }
  } catch (error) {
    toast(error.message || '创建会话失败', 'error'); // 提示错误
  }
}

async function loadRagDomains() { // 加载可用 domain 列表
  try { // 捕获异常
    const response = await getDomains({ limit: 200, offset: 0 }); // 请求域列表
    const domains = Array.isArray(response) ? response : response?.items || []; // 兼容不同返回格式
    cachedDomains = domains; // 缓存数据
    populateDomainSelects(domains); // 渲染到选择器
  } catch (error) {
    toast(error.message || '加载 domain 列表失败', 'error'); // 提示错误
    populateDomainSelects([]); // 回退为空状态
  }
}

function populateDomainSelects(domains) { // 将 domain 渲染到选择器
  if (domainSelect) { // 渲染聊天问答区域的多选框
    domainSelect.innerHTML = ''; // 清空旧选项
    if (!domains.length) { // 无可选 domain
      const option = document.createElement('option'); // 创建提示项
      option.value = ''; // 空值
      option.textContent = '暂无可选 domain'; // 文案
      option.disabled = true; // 禁用选择
      option.selected = true; // 默认选中提示
      domainSelect.appendChild(option); // 渲染选项
      domainSelect.disabled = true; // 禁用多选
      if (domainHintText) domainHintText.textContent = '暂无 domain，系统会对全部知识库检索。'; // 更新提示
    } else {
      domains.forEach((domain) => { // 遍历 domain
        const option = document.createElement('option'); // 创建选项
        option.value = String(domain.id); // 设置值
        option.textContent = `${domain.name || '未命名'} (#${domain.id})`; // 设置文案
        domainSelect.appendChild(option); // 渲染选项
      });
      domainSelect.disabled = false; // 启用选择
      if (domainHintText) domainHintText.textContent = '按住 Ctrl/⌘ 可多选，留空表示在全部知识库中检索。'; // 还原提示
    }
  }
}

function clearMessages() { // 清空消息列表
  if (!messagesContainer) return; // 若容器不存在则退出
  const list = messagesContainer.querySelector('#message-list'); // 查找消息列表
  if (list) list.innerHTML = ''; // 清空列表内容
  ragReferenceCache.clear(); // 清理引用缓存
}

function groupMessages(messages) {
  const groups = [];
  let pending = null;
  messages.forEach((msg) => {
    if (msg.role === 'user') {
      if (pending) {
        groups.push(pending);
      }
      pending = { user: msg, assistant: null };
    } else if (msg.role === 'assistant') {
      if (pending && !pending.assistant) {
        pending.assistant = msg;
        groups.push(pending);
        pending = null;
      } else {
        groups.push({ user: null, assistant: msg });
      }
    } else {
      groups.push({ user: msg, assistant: null });
      pending = null;
    }
  });
  if (pending) {
    groups.push(pending);
  }
  return groups;
}

function updateChatHighlight(listContainer, activeId) {
  if (!listContainer) return;
  listContainer.querySelectorAll('.table-wrapper').forEach((item) => {
    item.classList.remove('table-wrapper--active');
    item.style.border = '';
  });
  if (!activeId) return;
  const activeItem = Array.from(listContainer.querySelectorAll('.table-wrapper')).find(
    (node) => node.dataset?.chatId === String(activeId),
  );
  if (activeItem) {
    activeItem.classList.add('table-wrapper--active');
    activeItem.style.border = '2px solid #3b82f6';
  }
}

function getOptionsForMessage(messageId) {
  const cached = messageOptionsCache.get(messageId);
  if (cached) {
    const topK = typeof cached.top_k === 'number' && Number.isFinite(cached.top_k)
      ? cached.top_k
      : undefined;
    const domainIds = Array.isArray(cached.domain_ids)
      ? cached.domain_ids.filter((id) => Number.isFinite(id))
      : undefined;
    if (topK !== undefined || (domainIds && domainIds.length > 0)) {
      return {
        top_k: topK,
        domain_ids: domainIds && domainIds.length > 0 ? [...domainIds] : undefined,
      };
    }
  }
  return collectCurrentQuestionOptions();
}

function collectCurrentQuestionOptions() {
  const domainIds = domainSelect
    ? Array.from(domainSelect.selectedOptions)
        .map((option) => Number(option.value))
        .filter((id) => Number.isFinite(id))
    : [];
  const topRaw = topKInput?.value?.trim();
  const topK = topRaw ? Number(topRaw) : undefined;
  return {
    top_k: Number.isFinite(topK) ? topK : undefined,
    domain_ids: domainIds.length > 0 ? domainIds : undefined,
  };
}

function buildAskPayload(content, options) {
  const payload = { role: 'user', content };
  if (options?.top_k !== undefined) {
    payload.top_k = options.top_k;
  }
  if (Array.isArray(options?.domain_ids) && options.domain_ids.length > 0) {
    payload.domain_ids = options.domain_ids;
  }
  return payload;
}

async function safeDeleteMessage(messageId) {
  if (typeof messageId !== 'number' || !Number.isFinite(messageId)) return;
  try {
    await deleteMessage(messageId);
  } catch (error) {
    console.warn('删除临时消息失败', messageId, error);
  }
}
