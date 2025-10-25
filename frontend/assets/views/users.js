import { getUsers, createUser, updateUser, deleteUser } from '../api.js'; // 导入用户相关接口
import { renderTable, renderPagination, toast, confirmDialog, spinner, badge } from '../ui/components.js'; // 引入 UI 工具集
import { navigate } from '../app.js'; // 引入导航函数

let containerRef = null; // 保存容器引用
let currentQuery = null; // 当前查询参数
let currentLimit = 20; // 当前分页大小
let currentOffset = 0; // 当前偏移量
let currentSearch = ''; // 当前搜索关键词

export default { // 导出用户管理视图
  async mount(container, params) { // 挂载视图
    containerRef = container; // 保存容器
    currentQuery = params?.query || new URLSearchParams(); // 恢复查询参数
    currentLimit = Number(currentQuery.get('limit') || 20); // 解析 limit
    currentOffset = Number(currentQuery.get('offset') || 0); // 解析 offset
    currentSearch = currentQuery.get('q') || ''; // 解析搜索关键词
    const title = document.createElement('h1'); // 创建标题
    title.textContent = '用户管理'; // 设置标题文本
    container.appendChild(title); // 渲染标题
    const toolbar = document.createElement('div'); // 创建工具栏
    toolbar.style.display = 'flex'; // 使用弹性布局
    toolbar.style.flexWrap = 'wrap'; // 支持换行
    toolbar.style.alignItems = 'center'; // 垂直居中
    toolbar.style.gap = '12px'; // 控件间距
    toolbar.style.marginBottom = '16px'; // 与表格拉开距离
    const searchInput = document.createElement('input'); // 创建搜索输入框
    searchInput.className = 'input'; // 应用输入框样式
    searchInput.type = 'search'; // 指定类型
    searchInput.placeholder = '按邮箱或姓名搜索'; // 提示文案
    searchInput.value = currentSearch; // 绑定当前搜索
    searchInput.setAttribute('aria-label', '搜索用户'); // 设置无障碍描述
    toolbar.appendChild(searchInput); // 添加到工具栏
    const searchBtn = document.createElement('button'); // 创建搜索按钮
    searchBtn.className = 'button'; // 主按钮样式
    searchBtn.type = 'button'; // 指定类型
    searchBtn.textContent = '搜索'; // 按钮文本
    toolbar.appendChild(searchBtn); // 添加按钮
    const createBtn = document.createElement('button'); // 创建用户按钮
    createBtn.className = 'button'; // 主按钮样式
    createBtn.type = 'button'; // 指定类型
    createBtn.textContent = '创建用户'; // 按钮文本
    toolbar.appendChild(createBtn); // 添加按钮
    container.appendChild(toolbar); // 渲染工具栏
    const tableWrapper = document.createElement('div'); // 创建表格容器
    tableWrapper.className = 'table-wrapper'; // 应用卡片样式
    container.appendChild(tableWrapper); // 渲染表格容器
    const paginationContainer = document.createElement('div'); // 创建分页容器
    container.appendChild(paginationContainer); // 渲染分页区域
    const refresh = async () => { // 定义刷新函数
      tableWrapper.innerHTML = ''; // 清空表格
      paginationContainer.innerHTML = ''; // 清空分页
      const loading = spinner(); // 创建加载指示器
      tableWrapper.appendChild(loading); // 显示加载
      try { // 捕获请求错误
        const response = await getUsers({ limit: currentLimit, offset: currentOffset, q: currentSearch }); // 请求用户列表
        tableWrapper.innerHTML = ''; // 清空加载状态
        const table = renderTable(response.items || [], [ // 渲染表格
          { key: 'id', label: 'ID' }, // ID 列
          { key: 'email', label: '邮箱' }, // 邮箱列
          { key: 'full_name', label: '姓名' }, // 姓名列
          { // 角色列
            key: 'is_admin', // 使用 is_admin 字段
            label: '角色', // 列标题
            render: (user) => badge(user.is_admin ? 'Admin' : 'User'), // 使用徽章显示角色
          },
          { key: 'created_at', label: '创建时间' }, // 创建时间列
          { // 操作列
            key: 'actions', // 虚拟字段
            label: '操作', // 列标题
            render: (user) => { // 自定义渲染操作按钮
              const actions = document.createElement('div'); // 创建容器
              actions.className = 'table-actions'; // 应用样式
              const editBtn = document.createElement('button'); // 创建编辑按钮
              editBtn.className = 'button button--ghost'; // 次级按钮样式
              editBtn.type = 'button'; // 指定类型
              editBtn.textContent = '编辑'; // 按钮文本
              editBtn.addEventListener('click', () => openForm('edit', user, refresh)); // 绑定编辑对话框
              actions.appendChild(editBtn); // 添加编辑按钮
              const deleteBtn = document.createElement('button'); // 创建删除按钮
              deleteBtn.className = 'button button--ghost'; // 次级样式
              deleteBtn.type = 'button'; // 指定类型
              deleteBtn.textContent = '删除'; // 按钮文本
              deleteBtn.addEventListener('click', () => { // 绑定删除逻辑
                confirmDialog(`确定删除用户 ${user.email} 吗？`, async () => { // 弹出确认框
                  try { // 捕获删除错误
                    await deleteUser(user.id); // 调用删除接口
                    toast('用户已删除', 'success'); // 提示成功
                    refresh(); // 刷新列表
                  } catch (error) { // 捕获错误
                    toast(error.message || '删除失败', 'error'); // 提示失败
                  }
                }); // confirmDialog 结束
              }); // 删除按钮监听结束
              actions.appendChild(deleteBtn); // 添加删除按钮
              return actions; // 返回操作节点
            },
          },
        ]); // renderTable 结束
        tableWrapper.appendChild(table); // 渲染表格
        const pagination = renderPagination({ // 渲染分页控件
          total: response.total || 0, // 总数
          limit: currentLimit, // 当前分页大小
          offset: currentOffset, // 当前偏移
          onChange: ({ limit, offset }) => { // 分页回调
            currentLimit = limit; // 更新分页大小
            currentOffset = Math.max(0, offset); // 更新偏移量
            updateHash(); // 同步 URL
            refresh(); // 重新加载
          },
        }); // renderPagination 结束
        paginationContainer.appendChild(pagination); // 渲染分页控件
      } catch (error) { // 请求失败
        tableWrapper.innerHTML = ''; // 清空内容
        toast(error.message || '加载用户列表失败', 'error'); // 提示错误
      }
    }; // refresh 定义结束
    const updateHash = () => { // 同步 URL 查询参数
      const params = new URLSearchParams(); // 新建参数对象
      params.set('limit', String(currentLimit)); // 写入 limit
      params.set('offset', String(currentOffset)); // 写入 offset
      if (currentSearch) { // 若存在搜索关键词
        params.set('q', currentSearch); // 写入 q
      }
      navigate(`#/users?${params.toString()}`); // 更新 hash
    }; // updateHash 结束
    searchBtn.addEventListener('click', () => { // 点击搜索按钮
      currentSearch = searchInput.value.trim(); // 更新搜索关键词
      currentOffset = 0; // 重置偏移
      updateHash(); // 同步 URL
      refresh(); // 刷新列表
    }); // 搜索按钮事件结束
    searchInput.addEventListener('keydown', (event) => { // 输入框键盘事件
      if (event.key === 'Enter') { // 按下回车
        event.preventDefault(); // 阻止默认提交
        searchBtn.click(); // 触发搜索
      }
    }); // 键盘事件结束
    createBtn.addEventListener('click', () => openForm('create', null, refresh)); // 点击创建按钮弹出对话框
    await refresh(); // 首次加载数据
  }, // mount 结束
  unmount() { // 卸载逻辑
    if (containerRef) { // 若存在容器
      containerRef.innerHTML = ''; // 清空内容
    }
    containerRef = null; // 释放容器引用
  }, // unmount 结束
}; // 模块导出结束

