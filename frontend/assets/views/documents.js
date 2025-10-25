import { getDocuments, getDomains, createDocument, deleteDocumentByUUID } from '../api.js'; // 导入文档与域相关接口
import { renderTable, renderPagination, toast, confirmDialog, spinner } from '../ui/components.js'; // 引入通用 UI 组件
import { navigate } from '../app.js'; // 引入导航函数

let containerRef = null; // 保存容器引用
let currentLimit = 20; // 当前分页大小
let currentOffset = 0; // 当前偏移量
let currentDomainId = ''; // 当前选中的域过滤
let currentSortBy = 'created_at'; // 当前排序字段
let currentOrder = 'desc'; // 当前排序方向
let domainOptions = []; // 缓存所有域选项

export default { // 导出文档列表视图
  async mount(container, params) { // 挂载逻辑
    containerRef = container; // 保存容器引用
    const query = params?.query || new URLSearchParams(); // 解析查询参数
    currentLimit = Number(query.get('limit') || 20); // 恢复分页大小
    currentOffset = Number(query.get('offset') || 0); // 恢复偏移量
    currentDomainId = query.get('domain_id') || ''; // 恢复域过滤
    currentSortBy = query.get('sort_by') || 'created_at'; // 恢复排序字段
    currentOrder = query.get('order') || 'desc'; // 恢复排序方向
    const title = document.createElement('h1'); // 创建标题元素
    title.textContent = '文档列表'; // 设置标题文本
    container.appendChild(title); // 渲染标题
    const toolbar = document.createElement('div'); // 创建工具栏容器
    toolbar.style.display = 'flex'; // 使用弹性布局
    toolbar.style.flexWrap = 'wrap'; // 允许换行
    toolbar.style.alignItems = 'center'; // 垂直居中
    toolbar.style.gap = '12px'; // 设置控件间距
    toolbar.style.marginBottom = '16px'; // 与列表保持距离
    const domainSelect = document.createElement('select'); // 创建域下拉框
    domainSelect.className = 'input'; // 应用输入样式
    domainSelect.style.maxWidth = '240px'; // 限制宽度
    const sortSelect = document.createElement('select'); // 创建排序字段下拉框
    sortSelect.className = 'input'; // 应用样式
    const orderSelect = document.createElement('select'); // 创建排序方向下拉框
    orderSelect.className = 'input'; // 应用样式
    const limitSelect = document.createElement('select'); // 创建分页大小下拉框
    limitSelect.className = 'input'; // 应用样式
    [10, 20, 50, 100].forEach((size) => { // 初始化分页选项
      const option = document.createElement('option'); // 创建选项
      option.value = String(size); // 设置值
      option.textContent = `${size} 条/页`; // 设置文本
      if (size === currentLimit) option.selected = true; // 默认选中当前值
      limitSelect.appendChild(option); // 添加选项
    });
    const filterBtn = document.createElement('button'); // 创建筛选按钮
    filterBtn.className = 'button'; // 应用主按钮样式
    filterBtn.type = 'button'; // 指定类型
    filterBtn.textContent = '应用筛选'; // 按钮文案
    const createBtn = document.createElement('button'); // 创建文档按钮
    createBtn.className = 'button'; // 主按钮样式
    createBtn.type = 'button'; // 指定类型
    createBtn.textContent = '创建文档'; // 按钮文案
    toolbar.appendChild(domainSelect); // 添加域选择器
    toolbar.appendChild(sortSelect); // 添加排序字段选择器
    toolbar.appendChild(orderSelect); // 添加排序方向选择器
    toolbar.appendChild(limitSelect); // 添加分页大小选择器
    toolbar.appendChild(filterBtn); // 添加筛选按钮
    toolbar.appendChild(createBtn); // 添加创建按钮
    container.appendChild(toolbar); // 渲染工具栏
    const tableWrapper = document.createElement('div'); // 创建表格容器
    tableWrapper.className = 'table-wrapper'; // 应用卡片样式
    container.appendChild(tableWrapper); // 渲染表格容器
    const paginationContainer = document.createElement('div'); // 创建分页容器
    container.appendChild(paginationContainer); // 渲染分页区域
    await loadDomains(domainSelect); // 加载域下拉数据
    populateSortControls(sortSelect, orderSelect); // 初始化排序选项
    domainSelect.value = currentDomainId; // 恢复域选择
    sortSelect.value = currentSortBy; // 恢复排序字段
    orderSelect.value = currentOrder; // 恢复排序方向
    limitSelect.value = String(currentLimit); // 恢复分页大小
    const updateHash = () => { // 同步 URL 查询参数
      const params = new URLSearchParams(); // 创建参数对象
      params.set('limit', String(currentLimit)); // 写入 limit
      params.set('offset', String(currentOffset)); // 写入 offset
      params.set('sort_by', currentSortBy); // 写入排序字段
      params.set('order', currentOrder); // 写入排序方向
      if (currentDomainId) params.set('domain_id', currentDomainId); // 写入域过滤
      navigate(`#/documents?${params.toString()}`); // 更新 hash
    }; // updateHash 结束
    const refresh = async () => { // 定义刷新函数
      tableWrapper.innerHTML = ''; // 清空表格
      paginationContainer.innerHTML = ''; // 清空分页
      const loading = spinner(); // 创建加载指示器
      tableWrapper.appendChild(loading); // 显示加载状态
      try { // 捕获请求错误
        const response = await getDocuments({ // 请求文档列表
          domain_id: currentDomainId || undefined, // 传入域过滤
          limit: currentLimit, // 分页大小
          offset: currentOffset, // 偏移量
          sort_by: currentSortBy, // 排序字段
          order: currentOrder, // 排序方向
        }); // 请求结束
        tableWrapper.innerHTML = ''; // 移除加载状态
        const items = response.items || []; // 获取文档数组
        const total = response.total || items.length; // 解析总数
        const table = renderTable(items, [ // 渲染表格
          { key: 'id', label: 'ID' }, // ID 列
          { key: 'uuid', label: 'UUID' }, // UUID 列
          { key: 'title', label: '标题' }, // 标题列
          { // 域列
            key: 'domain_id', // 对应字段
            label: '所属域', // 列标题
            render: (doc) => { // 自定义渲染
              const domain = domainOptions.find((d) => String(d.id) === String(doc.domain_id)); // 查找域名称
              return domain ? domain.name : '未知'; // 返回名称或未知
            },
          },
          { key: 'created_at', label: '创建时间' }, // 创建时间列
          { // 操作列
            key: 'actions', // 虚拟字段
            label: '操作', // 列标题
            render: (doc) => { // 自定义操作按钮
              const actions = document.createElement('div'); // 创建容器
              actions.className = 'table-actions'; // 应用样式
              const viewBtn = document.createElement('button'); // 查看按钮
              viewBtn.className = 'button button--ghost'; // 次级样式
              viewBtn.type = 'button'; // 指定类型
              viewBtn.textContent = '查看'; // 按钮文案
              viewBtn.addEventListener('click', () => navigate(`#/documents/${doc.uuid}`)); // 跳转详情
              actions.appendChild(viewBtn); // 添加查看按钮
              const deleteBtn = document.createElement('button'); // 删除按钮
              deleteBtn.className = 'button button--ghost'; // 次级样式
              deleteBtn.type = 'button'; // 指定类型
              deleteBtn.textContent = '删除'; // 按钮文案
              deleteBtn.addEventListener('click', () => { // 绑定删除逻辑
                confirmDialog(`确定删除文档 ${doc.title} 吗？`, async () => { // 弹出确认框
                  try { // 捕获异常
                    await deleteDocumentByUUID(doc.uuid); // 调用删除接口
                    toast('文档已删除', 'success'); // 提示成功
                    await refresh(); // 刷新列表
                  } catch (error) { // 捕获错误
                    toast(error.message || '删除失败', 'error'); // 提示失败
                  }
                }); // confirmDialog 结束
              }); // 删除按钮事件结束
              actions.appendChild(deleteBtn); // 添加删除按钮
              return actions; // 返回操作节点
            },
          },
        ]); // 表格渲染结束
        tableWrapper.appendChild(table); // 渲染表格
        const pagination = renderPagination({ // 渲染分页控件
          total, // 总数
          limit: currentLimit, // 分页大小
          offset: currentOffset, // 当前偏移
          onChange: ({ limit, offset }) => { // 分页回调
            currentLimit = limit; // 更新分页大小
            currentOffset = Math.max(0, offset); // 更新偏移量
            updateHash(); // 同步 URL
            refresh(); // 重新加载数据
          },
        }); // 分页渲染结束
        paginationContainer.appendChild(pagination); // 渲染分页控件
      } catch (error) { // 请求失败
        tableWrapper.innerHTML = ''; // 清空表格
        toast(error.message || '加载文档失败', 'error'); // 提示错误
      }
    }; // refresh 结束
    filterBtn.addEventListener('click', () => { // 点击筛选按钮
      currentDomainId = domainSelect.value || ''; // 更新域过滤
      currentSortBy = sortSelect.value; // 更新排序字段
      currentOrder = orderSelect.value; // 更新排序方向
      currentLimit = Number(limitSelect.value); // 更新分页大小
      currentOffset = 0; // 重置偏移
      updateHash(); // 同步 URL
      refresh(); // 刷新数据
    }); // 筛选事件结束
    createBtn.addEventListener('click', () => openCreateDialog(refresh)); // 点击创建弹出对话框
    await refresh(); // 首次加载数据
  }, // mount 结束
  unmount() { // 卸载逻辑
    if (containerRef) containerRef.innerHTML = ''; // 清空容器内容
    containerRef = null; // 释放引用
    domainOptions = []; // 清空域缓存
  }, // unmount 结束
}; // 模块导出结束

