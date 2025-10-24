import { authMe } from './api.js'; // 导入认证接口用于获取当前用户
import { toast, badge } from './ui/components.js'; // 引入通用提示与徽章组件
import LoginView from './views/login.js'; // 登录视图模块
import RegisterView from './views/register.js'; // 注册视图模块
import DashboardView from './views/dashboard.js'; // 仪表盘视图模块
import UsersView from './views/users.js'; // 用户管理视图模块
import DomainsView from './views/domains.js'; // 域管理视图模块
import DocumentsView from './views/documents.js'; // 文档列表视图模块
import DocumentDetailView from './views/document_detail.js'; // 文档详情视图模块
import ChatsView from './views/chats.js'; // 聊天视图模块
import NotFoundView from './views/notfound.js'; // 404 兜底视图模块

const state = { // 全局状态集中管理 token 与用户信息
  authToken: window.localStorage.getItem('access_token'), // 从本地存储恢复 token
  currentUser: null, // 当前用户信息缓存
  activeView: null, // 当前激活的视图对象
  currentRoute: null, // 当前匹配的路由信息
};

const menuItems = [ // 侧边栏菜单配置
  { hash: '#/dashboard', label: '仪表盘', requiresAuth: true }, // 仪表盘仅登录可见
  { hash: '#/documents', label: '文档列表', requiresAuth: true }, // 文档列表需要登录
  { hash: '#/domains', label: '域管理', requiresAuth: true }, // 域管理需要登录
  { hash: '#/chats', label: '聊天记录', requiresAuth: true }, // 聊天记录需要登录
  { hash: '#/users', label: '用户管理', requiresAdmin: true }, // 用户管理仅管理员可见
];

const routes = [ // 路由表定义
  { pattern: '#/login', view: LoginView, title: '登录', requiresAuth: false }, // 登录页面无需鉴权
  { pattern: '#/register', view: RegisterView, title: '注册', requiresAuth: false }, // 注册页面无需鉴权
  { pattern: '#/dashboard', view: DashboardView, title: '仪表盘', requiresAuth: true }, // 仪表盘需要鉴权
  { pattern: '#/users', view: UsersView, title: '用户管理', requiresAuth: true, requiresAdmin: true }, // 用户管理要求管理员
  { pattern: '#/domains', view: DomainsView, title: '域管理', requiresAuth: true }, // 域管理需要鉴权
  { pattern: '#/documents', view: DocumentsView, title: '文档列表', requiresAuth: true }, // 文档列表需要鉴权
  { pattern: '#/documents/:uuid', view: DocumentDetailView, title: '文档详情', requiresAuth: true }, // 文档详情需要鉴权
  { pattern: '#/chats', view: ChatsView, title: '聊天记录', requiresAuth: true }, // 聊天记录需要鉴权
];

const fallbackRoute = { pattern: '#/404', view: NotFoundView, title: '未找到页面', requiresAuth: true }; // 未匹配时使用的默认路由

export function setToken(token) { // 更新 token 并持久化
  state.authToken = token; // 写入内存状态
  if (token) { // 存在 token 时
    window.localStorage.setItem('access_token', token); // 同步到 localStorage
  } else { // 无 token 时
    window.localStorage.removeItem('access_token'); // 清除存储
  }
}

export function clearToken() { // 清理 token 和用户信息
  state.authToken = null; // 清空内存 token
  state.currentUser = null; // 清空用户信息
  window.localStorage.removeItem('access_token'); // 移除本地存储 token
}

export function getCurrentUser() { // 暴露当前用户信息
  return state.currentUser; // 返回缓存对象
}

export function setCurrentUser(user) { // 更新当前用户
  state.currentUser = user; // 写入状态
  renderTopbar(); // 重绘顶部栏
  renderSidebar(); // 重绘侧边栏
}

export function requireAuth() { // 判断是否已登录
  return Boolean(state.authToken); // 根据 token 是否存在判断
}

export function navigate(hash) { // 导航到指定路由
  window.location.hash = hash; // 直接修改 hash 值
}