function openForm(mode, user, refresh) { // 打开创建或编辑对话框
  const backdrop = document.createElement('div'); // 创建遮罩层
  backdrop.className = 'dialog-backdrop'; // 应用遮罩样式
  const dialog = document.createElement('div'); // 创建对话框
  dialog.className = 'dialog'; // 应用样式
  backdrop.appendChild(dialog); // 将面板加入遮罩
  const title = document.createElement('h2'); // 创建标题
  title.textContent = mode === 'create' ? '创建用户' : `编辑 ${user.email}`; // 设置标题文本
  dialog.appendChild(title); // 添加标题
  const form = document.createElement('form'); // 创建表单
  form.setAttribute('aria-label', '用户表单'); // 设置无障碍描述
  dialog.appendChild(form); // 添加表单
  const emailGroup = document.createElement('div'); // 邮箱容器
  emailGroup.className = 'form-group'; // 应用样式
  if (mode === 'create') { // 创建模式显示输入框
    const emailLabel = document.createElement('label'); // 创建标签
    emailLabel.className = 'label'; // 应用样式
    emailLabel.textContent = '邮箱'; // 标签文本
    emailLabel.setAttribute('for', 'user-email'); // 关联输入框
    emailGroup.appendChild(emailLabel); // 添加标签
    const emailInput = document.createElement('input'); // 创建输入框
    emailInput.className = 'input'; // 应用样式
    emailInput.type = 'email'; // 指定类型
    emailInput.required = true; // 必填
    emailInput.id = 'user-email'; // 设置 ID
    emailInput.name = 'email'; // 设置 name
    emailGroup.appendChild(emailInput); // 添加输入框
  } else { // 编辑模式显示只读信息
    const info = document.createElement('p'); // 创建文本
    info.textContent = `邮箱：${user.email}`; // 显示邮箱
    emailGroup.appendChild(info); // 添加文本
  }
  form.appendChild(emailGroup); // 将邮箱容器加入表单
  const nameGroup = document.createElement('div'); // 姓名容器
  nameGroup.className = 'form-group'; // 应用样式
  const nameLabel = document.createElement('label'); // 姓名标签
  nameLabel.className = 'label'; // 设置样式
  nameLabel.textContent = '姓名'; // 标签文本
  nameLabel.setAttribute('for', 'user-full-name'); // 关联输入框
  nameGroup.appendChild(nameLabel); // 添加标签
  const nameInput = document.createElement('input'); // 创建输入框
  nameInput.className = 'input'; // 应用样式
  nameInput.type = 'text'; // 指定类型
  nameInput.id = 'user-full-name'; // 设置 ID
  nameInput.name = 'full_name'; // 设置 name
  nameInput.value = user?.full_name || ''; // 填入已有值
  nameGroup.appendChild(nameInput); // 添加输入框
  form.appendChild(nameGroup); // 将姓名容器加入表单
  const passwordGroup = document.createElement('div'); // 密码容器
  passwordGroup.className = 'form-group'; // 应用样式
  const passwordLabel = document.createElement('label'); // 密码标签
  passwordLabel.className = 'label'; // 设置样式
  passwordLabel.textContent = mode === 'create' ? '初始密码' : '新密码（留空不修改）'; // 根据模式设置文本
  passwordLabel.setAttribute('for', 'user-password'); // 关联输入框
  passwordGroup.appendChild(passwordLabel); // 添加标签
  const passwordInput = document.createElement('input'); // 创建输入框
  passwordInput.className = 'input'; // 应用样式
  passwordInput.type = 'password'; // 指定类型
  passwordInput.minLength = 8; // 设置最小长度
  passwordInput.id = 'user-password'; // 设置 ID
  passwordInput.name = 'password'; // 设置 name
  if (mode === 'create') { // 创建模式必填
    passwordInput.required = true; // 设置必填
  }
  passwordGroup.appendChild(passwordInput); // 添加输入框
  form.appendChild(passwordGroup); // 将密码容器加入表单
  const adminGroup = document.createElement('div'); // 管理员开关容器
  adminGroup.className = 'form-group'; // 应用样式
  const adminLabel = document.createElement('label'); // 标签
  adminLabel.className = 'label'; // 设置样式
  adminLabel.textContent = '是否管理员'; // 标签文本
  adminLabel.setAttribute('for', 'user-is-admin'); // 关联输入
  adminGroup.appendChild(adminLabel); // 添加标签
  const adminInput = document.createElement('input'); // 创建复选框
  adminInput.type = 'checkbox'; // 指定类型
  adminInput.id = 'user-is-admin'; // 设置 ID
  adminInput.name = 'is_admin'; // 设置 name
  adminInput.checked = Boolean(user?.is_admin); // 根据原值勾选
  adminGroup.appendChild(adminInput); // 添加复选框
  form.appendChild(adminGroup); // 将容器加入表单
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
  form.addEventListener('submit', async (event) => { // 提交事件
    event.preventDefault(); // 阻止默认行为
    submitBtn.disabled = true; // 禁用按钮
    const loading = spinner(); // 创建加载指示器
    submitBtn.appendChild(loading); // 显示加载
    const formData = new FormData(form); // 读取表单数据
    const payload = { // 构造请求体
      full_name: formData.get('full_name') || null, // 姓名字段
      password: formData.get('password') || undefined, // 密码字段
      is_admin: formData.get('is_admin') === 'on', // 管理员标记
    }; // payload 构造结束
    try { // 捕获错误
      if (mode === 'create') { // 创建模式
        await createUser({ // 调用创建接口
          email: formData.get('email'), // 邮箱
          password: formData.get('password'), // 密码
          full_name: payload.full_name, // 姓名
          is_admin: payload.is_admin, // 管理员标记
        }); // createUser 结束
        toast('用户创建成功', 'success'); // 提示成功
      } else { // 编辑模式
        await updateUser(user.id, payload); // 调用更新接口
        toast('用户信息已更新', 'success'); // 提示成功
      }
      backdrop.remove(); // 关闭对话框
      if (typeof refresh === 'function') { // 若存在刷新回调
        refresh(); // 重新加载列表
      }
    } catch (error) { // 捕获异常
      toast(error.message || '保存失败，请检查输入', 'error'); // 提示错误
    } finally { // 收尾处理
      submitBtn.disabled = false; // 恢复按钮
      loading.remove(); // 移除加载动画
    }
  }); // 提交事件结束
  form.appendChild(actions); // 将操作按钮放入表单内部以保证提交生效
  document.body.appendChild(backdrop); // 将对话框挂载到页面
  submitBtn.focus(); // 自动聚焦提交按钮
}
