import { getDomains, createDomain, updateDomain, deleteDomain } from '../api.js'; // 导入域相关接口
import { renderTable, renderPagination, toast, confirmDialog, spinner } from '../ui/components.js'; // 引入 UI 工具
import { navigate } from '../app.js'; // 引入导航函数

let containerRef = null; // 保存容器引用
let currentLimit = 20; // 当前分页大小
let currentOffset = 0; // 当前偏移量

export default { // 导出域管理视图
  async mount(container, params) { // 挂载逻辑
    containerRef = container; // 保存容器
    const query = params?.query || new URLSearchParams(); // 解析查询参数
    currentLimit = Number(query.get('limit') || 20); // 恢复 limit
    currentOffset = Number(query.get('offset') || 0); // 恢复 offset
    const title = document.createElement('h1'); // 创建标题
    title.textContent = '域管理'; // 设置标题文本
    container.appendChild(title); // 渲染标题
    const toolbar = document.createElement('div'); // 创建工具栏
    toolbar.style.display = 'flex'; // 使用弹性布局
    toolbar.style.gap = '12px'; // 设置间距
    toolbar.style.marginBottom = '16px'; // 与表格保持距离
    const createBtn = document.createElement('button'); // 创建按钮
    createBtn.className = 'button'; // 应用主按钮样式
    createBtn.type = 'button'; // 指定类型
    createBtn.textContent = '创建域'; // 按钮文案
    toolbar.appendChild(createBtn); // 添加按钮
    container.appendChild(toolbar); // 渲染工具栏
    const tableWrapper = document.createElement('div'); // 创建表格容器
    tableWrapper.className = 'table-wrapper'; // 应用卡片样式
    container.appendChild(tableWrapper); // 渲染表格容器
    const paginationContainer = document.createElement('div'); // 创建分页容器
    container.appendChild(paginationContainer); // 渲染分页
    const refresh = async () => { // 定义刷新函数
      tableWrapper.innerHTML = ''; // 清空表格
      paginationContainer.innerHTML = ''; // 清空分页
      const loading = spinner(); // 创建加载指示器
      tableWrapper.appendChild(loading); // 显示加载
      try { // 捕获请求错误
        const response = await getDomains({ limit: currentLimit, offset: currentOffset }); // 请求域列表
        tableWrapper.innerHTML = ''; // 清空加载状态
        const items = Array.isArray(response) ? response : response.items || []; // 兼容不同返回格式
        const total = Array.isArray(response) ? items.length : response.total || items.length; // 推算总数
        const table = renderTable(items, [ // 渲染表格
          { key: 'id', label: 'ID' }, // ID 列
          { key: 'name', label: '名称' }, // 名称列
          { key: 'description', label: '描述' }, // 描述列
          { key: 'created_at', label: '创建时间' }, // 创建时间列
          { // 操作列
            key: 'actions', // 虚拟字段
            label: '操作', // 列标题
            render: (domain) => { // 自定义渲染操作按钮
              const actions = document.createElement('div'); // 创建容器
              actions.className = 'table-actions'; // 应用样式
              const editBtn = document.createElement('button'); // 编辑按钮
              editBtn.className = 'button button--ghost'; // 次级样式
              editBtn.type = 'button'; // 指定类型
              editBtn.textContent = '编辑'; // 按钮文本
              editBtn.addEventListener('click', () => openForm(domain, refresh)); // 打开编辑对话框
              actions.appendChild(editBtn); // 添加按钮
              const deleteBtn = document.createElement('button'); // 删除按钮
              deleteBtn.className = 'button button--ghost'; // 次级样式
              deleteBtn.type = 'button'; // 指定类型
              deleteBtn.textContent = '删除'; // 按钮文本
              deleteBtn.addEventListener('click', () => { // 绑定删除逻辑
                confirmDialog(`确定删除域 ${domain.name} 吗？`, async () => { // 弹出确认框
                  try { // 捕获异常
                    await deleteDomain(domain.id); // 调用删除接口
                    toast('已删除域', 'success'); // 提示成功
                    await refresh(); // 刷新列表
                  } catch (error) { // 捕获错误
                    toast(error.message || '删除失败', 'error'); // 提示错误
                  }
                }); // confirmDialog 结束
              }); // 删除按钮监听结束
              actions.appendChild(deleteBtn); // 添加删除按钮
              return actions; // 返回操作容器
            },
          },
        ]); // 表格渲染完成
        tableWrapper.appendChild(table); // 渲染表格
        const pagination = renderPagination({ // 渲染分页控件
          total, // 总数
          limit: currentLimit, // 分页大小
          offset: currentOffset, // 当前偏移
          onChange: ({ limit, offset }) => { // 分页回调
            currentLimit = limit; // 更新分页大小
            currentOffset = Math.max(0, offset); // 更新偏移量
            updateHash(); // 同步 URL
            refresh(); // 重新加载
          },
        }); // 分页渲染结束
        paginationContainer.appendChild(pagination); // 添加分页控件
      } catch (error) { // 请求失败
        tableWrapper.innerHTML = ''; // 清空内容
        toast(error.message || '加载域列表失败', 'error'); // 提示错误
      }
    }; // refresh 结束
    const updateHash = () => { // 同步 URL 查询参数
      const params = new URLSearchParams(); // 创建参数对象
      params.set('limit', String(currentLimit)); // 写入 limit
      params.set('offset', String(currentOffset)); // 写入 offset
      navigate(`#/domains?${params.toString()}`); // 更新 hash
    }; // updateHash 结束
    createBtn.addEventListener('click', () => openForm(null, refresh)); // 点击按钮打开创建对话框
    await refresh(); // 首次加载数据
  }, // mount 结束
  unmount() { // 卸载逻辑
    if (containerRef) { // 若存在容器
      containerRef.innerHTML = ''; // 清空内容
    }
    containerRef = null; // 释放引用
  }, // unmount 结束
}; // 模块导出结束