async function loadDomains(selectEl) { // 加载全部域
  domainOptions = []; // 重置域缓存
  let offset = 0; // 初始化偏移
  const limit = 50; // 每次加载 50 条
  while (true) { // 循环分页加载
    const response = await getDomains({ limit, offset }); // 请求域列表
    const items = Array.isArray(response) ? response : response.items || []; // 获取数据数组
    domainOptions.push(...items); // 累加到缓存
    if (items.length < limit) break; // 若不足一页则结束
    offset += limit; // 否则继续下一页
  }
  selectEl.innerHTML = ''; // 清空下拉框
  const allOption = document.createElement('option'); // 创建“全部”选项
  allOption.value = ''; // 空值代表不过滤
  allOption.textContent = '全部域'; // 设置文本
  selectEl.appendChild(allOption); // 添加选项
  domainOptions.forEach((domain) => { // 遍历域列表
    const option = document.createElement('option'); // 创建选项
    option.value = String(domain.id); // 设置值
    option.textContent = domain.name; // 显示域名称
    selectEl.appendChild(option); // 添加到下拉框
  });
}

function populateSortControls(sortSelect, orderSelect) { // 初始化排序控件
  sortSelect.innerHTML = ''; // 清空字段下拉
  ['created_at', 'title'].forEach((field) => { // 遍历字段
    const option = document.createElement('option'); // 创建选项
    option.value = field; // 设置值
    option.textContent = field === 'created_at' ? '按创建时间' : '按标题'; // 设置文本
    sortSelect.appendChild(option); // 添加选项
  });
  orderSelect.innerHTML = ''; // 清空方向下拉
  ['asc', 'desc'].forEach((order) => { // 遍历方向
    const option = document.createElement('option'); // 创建选项
    option.value = order; // 设置值
    option.textContent = order === 'asc' ? '升序' : '降序'; // 设置文本
    orderSelect.appendChild(option); // 添加选项
  });
}

