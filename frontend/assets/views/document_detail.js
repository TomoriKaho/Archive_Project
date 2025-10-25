import { getDocumentByUUID, getChunksByDocId, getChunksByUUID, deleteDocumentByUUID } from '../api.js'; // 导入文档与 chunks 接口
import { toast, spinner, confirmDialog } from '../ui/components.js'; // 引入提示、加载与确认组件
import { navigate } from '../app.js'; // 引入导航函数

let containerRef = null; // 保存容器引用
let docData = null; // 缓存文档数据
let chunksCache = []; // 缓存 chunk 列表
let filterInput = null; // 缓存过滤输入框
let chunksContainer = null; // 缓存 chunk 显示容器
let rawContainer = null; // 缓存原始内容容器

export default { // 导出文档详情视图
  async mount(container, params) { // 挂载逻辑
    containerRef = container; // 保存容器引用
    const uuid = params?.uuid; // 获取文档 UUID
    if (!uuid) { // 如果缺少参数
      container.textContent = '缺少文档标识'; // 显示错误提示
      return; // 停止处理
    }
    const title = document.createElement('h1'); // 创建标题元素
    title.textContent = '文档详情'; // 设置标题文本
    container.appendChild(title); // 渲染标题
    const loading = spinner(); // 创建加载指示器
    container.appendChild(loading); // 显示加载状态
    try { // 捕获请求错误
      docData = await getDocumentByUUID(uuid); // 请求文档数据
      renderHeader(container, docData); // 渲染头部信息
      loading.remove(); // 移除加载动画
      await loadChunks(docData); // 加载 chunk 列表
      renderTabs(container, docData); // 渲染标签页
    } catch (error) { // 请求失败
      loading.remove(); // 移除加载动画
      container.innerHTML = ''; // 清空内容
      if (error.status === 404) { // 文档不存在
        container.textContent = '文档不存在或已删除'; // 显示提示
      } else { // 其他错误
        container.textContent = error.message || '加载文档失败'; // 显示错误信息
      }
    }
  }, // mount 结束
  unmount() { // 卸载逻辑
    if (containerRef) containerRef.innerHTML = ''; // 清空容器
    containerRef = null; // 释放容器引用
    docData = null; // 清空文档缓存
    chunksCache = []; // 清空 chunk 缓存
    filterInput = null; // 清空输入框引用
    chunksContainer = null; // 清空 chunks 容器引用
    rawContainer = null; // 清空原始内容容器引用
  }, // unmount 结束
}; // 模块导出结束

function renderHeader(container, doc) { // 渲染文档头部信息
  const infoCard = document.createElement('div'); // 创建信息卡片
  infoCard.className = 'table-wrapper'; // 应用样式
  const metaList = document.createElement('ul'); // 创建列表容器
  metaList.style.listStyle = 'none'; // 移除默认样式
  metaList.style.padding = '0'; // 去掉内边距
  metaList.style.margin = '0'; // 去掉外边距
  const fields = [ // 构造需要展示的字段
    ['UUID', doc.uuid], // 文档 UUID
    ['ID', doc.id], // 文档 ID
    ['标题', doc.title], // 标题
    ['Domain ID', doc.domain_id], // 域 ID
    ['创建时间', doc.created_at], // 创建时间
  ];
  fields.forEach(([label, value]) => { // 遍历字段
    const item = document.createElement('li'); // 创建列表项
    item.textContent = `${label}：${value}`; // 设置文本
    metaList.appendChild(item); // 添加到列表
  });
  infoCard.appendChild(metaList); // 将列表加入卡片
  const actions = document.createElement('div'); // 创建操作区域
  actions.style.display = 'flex'; // 设置水平布局
  actions.style.gap = '12px'; // 设置按钮间距
  actions.style.marginTop = '16px'; // 设置顶部间距
  const backBtn = document.createElement('button'); // 创建返回按钮
  backBtn.className = 'button button--ghost'; // 使用次级样式
  backBtn.type = 'button'; // 指定类型
  backBtn.textContent = '返回列表'; // 按钮文本
  backBtn.addEventListener('click', () => navigate('#/documents')); // 点击返回列表
  actions.appendChild(backBtn); // 添加返回按钮
  const deleteBtn = document.createElement('button'); // 创建删除按钮
  deleteBtn.className = 'button'; // 主按钮样式
  deleteBtn.type = 'button'; // 指定类型
  deleteBtn.textContent = '删除文档'; // 按钮文本
  deleteBtn.addEventListener('click', () => { // 绑定删除逻辑
    confirmDialog('确定删除该文档及其 chunks 吗？', async () => { // 弹出确认对话框
      try { // 捕获异常
        await deleteDocumentByUUID(doc.uuid); // 调用删除接口
        toast('文档已删除', 'success'); // 提示成功
        navigate('#/documents'); // 跳回文档列表
      } catch (error) { // 捕获错误
        toast(error.message || '删除失败', 'error'); // 显示错误
      }
    }); // confirmDialog 结束
  }); // 删除按钮事件结束
  actions.appendChild(deleteBtn); // 添加删除按钮
  infoCard.appendChild(actions); // 将操作区域加入卡片
  container.appendChild(infoCard); // 渲染卡片
}