function parseHash(rawHash) { // 解析 hash 得到路径与查询参数
  const hash = rawHash || '#/login'; // 若为空则默认跳到登录
  const [path, queryString] = hash.split('?'); // 拆分路径与查询字符串
  const query = new URLSearchParams(queryString || ''); // 将查询字符串转为对象
  return { path, query }; // 返回解析结果
}

function matchRoute(path) { // 根据路径匹配路由表
  for (const route of routes) { // 遍历所有路由配置
    const patternSegments = route.pattern.split('/'); // 解析模式片段
    const pathSegments = path.split('/'); // 解析实际路径片段
    if (patternSegments.length !== pathSegments.length) { // 长度不同直接跳过
      continue; // 继续下一个配置
    }
    const params = {}; // 初始化参数对象
    let matched = true; // 默认匹配成功
    for (let i = 0; i < patternSegments.length; i += 1) { // 遍历每个片段
      const patternPart = patternSegments[i]; // 获取模式段
      const pathPart = pathSegments[i]; // 获取路径段
      if (patternPart.startsWith(':')) { // 处理动态参数
        params[patternPart.slice(1)] = pathPart; // 记录参数值
      } else if (patternPart !== pathPart) { // 静态段不一致
        matched = false; // 标记不匹配
        break; // 终止循环
      }
    }
    if (matched) { // 如果所有片段均匹配
      return { route, params }; // 返回匹配结果
    }
  }
  return { route: fallbackRoute, params: {} }; // 未匹配时返回兜底路由
}

function renderSidebar() { // 根据权限渲染侧边栏菜单
  const menuEl = document.getElementById('sidebar-menu'); // 获取菜单容器
  if (!menuEl) return; // 若不存在则直接返回
  menuEl.innerHTML = ''; // 清空旧内容
  menuItems.forEach((item) => { // 遍历菜单配置
    if (item.requiresAuth && !state.authToken) { // 未登录时跳过需要鉴权的菜单
      return; // 跳过该项
    }
    if (item.requiresAdmin && !state.currentUser?.is_admin) { // 非管理员隐藏管理员菜单
      return; // 跳过该项
    }
    const li = document.createElement('li'); // 创建列表项
    li.className = 'sidebar__menu-item'; // 设置样式类
    const button = document.createElement('button'); // 创建按钮
    button.className = 'sidebar__menu-button'; // 设置按钮样式
    button.type = 'button'; // 明确按钮类型
    button.textContent = item.label; // 显示菜单名称
    button.addEventListener('click', () => { // 绑定点击事件
      navigate(item.hash); // 切换到对应路由
    });
    if (window.location.hash.startsWith(item.hash)) { // 当前路由高亮
      button.classList.add('sidebar__menu-button--active'); // 添加选中样式
    }
    li.appendChild(button); // 挂载按钮到列表项
    menuEl.appendChild(li); // 添加到菜单容器
  });
}

function renderTopbar() { // 渲染顶部栏
  const titleEl = document.getElementById('topbar-title'); // 获取标题元素
  const actionsEl = document.getElementById('topbar-actions'); // 获取操作容器
  if (titleEl) { // 存在标题元素时
    titleEl.textContent = state.currentRoute?.route?.title || 'Archive 控制台'; // 设置标题文本
  }
  if (!actionsEl) return; // 若没有操作容器直接返回
  actionsEl.innerHTML = ''; // 清空旧内容
  if (state.currentUser) { // 登录状态下展示用户信息
    const userInfo = document.createElement('div'); // 创建用户信息容器
    userInfo.style.display = 'flex'; // 设置布局为水平
    userInfo.style.alignItems = 'center'; // 垂直居中
    userInfo.style.gap = '8px'; // 设置间距
    const name = document.createElement('span'); // 创建显示名称元素
    name.textContent = state.currentUser.full_name || state.currentUser.email; // 显示姓名或邮箱
    userInfo.appendChild(name); // 添加到容器
    const roleBadge = badge(state.currentUser.is_admin ? 'Admin' : 'User'); // 创建角色徽章
    userInfo.appendChild(roleBadge); // 添加徽章
    actionsEl.appendChild(userInfo); // 将用户信息插入操作栏
    const logoutBtn = document.createElement('button'); // 创建登出按钮
    logoutBtn.className = 'button button--ghost'; // 设置样式
    logoutBtn.type = 'button'; // 明确类型
    logoutBtn.textContent = '登出'; // 设置按钮文案
    logoutBtn.addEventListener('click', () => { // 绑定登出逻辑
      clearToken(); // 清除 token
      setCurrentUser(null); // 清空用户状态
      toast('已退出登录', 'info'); // 给出提示
      navigate('#/login'); // 跳回登录页
    });
    actionsEl.appendChild(logoutBtn); // 添加登出按钮
  }
}

