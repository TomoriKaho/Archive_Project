import {
  getChats,
  createChat,
  updateChat,
  deleteChat,
  getMessages,
  createMessage,
  updateMessage,
  deleteMessage,
  askChatWithRag,
  previewRag,
  getDomains,
} from '../api.js'; // 导入聊天、消息与 RAG 接口
import { toast, spinner, confirmDialog } from '../ui/components.js'; // 引入提示、加载与确认组件
import { getCurrentUser } from '../app.js'; // 引入当前用户信息

let containerRef = null; // 保存容器引用
let chatsContainer = null; // 缓存会话列表容器
let messagesContainer = null; // 缓存消息区域容器
let messageForm = null; // 缓存发送消息表单
let sendHandler = null; // 缓存发送事件处理器
let currentChatId = null; // 当前选中的会话 ID
let paginationState = { limit: 50, offset: 0 }; // 消息分页状态
let ragForm = null; // RAG 问答表单引用
let ragSubmitHandler = null; // RAG 提交事件处理器
let ragQuestionInput = null; // RAG 问题输入框
let ragTopKInput = null; // RAG top_k 输入框
let ragDomainSelect = null; // RAG domain 多选框
let ragSubmitBtn = null; // RAG 提交按钮
let ragDomainHint = null; // RAG domain 提示文本
let previewForm = null; // RAG 预览表单引用
let previewSubmitHandler = null; // RAG 预览提交处理器
let previewQuestionInput = null; // RAG 预览问题输入框
let previewTopKInput = null; // RAG 预览 top_k 输入
let previewDomainSelect = null; // RAG 预览 domain 下拉
let previewSubmitBtn = null; // RAG 预览按钮
let previewResultsContainer = null; // RAG 预览结果容器
let cachedDomains = []; // 缓存 domain 列表供多处复用
const ragReferenceCache = new Map(); // 记录最近一次 ask 的引用结果

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

    const ragSection = document.createElement('section'); // 创建 RAG 区域
    ragSection.style.marginTop = '24px'; // 设置顶部间距
    const ragHeading = document.createElement('h3'); // RAG 标题
    ragHeading.textContent = 'RAG 智能问答'; // 设置标题
    ragSection.appendChild(ragHeading); // 渲染标题
    const ragDescription = document.createElement('p'); // RAG 描述
    ragDescription.textContent = '提交问题后将自动创建问答消息并使用知识库生成回答。'; // 设置描述
    ragDescription.style.margin = '4px 0 12px'; // 设置间距
    ragDescription.style.color = '#555'; // 调整颜色
    ragDescription.style.fontSize = '13px'; // 调整字号
    ragSection.appendChild(ragDescription); // 渲染描述
    ragForm = document.createElement('form'); // 创建 RAG 表单
    ragForm.style.display = 'grid'; // 使用网格布局
    ragForm.style.gap = '12px'; // 设置间距
    ragForm.setAttribute('aria-label', 'RAG 问答表单'); // 设置无障碍说明
    ragSection.appendChild(ragForm); // 渲染表单
    const questionGroup = document.createElement('div'); // 问题容器
    questionGroup.className = 'form-group'; // 应用样式
    const questionLabel = document.createElement('label'); // 问题标签
    questionLabel.className = 'label'; // 标签样式
    questionLabel.textContent = '问题'; // 标签文本
    questionLabel.setAttribute('for', 'rag-question'); // 关联输入
    questionGroup.appendChild(questionLabel); // 渲染标签
    ragQuestionInput = document.createElement('textarea'); // 问题输入
    ragQuestionInput.className = 'input'; // 应用样式
    ragQuestionInput.id = 'rag-question'; // 设置 ID
    ragQuestionInput.name = 'question'; // 设置 name
    ragQuestionInput.required = true; // 设置必填
    ragQuestionInput.placeholder = '请输入要向知识库查询的问题'; // 设置提示
    ragQuestionInput.style.minHeight = '120px'; // 调整高度
    questionGroup.appendChild(ragQuestionInput); // 渲染输入
    ragForm.appendChild(questionGroup); // 添加问题容器
    const topkGroup = document.createElement('div'); // top_k 容器
    topkGroup.className = 'form-group'; // 应用样式
    const topkLabel = document.createElement('label'); // top_k 标签
    topkLabel.className = 'label'; // 标签样式
    topkLabel.textContent = 'Top K (可选)'; // 标签文本
    topkLabel.setAttribute('for', 'rag-topk'); // 关联输入
    topkGroup.appendChild(topkLabel); // 渲染标签
    ragTopKInput = document.createElement('input'); // top_k 输入
    ragTopKInput.className = 'input'; // 应用样式
    ragTopKInput.type = 'number'; // 数字输入
    ragTopKInput.min = '1'; // 最小值
    ragTopKInput.max = '100'; // 最大值
    ragTopKInput.id = 'rag-topk'; // 设置 ID
    ragTopKInput.placeholder = '留空则使用默认环境值'; // 设置提示
    topkGroup.appendChild(ragTopKInput); // 渲染输入
    ragForm.appendChild(topkGroup); // 添加 top_k 容器
    const domainGroup = document.createElement('div'); // domain 容器
    domainGroup.className = 'form-group'; // 应用样式
    const domainLabel = document.createElement('label'); // domain 标签
    domainLabel.className = 'label'; // 标签样式
    domainLabel.textContent = '限制 Domain (可多选)'; // 标签文本
    domainLabel.setAttribute('for', 'rag-domains'); // 关联选择器
    domainGroup.appendChild(domainLabel); // 渲染标签
    ragDomainSelect = document.createElement('select'); // domain 多选
    ragDomainSelect.className = 'input'; // 应用样式
    ragDomainSelect.id = 'rag-domains'; // 设置 ID
    ragDomainSelect.multiple = true; // 启用多选
    ragDomainSelect.size = 6; // 默认展示选项数量
    domainGroup.appendChild(ragDomainSelect); // 渲染多选框
    const domainHint = document.createElement('p'); // 多选提示
    domainHint.textContent = '按住 Ctrl/⌘ 可多选，留空表示在全部 domain 中检索。'; // 提示文案
    domainHint.style.marginTop = '4px'; // 设置间距
    domainHint.style.fontSize = '12px'; // 调整字号
    domainHint.style.color = '#666'; // 调整颜色
    ragDomainHint = domainHint; // 缓存提示文本以便动态更新
    domainGroup.appendChild(domainHint); // 渲染提示
    ragForm.appendChild(domainGroup); // 添加 domain 容器
    const ragActions = document.createElement('div'); // RAG 按钮容器
    ragActions.style.display = 'flex'; // 使用弹性布局
    ragActions.style.justifyContent = 'flex-end'; // 右对齐按钮
    ragActions.style.gap = '12px'; // 设置间距
    ragForm.appendChild(ragActions); // 渲染按钮容器
    ragSubmitBtn = document.createElement('button'); // RAG 提交按钮
    ragSubmitBtn.className = 'button'; // 主按钮样式
    ragSubmitBtn.type = 'submit'; // 提交表单
    ragSubmitBtn.textContent = '发起 RAG'; // 按钮文本
    ragActions.appendChild(ragSubmitBtn); // 渲染按钮
    messagesContainer.appendChild(ragSection); // 将 RAG 区域加入消息面板

    const previewCard = document.createElement('div'); // 创建 RAG 预览卡片
    previewCard.className = 'table-wrapper'; // 使用卡片样式
    previewCard.style.marginTop = '24px'; // 设置外边距
    previewCard.style.padding = '16px'; // 设置内边距
    const previewTitle = document.createElement('h2'); // 预览标题
    previewTitle.textContent = 'RAG 预览'; // 设置标题
    previewCard.appendChild(previewTitle); // 渲染标题
    const previewDescription = document.createElement('p'); // 预览描述
    previewDescription.textContent = '快速调试检索命中的 chunks（不会写入消息）。'; // 描述文案
    previewDescription.style.margin = '4px 0 16px'; // 设置间距
    previewDescription.style.color = '#555'; // 设置颜色
    previewDescription.style.fontSize = '13px'; // 调整字号
    previewCard.appendChild(previewDescription); // 渲染描述
    previewForm = document.createElement('form'); // 创建预览表单
    previewForm.style.display = 'grid'; // 使用网格布局
    previewForm.style.gap = '12px'; // 设置间距
    previewForm.setAttribute('aria-label', 'RAG 预览表单'); // 设置无障碍说明
    previewCard.appendChild(previewForm); // 渲染表单
    const previewQuestionGroup = document.createElement('div'); // 预览问题容器
    previewQuestionGroup.className = 'form-group'; // 应用样式
    const previewQuestionLabel = document.createElement('label'); // 预览问题标签
    previewQuestionLabel.className = 'label'; // 标签样式
    previewQuestionLabel.textContent = '问题'; // 标签文本
    previewQuestionLabel.setAttribute('for', 'rag-preview-question'); // 关联输入
    previewQuestionGroup.appendChild(previewQuestionLabel); // 渲染标签
    previewQuestionInput = document.createElement('input'); // 预览问题输入
    previewQuestionInput.className = 'input'; // 应用样式
    previewQuestionInput.type = 'text'; // 文本输入
    previewQuestionInput.id = 'rag-preview-question'; // 设置 ID
    previewQuestionInput.name = 'q'; // 设置 name
    previewQuestionInput.required = true; // 设置必填
    previewQuestionInput.placeholder = '请输入需要调试的问题'; // 设置提示
    previewQuestionGroup.appendChild(previewQuestionInput); // 渲染输入
    previewForm.appendChild(previewQuestionGroup); // 添加问题容器
    const previewTopkGroup = document.createElement('div'); // 预览 top_k 容器
    previewTopkGroup.className = 'form-group'; // 应用样式
    const previewTopkLabel = document.createElement('label'); // 预览 top_k 标签
    previewTopkLabel.className = 'label'; // 标签样式
    previewTopkLabel.textContent = 'Top K (可选)'; // 标签文本
    previewTopkLabel.setAttribute('for', 'rag-preview-topk'); // 关联输入
    previewTopkGroup.appendChild(previewTopkLabel); // 渲染标签
    previewTopKInput = document.createElement('input'); // 预览 top_k 输入
    previewTopKInput.className = 'input'; // 应用样式
    previewTopKInput.type = 'number'; // 数字输入
    previewTopKInput.min = '1'; // 最小值
    previewTopKInput.max = '100'; // 最大值
    previewTopKInput.id = 'rag-preview-topk'; // 设置 ID
    previewTopKInput.placeholder = '留空则使用默认值'; // 设置提示
    previewTopkGroup.appendChild(previewTopKInput); // 渲染输入
    previewForm.appendChild(previewTopkGroup); // 添加 top_k 容器
    const previewDomainGroup = document.createElement('div'); // 预览 domain 容器
    previewDomainGroup.className = 'form-group'; // 应用样式
    const previewDomainLabel = document.createElement('label'); // 预览 domain 标签
    previewDomainLabel.className = 'label'; // 标签样式
    previewDomainLabel.textContent = '限定 Domain (可选)'; // 标签文本
    previewDomainLabel.setAttribute('for', 'rag-preview-domain'); // 关联选择器
    previewDomainGroup.appendChild(previewDomainLabel); // 渲染标签
    previewDomainSelect = document.createElement('select'); // 预览 domain 下拉
    previewDomainSelect.className = 'input'; // 应用样式
    previewDomainSelect.id = 'rag-preview-domain'; // 设置 ID
    previewDomainSelect.name = 'domain_id'; // 设置 name
    const defaultDomainOption = document.createElement('option'); // 默认选项
    defaultDomainOption.value = ''; // 空值表示全部
    defaultDomainOption.textContent = '全部 domain'; // 选项文案
    previewDomainSelect.appendChild(defaultDomainOption); // 渲染默认项
    previewDomainGroup.appendChild(previewDomainSelect); // 渲染下拉框
    previewForm.appendChild(previewDomainGroup); // 添加 domain 容器
    const previewActions = document.createElement('div'); // 预览按钮容器
    previewActions.style.display = 'flex'; // 使用弹性布局
    previewActions.style.justifyContent = 'flex-end'; // 右对齐
    previewActions.style.gap = '12px'; // 设置间距
    previewForm.appendChild(previewActions); // 渲染按钮容器
    previewSubmitBtn = document.createElement('button'); // 预览提交按钮
    previewSubmitBtn.className = 'button'; // 主按钮样式
    previewSubmitBtn.type = 'submit'; // 提交表单
    previewSubmitBtn.textContent = '运行检索'; // 按钮文本
    previewActions.appendChild(previewSubmitBtn); // 渲染按钮
    previewResultsContainer = document.createElement('div'); // 预览结果容器
    previewResultsContainer.style.marginTop = '16px'; // 设置间距
    previewResultsContainer.textContent = '提交问题后显示检索结果。'; // 初始提示
    previewCard.appendChild(previewResultsContainer); // 渲染结果容器
    container.appendChild(previewCard); // 将预览卡片加入页面

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
        await createMessage(currentChatId, { role, content }); // 调用发送接口
        toast('消息已发送', 'success'); // 提示成功
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
    ragSubmitHandler = async (event) => { // RAG 提交逻辑
      event.preventDefault(); // 阻止默认提交
      if (!currentChatId) { // 未选择会话
        toast('请选择一个会话', 'info'); // 提示用户
        return; // 终止处理
      }
      const question = ragQuestionInput?.value?.trim(); // 读取问题
      if (!question) { // 问题为空
        toast('请输入问题后再提交', 'error'); // 提示错误
        return; // 终止处理
      }
      const topkRaw = ragTopKInput?.value?.trim(); // 读取 top_k
      const topKValue = topkRaw ? Number(topkRaw) : undefined; // 转换为数字
      const domainIds = ragDomainSelect && !ragDomainSelect.disabled
        ? Array.from(ragDomainSelect.selectedOptions)
            .map((option) => Number(option.value))
            .filter((id) => Number.isFinite(id))
        : []; // 解析 domain
      ragSubmitBtn.disabled = true; // 禁用按钮
      const loading = spinner(); // 创建加载指示器
      ragSubmitBtn.appendChild(loading); // 显示加载
      try {
        const response = await askChatWithRag(currentChatId, {
          question,
          top_k: Number.isFinite(topKValue) ? topKValue : undefined,
          domain_ids: domainIds.length > 0 ? domainIds : undefined,
        }); // 调用后端 RAG 接口
        toast('RAG 回答已生成', 'success'); // 提示成功
        ragQuestionInput.value = ''; // 清空输入
        if (response?.references?.length) { // 缓存引用信息
          ragReferenceCache.set(response.id, response.references);
        }
        await loadMessages(currentChatId); // 刷新消息列表
      } catch (error) {
        toast(error.message || 'RAG 问答失败', 'error'); // 提示错误
      } finally {
        ragSubmitBtn.disabled = false; // 恢复按钮
        loading.remove(); // 移除加载动画
      }
    }; // ragSubmitHandler 结束
    if (ragForm) ragForm.addEventListener('submit', ragSubmitHandler); // 绑定 RAG 表单
    previewSubmitHandler = async (event) => { // 预览提交逻辑
      event.preventDefault(); // 阻止默认提交
      const question = previewQuestionInput?.value?.trim(); // 读取问题
      if (!question) { // 问题为空
        toast('请输入需要预览的问题', 'error'); // 提示错误
        return; // 停止处理
      }
      const topkRaw = previewTopKInput?.value?.trim(); // 读取 top_k
      const topKValue = topkRaw ? Number(topkRaw) : undefined; // 转为数字
      const domainValue = previewDomainSelect?.value; // 读取 domain
      const domainId = domainValue ? Number(domainValue) : undefined; // 转换为数字
      previewSubmitBtn.disabled = true; // 禁用按钮
      const loading = spinner(); // 创建加载指示器
      previewSubmitBtn.appendChild(loading); // 显示加载
      try {
        const result = await previewRag({
          q: question,
          top_k: Number.isFinite(topKValue) ? topKValue : undefined,
          domain_id: Number.isFinite(domainId) ? domainId : undefined,
        }); // 调用预览接口
        const items = Array.isArray(result) ? result : result?.items || []; // 解析数据
        renderPreviewResults(items); // 渲染结果
      } catch (error) {
        toast(error.message || '预览失败', 'error'); // 提示错误
      } finally {
        previewSubmitBtn.disabled = false; // 恢复按钮
        loading.remove(); // 移除加载动画
      }
    }; // previewSubmitHandler 结束
    if (previewForm) previewForm.addEventListener('submit', previewSubmitHandler); // 绑定预览表单
  }, // mount 结束
  unmount() { // 卸载逻辑
    if (messageForm && sendHandler) messageForm.removeEventListener('submit', sendHandler); // 移除普通消息事件
    if (ragForm && ragSubmitHandler) ragForm.removeEventListener('submit', ragSubmitHandler); // 移除 RAG 事件
    if (previewForm && previewSubmitHandler) previewForm.removeEventListener('submit', previewSubmitHandler); // 移除预览事件
    if (containerRef) containerRef.innerHTML = ''; // 清空容器
    containerRef = null; // 释放容器引用
    chatsContainer = null; // 清空会话容器
    messagesContainer = null; // 清空消息容器
    messageForm = null; // 清空表单引用
    sendHandler = null; // 清空处理器引用
    ragForm = null; // 清空 RAG 表单
    ragSubmitHandler = null; // 清空 RAG 处理器
    ragQuestionInput = null; // 清空 RAG 输入
    ragTopKInput = null; // 清空 RAG top_k 输入
    ragDomainSelect = null; // 清空 RAG 选择器
    ragSubmitBtn = null; // 清空 RAG 按钮
    ragDomainHint = null; // 清空 RAG 提示
    previewForm = null; // 清空预览表单
    previewSubmitHandler = null; // 清空预览处理器
    previewQuestionInput = null; // 清空预览输入
    previewTopKInput = null; // 清空预览 top_k 输入
    previewDomainSelect = null; // 清空预览选择器
    previewSubmitBtn = null; // 清空预览按钮
    previewResultsContainer = null; // 清空预览结果容器
    cachedDomains = []; // 清空缓存的 domain 列表
    ragReferenceCache.clear(); // 清理引用缓存
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
    const messages = Array.isArray(response) ? response : response?.items || response || []; // 获取数组数据
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
      const references = Array.isArray(msg.references) && msg.references.length > 0
        ? msg.references
        : ragReferenceCache.get(msg.id); // 读取引用信息
      if (msg.role === 'assistant' && references && references.length > 0) { // 对助手消息展示引用
        const refTitle = document.createElement('div'); // 引用标题
        refTitle.className = 'label'; // 使用标签样式
        refTitle.textContent = '引用 chunks'; // 设置标题
        refTitle.style.marginTop = '8px'; // 调整间距
        item.appendChild(refTitle); // 渲染标题
        const refList = document.createElement('ul'); // 创建引用列表
        refList.style.margin = '4px 0 0'; // 设置外边距
        refList.style.paddingLeft = '20px'; // 设置内边距
        references.forEach((ref) => { // 遍历引用
          const refItem = document.createElement('li'); // 列表项
          const chunkId = typeof ref.chunk_id === 'number' ? ref.chunk_id : Number(ref.chunk_id);
          const score = typeof ref.score === 'number' ? ref.score : Number(ref.score);
          const scoreText = Number.isFinite(score) ? score.toFixed(4) : String(ref.score ?? ''); // 处理得分
          refItem.textContent = `Chunk #${Number.isFinite(chunkId) ? chunkId : ref.chunk_id} · Score ${scoreText}`; // 文案
          refList.appendChild(refItem); // 渲染引用项
        });
        item.appendChild(refList); // 渲染引用列表
      }
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
            ragReferenceCache.delete(msg.id); // 清理引用缓存
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
  if (ragDomainSelect) { // 渲染多选框
    ragDomainSelect.innerHTML = ''; // 清空旧选项
    if (!domains.length) { // 无可选 domain
      const option = document.createElement('option'); // 创建提示项
      option.value = ''; // 空值
      option.textContent = '暂无可选 domain'; // 文案
      option.disabled = true; // 禁用选择
      option.selected = true; // 默认选中提示
      ragDomainSelect.appendChild(option); // 渲染选项
      ragDomainSelect.disabled = true; // 禁用多选
      if (ragDomainHint) ragDomainHint.textContent = '暂无 domain，系统会对全部知识库检索。'; // 更新提示
    } else {
      domains.forEach((domain) => { // 遍历 domain
        const option = document.createElement('option'); // 创建选项
        option.value = String(domain.id); // 设置值
        option.textContent = `${domain.name || '未命名'} (#${domain.id})`; // 设置文案
        ragDomainSelect.appendChild(option); // 渲染选项
      });
      ragDomainSelect.disabled = false; // 启用选择
      if (ragDomainHint) ragDomainHint.textContent = '按住 Ctrl/⌘ 可多选，留空表示在全部 domain 中检索。'; // 还原提示
    }
  }
  if (previewDomainSelect) { // 渲染预览下拉
    const previous = previewDomainSelect.value; // 记录旧值
    previewDomainSelect.innerHTML = ''; // 清空选项
    const defaultOption = document.createElement('option'); // 默认选项
    defaultOption.value = ''; // 空值
    defaultOption.textContent = '全部 domain'; // 文案
    previewDomainSelect.appendChild(defaultOption); // 渲染默认项
    domains.forEach((domain) => { // 遍历 domain
      const option = document.createElement('option'); // 创建选项
      option.value = String(domain.id); // 设置值
      option.textContent = `${domain.name || '未命名'} (#${domain.id})`; // 文案
      previewDomainSelect.appendChild(option); // 渲染选项
    });
    if (previous && domains.some((domain) => String(domain.id) === previous)) { // 尝试恢复旧值
      previewDomainSelect.value = previous; // 恢复选择
    }
  }
}