async function loadChunks(doc) { // 加载 chunk 数据
  chunksCache = []; // 重置缓存
  try { // 优先尝试通过文档 ID 获取
    const res = await getChunksByDocId(doc.id); // 请求 chunk 列表
    chunksCache = res || []; // 缓存结果
  } catch (error) { // 若失败则尝试 UUID
    try { // 备用方案
      const fallback = await getChunksByUUID(doc.uuid); // 使用 UUID 请求
      chunksCache = fallback || []; // 缓存结果
    } catch (innerError) { // 仍失败
      toast('无法加载 chunks', 'error'); // 提示错误
    }
  }
  updateRawContent(); // 每次加载后根据最新 chunk 更新原文内容
}

function renderTabs(container, doc) { // 渲染标签页
  const tabBar = document.createElement('div'); // 创建标签栏
  tabBar.style.display = 'flex'; // 设置水平布局
  tabBar.style.gap = '12px'; // 设置间距
  tabBar.style.marginTop = '24px'; // 设置顶部间距
  const chunksBtn = document.createElement('button'); // 创建 chunk 标签按钮
  chunksBtn.className = 'button'; // 主按钮样式
  chunksBtn.type = 'button'; // 指定类型
  chunksBtn.textContent = 'Chunks'; // 按钮文本
  const rawBtn = document.createElement('button'); // 创建原始内容按钮
  rawBtn.className = 'button button--ghost'; // 次级按钮样式
  rawBtn.type = 'button'; // 指定类型
  rawBtn.textContent = '原始内容'; // 按钮文本
  tabBar.appendChild(chunksBtn); // 添加 chunk 按钮
  tabBar.appendChild(rawBtn); // 添加原始内容按钮
  container.appendChild(tabBar); // 渲染标签栏
  const contentArea = document.createElement('div'); // 创建内容区域
  contentArea.style.marginTop = '16px'; // 设置顶部间距
  container.appendChild(contentArea); // 渲染内容区域
  chunksContainer = document.createElement('div'); // 创建 chunk 容器
  rawContainer = document.createElement('pre'); // 创建原始内容容器
  updateRawContent(); // 根据已有 chunk 拼接原始内容文本
  rawContainer.style.whiteSpace = 'pre-wrap'; // 保留换行
  rawContainer.style.wordBreak = 'break-word'; // 防止溢出
  const filterGroup = document.createElement('div'); // 创建过滤输入容器
  filterGroup.className = 'form-group'; // 应用样式
  const filterLabel = document.createElement('label'); // 创建过滤标签
  filterLabel.className = 'label'; // 设置样式
  filterLabel.textContent = 'Chunks 关键字过滤'; // 标签文本
  filterGroup.appendChild(filterLabel); // 添加标签
  filterInput = document.createElement('input'); // 创建输入框
  filterInput.className = 'input'; // 应用样式
  filterInput.type = 'search'; // 指定类型
  filterInput.placeholder = '输入关键词过滤 chunk 内容'; // 提示文本
  filterInput.addEventListener('input', () => renderChunksList()); // 输入变化时刷新列表
  filterGroup.appendChild(filterInput); // 添加输入框
  chunksContainer.appendChild(filterGroup); // 将过滤器加入 chunk 容器
  const chunksList = document.createElement('div'); // 创建列表容器
  chunksList.id = 'chunks-list'; // 设置 ID
  chunksContainer.appendChild(chunksList); // 添加容器
  renderChunksList(); // 在容器挂载后渲染初始 chunk 列表
  const showChunks = () => { // 定义显示 chunk 的函数
    chunksBtn.className = 'button'; // 高亮 chunk 按钮
    rawBtn.className = 'button button--ghost'; // 取消原始内容高亮
    contentArea.innerHTML = ''; // 清空内容区域
    contentArea.appendChild(chunksContainer); // 显示 chunk 容器
    renderChunksList(); // 刷新列表
  }; // showChunks 结束
  const showRaw = () => { // 定义显示原始内容的函数
    chunksBtn.className = 'button button--ghost'; // 取消 chunk 按钮高亮
    rawBtn.className = 'button'; // 高亮原始内容按钮
    contentArea.innerHTML = ''; // 清空内容区域
    contentArea.appendChild(rawContainer); // 显示原始内容
  }; // showRaw 结束
  chunksBtn.addEventListener('click', showChunks); // 绑定 chunk 标签点击
  rawBtn.addEventListener('click', showRaw); // 绑定原始内容标签点击
  showChunks(); // 默认显示 chunk 列表
}

