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
  const modeOptions = document.createElement('div'); // 创建模式切换区域
  modeOptions.className = 'form-toggle'; // 应用样式
  const textOption = document.createElement('label'); // 文本模式选项
  textOption.className = 'form-toggle__option form-toggle__option--active';
  textOption.setAttribute('data-mode', 'text');
  const textRadio = document.createElement('input'); // 文本模式单选
  textRadio.type = 'radio';
  textRadio.name = 'mode';
  textRadio.value = 'text';
  textRadio.checked = true;
  const textOptionContent = document.createElement('div'); // 文本模式说明
  textOptionContent.className = 'form-toggle__content';
  const textOptionTitle = document.createElement('div');
  textOptionTitle.className = 'form-toggle__title';
  textOptionTitle.textContent = '纯文本';
  const textOptionDesc = document.createElement('div');
  textOptionDesc.className = 'form-toggle__description';
  textOptionDesc.textContent = '直接粘贴或输入纯文本内容，系统将按滑动窗口拆分。';
  textOptionContent.appendChild(textOptionTitle);
  textOptionContent.appendChild(textOptionDesc);
  textOption.appendChild(textRadio);
  textOption.appendChild(textOptionContent);
  const csvOption = document.createElement('label'); // CSV 模式选项
  csvOption.className = 'form-toggle__option';
  csvOption.setAttribute('data-mode', 'csv');
  const csvRadio = document.createElement('input'); // CSV 单选按钮
  csvRadio.type = 'radio';
  csvRadio.name = 'mode';
  csvRadio.value = 'csv';
  const csvOptionContent = document.createElement('div');
  csvOptionContent.className = 'form-toggle__content';
  const csvOptionTitle = document.createElement('div');
  csvOptionTitle.className = 'form-toggle__title';
  csvOptionTitle.textContent = 'CSV 上传';
  const csvOptionDesc = document.createElement('div');
  csvOptionDesc.className = 'form-toggle__description';
  csvOptionDesc.textContent = '上传结构化 CSV，我们会解析实体并按 key-value 自动分段。';
  csvOptionContent.appendChild(csvOptionTitle);
  csvOptionContent.appendChild(csvOptionDesc);
  csvOption.appendChild(csvRadio);
  csvOption.appendChild(csvOptionContent);
  modeOptions.appendChild(textOption);
  modeOptions.appendChild(csvOption);
  modeGroup.appendChild(modeOptions);
  form.appendChild(modeGroup); // 渲染模式切换
  const contentGroup = document.createElement('div'); // 创建内容输入容器
  contentGroup.className = 'form-group'; // 应用样式
  const contentLabel = document.createElement('label'); // 创建标签
  contentLabel.className = 'label'; // 设置样式
  contentLabel.textContent = '内容'; // 标签文本
  contentLabel.setAttribute('for', 'doc-content'); // 关联输入
  contentGroup.appendChild(contentLabel); // 添加标签
  const textPane = document.createElement('div'); // 文本模式容器
  textPane.className = 'content-pane content-pane--active';
  const contentInput = document.createElement('textarea'); // 创建文本域
  contentInput.className = 'input'; // 应用输入样式
  contentInput.id = 'doc-content'; // 设置 ID
  contentInput.name = 'content'; // 设置 name
  contentInput.required = true; // 默认文本必填
  contentInput.style.minHeight = '160px'; // 设置高度
  textPane.appendChild(contentInput); // 添加文本域
  const textHint = document.createElement('p'); // 文本模式提示
  textHint.className = 'form-hint';
  textHint.textContent = '系统会使用 250 字符窗口并重叠 50 字符自动拆分文本。';
  textPane.appendChild(textHint);
  const csvPane = document.createElement('div'); // CSV 模式容器
  csvPane.className = 'content-pane';
  const fileInput = document.createElement('input'); // 创建文件选择器
  fileInput.type = 'file';
  fileInput.accept = '.csv,text/csv';
  fileInput.name = 'file';
  fileInput.id = 'doc-file';
  fileInput.style.display = 'none';
  const uploadLabel = document.createElement('label'); // 上传区域
  uploadLabel.className = 'upload-dropzone';
  uploadLabel.setAttribute('for', 'doc-file');
  uploadLabel.setAttribute('role', 'button');
  uploadLabel.tabIndex = 0;
  const uploadTitle = document.createElement('strong');
  uploadTitle.textContent = '选择或拖拽 CSV 文件';
  const uploadHint = document.createElement('span');
  uploadHint.className = 'upload-dropzone__hint';
  uploadHint.textContent = '仅支持 UTF-8 编码 CSV，首行作为表头。';
  uploadLabel.appendChild(uploadTitle);
  uploadLabel.appendChild(uploadHint);
  const fileNameDisplay = document.createElement('span');
  fileNameDisplay.className = 'upload-filename';
  fileNameDisplay.textContent = '尚未选择文件';
  const csvHint = document.createElement('p');
  csvHint.className = 'form-hint';
  csvHint.textContent = '我们会将每一行解析为 entity:key:value 形式，单段最长 250 字符。';
  csvPane.appendChild(fileInput);
  csvPane.appendChild(uploadLabel);
  csvPane.appendChild(fileNameDisplay);
  csvPane.appendChild(csvHint);
  contentGroup.appendChild(textPane);
  contentGroup.appendChild(csvPane);
  form.appendChild(contentGroup); // 渲染内容区域
  const processingNotice = document.createElement('div'); // 处理中提示
  processingNotice.className = 'form-processing';
  const processingSpinner = spinner();
  processingNotice.appendChild(processingSpinner);
  const processingText = document.createElement('span');
  processingText.textContent = '处理中，请稍候…';
  processingNotice.appendChild(processingText);
  form.appendChild(processingNotice);
  let currentMode = 'text'; // 记录当前模式
  const updateFileName = (file) => { // 更新已选文件名
    if (file) {
      fileNameDisplay.textContent = file.name;
      fileNameDisplay.classList.add('upload-filename--active');
    } else {
      fileNameDisplay.textContent = '尚未选择文件';
      fileNameDisplay.classList.remove('upload-filename--active');
    }
  };
  const setMode = (mode) => { // 切换模式
    currentMode = mode;
    const isCsv = mode === 'csv';
    textRadio.checked = !isCsv;
    csvRadio.checked = isCsv;
    if (isCsv) {
      textOption.classList.remove('form-toggle__option--active');
      csvOption.classList.add('form-toggle__option--active');
      textPane.classList.remove('content-pane--active');
      csvPane.classList.add('content-pane--active');
      contentInput.required = false;
      fileInput.required = true;
    } else {
      csvOption.classList.remove('form-toggle__option--active');
      textOption.classList.add('form-toggle__option--active');
      csvPane.classList.remove('content-pane--active');
      textPane.classList.add('content-pane--active');
      fileInput.required = false;
      contentInput.required = true;
    }
  };
  textRadio.addEventListener('change', () => {
    if (textRadio.checked) setMode('text');
  });
  csvRadio.addEventListener('change', () => {
    if (csvRadio.checked) setMode('csv');
  });
  uploadLabel.addEventListener('keydown', (event) => { // 键盘支持
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      fileInput.click();
    }
  });
  uploadLabel.addEventListener('dragover', (event) => { // 拖拽状态
    event.preventDefault();
    uploadLabel.classList.add('upload-dropzone--dragover');
  });
  uploadLabel.addEventListener('dragleave', () => {
    uploadLabel.classList.remove('upload-dropzone--dragover');
  });
  uploadLabel.addEventListener('drop', (event) => { // 支持拖拽上传
    event.preventDefault();
    uploadLabel.classList.remove('upload-dropzone--dragover');
    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (typeof DataTransfer !== 'undefined') {
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        fileInput.files = dataTransfer.files;
      } else {
        try {
          fileInput.files = files;
        } catch (err) {
          // 某些浏览器不允许直接赋值，忽略错误并保持原状
        }
      }
      fileInput.dispatchEvent(new Event('change', { bubbles: true }));
    }
  });
  fileInput.addEventListener('change', () => { // 文件选择回调
    const file = fileInput.files && fileInput.files[0];
    updateFileName(file);
  });
  setMode('text'); // 初始化文本模式
  const toggleInputsDisabled = (disabled) => { // 批量禁用输入
    [domainSelect, titleInput, textRadio, csvRadio, contentInput, fileInput].forEach((el) => {
      if (el) el.disabled = disabled;
    });
  };
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
    const formData = new FormData(form); // 读取表单数据
    const domain_id = formData.get('domain_id'); // 获取域 ID
    const titleValue = (formData.get('title') || '').toString().trim(); // 标题
    const contentValue = (contentInput.value || '').toString(); // 文本内容
    const selectedFile = fileInput.files && fileInput.files[0]; // 文件
    if (!domain_id) {
      toast('请选择所属域', 'error');
      return;
    }
    if (!titleValue) {
      toast('请输入标题', 'error');
      return;
    }
    submitBtn.disabled = true; // 禁用提交
    cancelBtn.disabled = true; // 禁用取消
    toggleInputsDisabled(true); // 禁用输入控件
    if (processingNotice) {
      processingNotice.classList.add('form-processing--active');
    }
    try {
      const payload = new FormData(); // 准备提交载荷
      payload.append('title', titleValue); // 写入标题
      payload.append('mode', currentMode || 'text'); // 写入模式
      if (currentMode === 'csv') {
        if (!selectedFile) {
          toast('请选择 CSV 文件', 'error');
          return;
        }
        payload.append('file', selectedFile);
      } else {
        if (!contentValue.trim()) {
          toast('请输入文档内容', 'error');
          return;
        }
        payload.append('content', contentValue);
      }
      await createDocument(domain_id, payload); // 调用创建接口
      toast('文档创建成功', 'success'); // 提示成功
      backdrop.remove(); // 关闭对话框
      if (typeof refresh === 'function') await refresh(); // 刷新列表
    } catch (error) { // 捕获异常
      toast(error.message || '创建失败', 'error'); // 提示错误
    } finally {
      if (processingNotice && processingNotice.classList.contains('form-processing--active')) {
        processingNotice.classList.remove('form-processing--active');
      }
      if (form.isConnected) {
        submitBtn.disabled = false;
        cancelBtn.disabled = false;
        toggleInputsDisabled(false);
        setMode(currentMode);
      }
    }
  }); // 提交事件结束
  form.appendChild(actions); // 渲染按钮容器
  document.body.appendChild(backdrop); // 将对话框挂载到页面
  submitBtn.focus(); // 聚焦提交按钮
}