function renderPreviewResults(items) { // 渲染 RAG 预览结果
  if (!previewResultsContainer) return; // 若无容器则退出
  previewResultsContainer.innerHTML = ''; // 清空旧内容
  const results = Array.isArray(items) ? items : []; // 规范化数组
  if (results.length === 0) { // 无数据时
    const empty = document.createElement('p'); // 创建提示
    empty.className = 'table-empty'; // 应用样式
    empty.textContent = '没有检索到相关 chunk'; // 文案
    previewResultsContainer.appendChild(empty); // 渲染提示
    return; // 停止处理
  }
  results.forEach((item) => { // 遍历结果
    const card = document.createElement('div'); // 创建结果卡片
    card.style.border = '1px solid #e5e7eb'; // 设置边框
    card.style.borderRadius = '8px'; // 设置圆角
    card.style.padding = '12px'; // 设置内边距
    card.style.marginBottom = '12px'; // 设置外边距
    const header = document.createElement('div'); // 创建头部
    header.style.fontWeight = '600'; // 加粗
    header.textContent = `Chunk #${item.chunk_id} · Doc ${item.document_id ?? '-'} · Domain ${item.domain_id ?? '-'}`; // 显示基础信息
    card.appendChild(header); // 渲染头部
    const scoreValue = typeof item.score === 'number' ? item.score : Number(item.score); // 解析得分
    const score = document.createElement('div'); // 创建得分节点
    score.style.margin = '4px 0 8px'; // 设置间距
    score.textContent = `Score: ${Number.isFinite(scoreValue) ? scoreValue.toFixed(4) : item.score ?? 'N/A'}`; // 显示得分
    card.appendChild(score); // 渲染得分
    const content = document.createElement('p'); // 创建内容片段
    content.style.margin = '0'; // 移除外边距
    content.style.whiteSpace = 'pre-wrap'; // 保留换行
    content.style.wordBreak = 'break-word'; // 自动换行
    content.textContent = item.content_preview || ''; // 显示文本
    card.appendChild(content); // 渲染内容
    previewResultsContainer.appendChild(card); // 添加卡片
  });
}

function clearMessages() { // 清空消息列表
  if (!messagesContainer) return; // 若容器不存在则退出
  const list = messagesContainer.querySelector('#message-list'); // 查找消息列表
  if (list) list.innerHTML = ''; // 清空列表内容
  ragReferenceCache.clear(); // 清理引用缓存
}