function renderChunksList() { // 渲染 chunk 列表
  if (!chunksContainer) return; // 若容器不存在则退出
  const list = chunksContainer.querySelector('#chunks-list'); // 查找列表容器
  if (!list) return; // 若不存在则返回
  list.innerHTML = ''; // 清空列表
  const keyword = filterInput?.value?.toLowerCase() || ''; // 获取过滤关键词
  const filtered = chunksCache.filter((chunk) => { // 过滤 chunk
    if (!keyword) return true; // 无关键词时不过滤
    return String(chunk.content || '').toLowerCase().includes(keyword); // 按内容匹配
  });
  if (filtered.length === 0) { // 若无匹配项
    const empty = document.createElement('p'); // 创建空状态文本
    empty.className = 'table-empty'; // 应用样式
    empty.textContent = '没有匹配的 chunk'; // 设置文案
    list.appendChild(empty); // 渲染空状态
    return; // 结束函数
  }
  const sorted = [...filtered].sort( // 创建排序后的副本以保障序号顺序
    (a, b) => (a.ordinal ?? a.seq ?? 0) - (b.ordinal ?? b.seq ?? 0), // 兼容旧字段命名
  );
  sorted.forEach((chunk) => { // 遍历过滤后的 chunk
    const item = document.createElement('details'); // 使用 details 元素以支持点击展开
    item.className = 'table-wrapper'; // 应用统一卡片样式
    item.style.marginBottom = '12px'; // 设置列表间距
    const summary = document.createElement('summary'); // 创建 summary 作为可点击标题
    const previewText = chunk.content || ''; // 读取 chunk 正文
    const truncated = previewText.slice(0, 50); // 截取前50字符作为预览
    const suffix = previewText.length > 50 ? '…' : ''; // 超长时追加省略号
    summary.textContent = `序号：${chunk.ordinal ?? chunk.seq ?? '-'} ｜ ID：${chunk.id ?? '-'} ｜ 预览：${truncated}${suffix}`; // 构造可读的预览标题
    item.appendChild(summary); // 加入 summary
    const content = document.createElement('pre'); // 创建 pre 展示 chunk 正文
    content.textContent = previewText || '（该 chunk 内容为空）'; // 渲染 chunk 内容并在缺失时提示
    content.style.whiteSpace = 'pre-wrap'; // 允许换行保持原格式
    content.style.wordBreak = 'break-word'; // 长单词自动换行避免溢出
    content.style.marginTop = '8px'; // 与 summary 保持间距
    item.appendChild(content); // 添加内容区域
    list.appendChild(item); // 将详情块加入列表
  });
}

function updateRawContent() { // 根据 chunk 列表拼接原始内容
  if (!rawContainer) return; // 若原始内容容器未准备好则直接返回
  const sorted = [...chunksCache].sort( // 对 chunk 按序号排序以复原原文顺序
    (a, b) => (a.ordinal ?? a.seq ?? 0) - (b.ordinal ?? b.seq ?? 0), // 兼容旧字段命名
  );
  const combined = sorted // 组合排序后的 chunk 文本
    .map((chunk) => chunk.content || '') // 抽取内容，缺失时视为空串
    .filter((text) => text !== '') // 过滤掉空内容避免出现多余空行
    .join('\n\n'); // 使用空行拼接增强可读性
  rawContainer.textContent = combined || '无内容'; // 当存在内容时渲染，否则提示无内容
}

// 设计说明：基于 chunk 列表按需展开与拼接原文，可避免接口重复传输大字段并提升阅读体验。