function openCreateDialog(refresh) { // 打开创建文档对话框
  const backdrop = document.createElement('div'); // 创建遮罩层
  backdrop.className = 'dialog-backdrop'; // 应用遮罩样式
  const dialog = document.createElement('div'); // 创建对话框
  dialog.className = 'dialog'; // 应用对话框样式
  backdrop.appendChild(dialog); // 将对话框加入遮罩
  const title = document.createElement('h2'); // 创建标题
  title.textContent = '创建文档'; // 设置标题文本
  dialog.appendChild(title); // 渲染标题
  const form = document.createElement('form'); // 创建表单
  form.setAttribute('aria-label', '创建文档表单'); // 设置无障碍描述
  dialog.appendChild(form); // 添加表单
  const domainGroup = document.createElement('div'); // 创建域选择容器
  domainGroup.className = 'form-group'; // 应用样式
  const domainLabel = document.createElement('label'); // 创建标签
  domainLabel.className = 'label'; // 设置样式
  domainLabel.textContent = '所属域'; // 标签文本
  domainLabel.setAttribute('for', 'doc-domain'); // 关联输入
  domainGroup.appendChild(domainLabel); // 添加标签
  const domainSelect = document.createElement('select'); // 创建选择器
  domainSelect.className = 'input'; // 应用输入样式
  domainSelect.id = 'doc-domain'; // 设置 ID
  domainSelect.name = 'domain_id'; // 设置 name
  domainSelect.required = true; // 设置必选
  domainOptions.forEach((domain) => { // 遍历域列表
    const option = document.createElement('option'); // 创建选项
    option.value = String(domain.id); // 设置值
    option.textContent = domain.name; // 显示域名称
    domainSelect.appendChild(option); // 添加选项
  });
  domainGroup.appendChild(domainSelect); // 添加选择器
  form.appendChild(domainGroup); // 渲染容器
  const titleGroup = document.createElement('div'); // 创建标题输入容器
  titleGroup.className = 'form-group'; // 应用样式
  const titleLabel = document.createElement('label'); // 创建标签
  titleLabel.className = 'label'; // 设置样式
  titleLabel.textContent = '标题'; // 标签文本
  titleLabel.setAttribute('for', 'doc-title'); // 关联输入
  titleGroup.appendChild(titleLabel); // 添加标签
  const titleInput = document.createElement('input'); // 创建输入框
  titleInput.className = 'input'; // 应用样式
  titleInput.type = 'text'; // 指定类型
  titleInput.required = true; // 设置必填
  titleInput.id = 'doc-title'; // 设置 ID
  titleInput.name = 'title'; // 设置 name
  titleGroup.appendChild(titleInput); // 添加输入框
  form.appendChild(titleGroup); // 渲染容器
  const modeGroup = document.createElement('div'); // 创建内容模式容器
  modeGroup.className = 'form-group'; // 应用样式
  const modeLabel = document.createElement('label'); // 创建标签
  modeLabel.className = 'label'; // 设置样式
  modeLabel.textContent = '内容模式'; // 标签文本
  modeGroup.appendChild(modeLabel); // 添加标签
  const textOption = document.createElement('label'); // 创建文本模式选项
  textOption.style.display = 'flex'; // 使用弹性布局
  textOption.style.alignItems = 'center'; // 垂直居中
  textOption.style.gap = '8px'; // 设置间距
  const textRadio = document.createElement('input'); // 创建单选按钮
  textRadio.type = 'radio'; // 指定类型
  textRadio.name = 'mode'; // 设置 name
  textRadio.value = 'text'; // 设置值
  textRadio.checked = true; // 默认选中文本模式
  textOption.appendChild(textRadio); // 添加单选按钮
  textOption.appendChild(document.createTextNode('纯文本')); // 添加文本说明
  const jsonOption = document.createElement('label'); // 创建 JSON 模式选项
  jsonOption.style.display = 'flex'; // 使用弹性布局
  jsonOption.style.alignItems = 'center'; // 垂直居中
  jsonOption.style.gap = '8px'; // 设置间距
  const jsonRadio = document.createElement('input'); // 创建单选按钮
  jsonRadio.type = 'radio'; // 指定类型
  jsonRadio.name = 'mode'; // 设置 name
  jsonRadio.value = 'json'; // 设置值
  jsonOption.appendChild(jsonRadio); // 添加单选按钮
  jsonOption.appendChild(document.createTextNode('结构化 JSON')); // 添加文本说明
  modeGroup.appendChild(textOption); // 添加文本选项
  modeGroup.appendChild(jsonOption); // 添加 JSON 选项
  form.appendChild(modeGroup); // 渲染容器
  const contentGroup = document.createElement('div'); // 创建内容输入容器
  contentGroup.className = 'form-group'; // 应用样式
  const contentLabel = document.createElement('label'); // 创建标签
  contentLabel.className = 'label'; // 设置样式
  contentLabel.textContent = '内容'; // 标签文本
  contentLabel.setAttribute('for', 'doc-content'); // 关联输入
  contentGroup.appendChild(contentLabel); // 添加标签
  const contentInput = document.createElement('textarea'); // 创建文本域
  contentInput.className = 'input'; // 应用输入样式
  contentInput.id = 'doc-content'; // 设置 ID
  contentInput.name = 'content'; // 设置 name
  contentInput.required = true; // 设置必填
  contentInput.style.minHeight = '160px'; // 设置高度
  contentGroup.appendChild(contentInput); // 添加文本域
  form.appendChild(contentGroup); // 渲染容器
  const actions = document.createElement('div'); // 创建按钮容器
  actions.className = 'dialog__actions'; // 应用布局样式
  const cancelBtn = document.createElement('button'); // 创建取消按钮
  cancelBtn.className = 'button button--ghost'; // 次级样式
  cancelBtn.type = 'button'; // 指定类型
  cancelBtn.textContent = '取消'; // 按钮文本
  cancelBtn.addEventListener('click', () => backdrop.remove()); // 点击关闭对话框
  actions.appendChild(cancelBtn); // 添加取消按钮
  const submitBtn = document.createElement('button'); // 创建提交按钮
  submitBtn.className = 'button'; // 主按钮样式
  submitBtn.type = 'submit'; // 指定类型
  submitBtn.textContent = '创建'; // 按钮文案
  actions.appendChild(submitBtn); // 添加提交按钮
  form.addEventListener('submit', async (event) => { // 绑定提交事件
    event.preventDefault(); // 阻止默认行为
    submitBtn.disabled = true; // 禁用按钮
    const loading = spinner(); // 创建加载指示器
    submitBtn.appendChild(loading); // 显示加载
    const formData = new FormData(form); // 读取表单数据
    const domain_id = formData.get('domain_id'); // 获取域 ID
    const titleValue = formData.get('title'); // 获取标题
    const mode = formData.get('mode'); // 获取模式
    const contentValue = formData.get('content'); // 获取内容
    try { // 捕获错误
      let payloadContent = contentValue; // 默认使用原始内容
      let metadata = {}; // 初始化元数据
      if (mode === 'json') { // 若选择结构化模式
        try { // 尝试解析 JSON
          JSON.parse(contentValue); // 验证 JSON 格式
          metadata = { type: 'structured' }; // 标记为结构化
        } catch (error) { // 解析失败
          toast('结构化模式需要合法 JSON', 'error'); // 提示错误
          submitBtn.disabled = false; // 恢复按钮
          loading.remove(); // 移除加载
          return; // 中止提交流程
        }
      }
      await createDocument(domain_id, { title: titleValue, content: payloadContent, doc_metadata: metadata }); // 调用创建接口
      toast('文档创建成功', 'success'); // 提示成功
      backdrop.remove(); // 关闭对话框
      if (typeof refresh === 'function') await refresh(); // 刷新列表
    } catch (error) { // 捕获异常
      toast(error.message || '创建失败', 'error'); // 提示错误
    } finally { // 收尾处理
      submitBtn.disabled = false; // 恢复按钮
      loading.remove(); // 移除加载指示器
    }
  }); // 提交事件结束
  form.appendChild(actions); // 渲染按钮容器
  document.body.appendChild(backdrop); // 将对话框挂载到页面
  submitBtn.focus(); // 聚焦提交按钮
}