function openForm(domain, refresh) { // 打开创建或编辑对话框
  const backdrop = document.createElement('div'); // 创建遮罩层
  backdrop.className = 'dialog-backdrop'; // 应用遮罩样式
  const dialog = document.createElement('div'); // 创建对话框
  dialog.className = 'dialog'; // 应用样式
  backdrop.appendChild(dialog); // 将面板加入遮罩
  const title = document.createElement('h2'); // 创建标题
  title.textContent = domain ? `编辑 ${domain.name}` : '创建域'; // 设置标题文本
  dialog.appendChild(title); // 渲染标题
  const form = document.createElement('form'); // 创建表单
  form.setAttribute('aria-label', '域表单'); // 设置无障碍描述
  dialog.appendChild(form); // 添加表单
  const nameGroup = document.createElement('div'); // 名称容器
  nameGroup.className = 'form-group'; // 应用样式
  const nameLabel = document.createElement('label'); // 名称标签
  nameLabel.className = 'label'; // 设置样式
  nameLabel.textContent = '名称'; // 标签文本
  nameLabel.setAttribute('for', 'domain-name'); // 关联输入
  nameGroup.appendChild(nameLabel); // 添加标签
  const nameInput = document.createElement('input'); // 创建输入框
  nameInput.className = 'input'; // 应用样式
  nameInput.type = 'text'; // 指定类型
  nameInput.required = true; // 设置必填
  nameInput.id = 'domain-name'; // 设置 ID
  nameInput.name = 'name'; // 设置 name
  nameInput.value = domain?.name || ''; // 填入已有值
  nameGroup.appendChild(nameInput); // 添加输入框
  form.appendChild(nameGroup); // 将容器加入表单
  const descGroup = document.createElement('div'); // 描述容器
  descGroup.className = 'form-group'; // 应用样式
  const descLabel = document.createElement('label'); // 描述标签
  descLabel.className = 'label'; // 设置样式
  descLabel.textContent = '描述'; // 标签文本
  descLabel.setAttribute('for', 'domain-desc'); // 关联输入
  descGroup.appendChild(descLabel); // 添加标签
  const descInput = document.createElement('textarea'); // 创建文本域
  descInput.className = 'input'; // 应用输入样式
  descInput.style.minHeight = '120px'; // 设置高度
  descInput.id = 'domain-desc'; // 设置 ID
  descInput.name = 'description'; // 设置 name
  descInput.value = domain?.description || ''; // 填入已有值
  descGroup.appendChild(descInput); // 添加文本域
  form.appendChild(descGroup); // 将容器加入表单
  const actions = document.createElement('div'); // 操作按钮容器
  actions.className = 'dialog__actions'; // 应用布局样式
  const cancelBtn = document.createElement('button'); // 取消按钮
  cancelBtn.className = 'button button--ghost'; // 次级样式
  cancelBtn.type = 'button'; // 指定类型
  cancelBtn.textContent = '取消'; // 按钮文本
  cancelBtn.addEventListener('click', () => backdrop.remove()); // 点击关闭对话框
  actions.appendChild(cancelBtn); // 添加按钮
  const submitBtn = document.createElement('button'); // 提交按钮
  submitBtn.className = 'button'; // 主按钮样式
  submitBtn.type = 'submit'; // 指定类型
  submitBtn.textContent = '保存'; // 按钮文本
  actions.appendChild(submitBtn); // 添加按钮
  form.addEventListener('submit', async (event) => { // 表单提交事件
    event.preventDefault(); // 阻止默认行为
    submitBtn.disabled = true; // 禁用按钮
    const loading = spinner(); // 创建加载指示器
    submitBtn.appendChild(loading); // 显示加载
    const formData = new FormData(form); // 读取表单数据
    const payload = { // 构造请求体
      name: formData.get('name'), // 域名称
      description: formData.get('description') || null, // 描述
    }; // 请求体构建完成
    try { // 捕获错误
      if (domain) { // 编辑模式
        await updateDomain(domain.id, payload); // 调用更新接口
        toast('域已更新', 'success'); // 提示成功
      } else { // 创建模式
        await createDomain(payload); // 调用创建接口
        toast('域已创建', 'success'); // 提示成功
      }
      backdrop.remove(); // 关闭对话框
      if (typeof refresh === 'function') { // 若存在刷新回调
        await refresh(); // 刷新列表
      }
    } catch (error) { // 捕获异常
      toast(error.message || '保存失败', 'error'); // 提示错误
    } finally { // 收尾处理
      submitBtn.disabled = false; // 恢复按钮
      loading.remove(); // 移除加载动画
    }
  }); // 提交事件结束
  form.appendChild(actions); // 将操作区域添加到表单内，确保提交按钮触发表单提交
  document.body.appendChild(backdrop); // 将对话框挂载到页面
  submitBtn.focus(); // 自动聚焦提交按钮
}