async function handleRouteChange() { // 处理路由变化
  const { path, query } = parseHash(window.location.hash || '#/login'); // 解析当前 hash
  const match = matchRoute(path); // 匹配路由
  state.currentRoute = match; // 保存匹配结果
  const target = match.route; // 提取目标路由
  if (target.requiresAuth && !state.authToken) { // 未登录访问受限页面
    toast('请先登录后再访问该页面', 'error'); // 提示需要登录
    navigate('#/login'); // 重定向到登录
    return; // 停止后续处理
  }
  if (!target.requiresAuth && state.authToken && path !== '#/logout') { // 登录状态访问匿名页面
    if (!state.currentUser) { // 若用户信息未加载
      await loadCurrentUser(); // 先拉取当前用户
    }
    navigate('#/dashboard'); // 跳转至仪表盘
    return; // 终止后续逻辑
  }
  if (target.requiresAuth && state.authToken && !state.currentUser) { // 登录但未缓存用户
    const success = await loadCurrentUser(); // 尝试加载用户
    if (!success) { // 若失败则终止
      return; // 已在 loadCurrentUser 内处理重定向
    }
  }
  if (target.requiresAdmin && !state.currentUser?.is_admin) { // 非管理员访问管理员页面
    toast('需要管理员权限才能访问', 'error'); // 提示权限不足
    navigate('#/dashboard'); // 回到仪表盘
    return; // 停止处理
  }
  renderSidebar(); // 根据最新状态渲染侧边栏
  renderTopbar(); // 更新顶部栏
  const container = document.getElementById('app-view'); // 找到视图容器
  if (!container) return; // 若不存在则终止
  if (state.activeView && typeof state.activeView.unmount === 'function') { // 若存在旧视图
    state.activeView.unmount(); // 调用卸载逻辑
  }
  container.innerHTML = ''; // 清空容器内容
  const params = { ...match.params, query }; // 组合路径参数与查询参数
  state.activeView = target.view; // 记录当前视图模块
  if (state.activeView && typeof state.activeView.mount === 'function') { // 如果视图提供 mount
    await state.activeView.mount(container, params); // 执行挂载
  }
  container.focus(); // 将焦点移动到内容区
  renderSidebar(); // 再次刷新侧边栏确保高亮正确
  renderTopbar(); // 再次刷新顶部栏
}

async function loadCurrentUser() { // 拉取当前用户信息
  try { // 捕获异常
    const me = await authMe(); // 调用 /auth/me
    setCurrentUser(me); // 缓存用户信息
    return true; // 返回成功
  } catch (error) { // 捕获失败
    clearToken(); // 清理 token
    toast('登录已过期，请重新登录', 'error'); // 提示用户重新登录
    navigate('#/login'); // 跳回登录页
    return false; // 表示失败
  }
}

window.addEventListener('hashchange', handleRouteChange); // 监听 hash 变化以触发路由切换

window.addEventListener('app:unauthorized', () => { // 监听全局未授权事件
  clearToken(); // 清除 token
  toast('登录已过期，请重新登录', 'error'); // 提示重新登录
  navigate('#/login'); // 跳转登录
});

(async function init() { // 应用启动入口
  renderSidebar(); // 首次渲染侧边栏
  if (state.authToken) { // 若存在 token
    await loadCurrentUser(); // 预加载用户信息
  }
  await handleRouteChange(); // 执行首次路由渲染
})();
