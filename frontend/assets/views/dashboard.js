import { getDocuments, getUsers } from '../api.js'; // 导入统计所需接口
import { badge, toast, spinner } from '../ui/components.js'; // 引入徽章、提示与加载组件
import { getCurrentUser, navigate } from '../app.js'; // 获取当前用户并提供导航

let containerRef = null; // 保存容器引用

export default { // 导出仪表盘视图
  async mount(container) { // 挂载逻辑
    containerRef = container; // 记录容器引用
    const user = getCurrentUser(); // 获取当前用户
    const title = document.createElement('h1'); // 创建标题
    title.textContent = '仪表盘'; // 设置标题文本
    container.appendChild(title); // 添加标题
    const welcome = document.createElement('p'); // 创建欢迎语
    welcome.textContent = `欢迎回来，${user?.full_name || user?.email || '访客'}！`; // 动态插入用户信息
    container.appendChild(welcome); // 渲染欢迎语
    const profileCard = document.createElement('div'); // 创建用户信息卡片
    profileCard.className = 'table-wrapper'; // 应用卡片样式
    const emailRow = document.createElement('p'); // 创建邮箱行
    emailRow.textContent = `邮箱：${user?.email ?? '未知'}`; // 显示邮箱
    profileCard.appendChild(emailRow); // 添加邮箱信息
    const nameRow = document.createElement('p'); // 创建姓名行
    nameRow.textContent = `姓名：${user?.full_name ?? '未填写'}`; // 显示姓名
    profileCard.appendChild(nameRow); // 添加姓名
    const roleRow = document.createElement('p'); // 创建角色行
    roleRow.textContent = '角色：'; // 前缀文案
    const roleTag = badge(user?.is_admin ? 'Admin' : 'User'); // 根据权限显示徽章
    roleRow.appendChild(roleTag); // 添加徽章
    profileCard.appendChild(roleRow); // 将角色信息加入卡片
    container.appendChild(profileCard); // 渲染卡片
    const statsWrapper = document.createElement('div'); // 创建统计区域
    statsWrapper.style.display = 'grid'; // 使用栅格布局
    statsWrapper.style.gridTemplateColumns = 'repeat(auto-fit, minmax(220px, 1fr))'; // 自适应列数
    statsWrapper.style.gap = '16px'; // 设置间距
    statsWrapper.style.marginTop = '24px'; // 与上方元素拉开距离
    container.appendChild(statsWrapper); // 渲染统计区域
    const docCard = document.createElement('div'); // 创建文档统计卡片
    docCard.className = 'table-wrapper'; // 应用卡片样式
    const docTitle = document.createElement('h2'); // 创建卡片标题
    docTitle.textContent = '文档总数'; // 设置文案
    docCard.appendChild(docTitle); // 添加标题
    const docCount = document.createElement('p'); // 创建数量文本
    docCount.textContent = '加载中...'; // 初始显示
    docCard.appendChild(docCount); // 添加数量
    const docButton = document.createElement('button'); // 创建跳转按钮
    docButton.className = 'button'; // 主按钮样式
    docButton.type = 'button'; // 指定类型
    docButton.textContent = '查看文档'; // 按钮文案
    docButton.addEventListener('click', () => navigate('#/documents')); // 点击跳转文档页
    docCard.appendChild(docButton); // 添加按钮
    statsWrapper.appendChild(docCard); // 渲染卡片
    let userCard = null; // 预留用户统计卡片引用
    let userCount = null; // 预留用户数量文本
    if (user?.is_admin) { // 仅管理员显示用户统计
      userCard = document.createElement('div'); // 创建卡片
      userCard.className = 'table-wrapper'; // 应用样式
      const userTitle = document.createElement('h2'); // 创建标题
      userTitle.textContent = '用户总数'; // 设置文案
      userCard.appendChild(userTitle); // 添加标题
      userCount = document.createElement('p'); // 创建数量文本
      userCount.textContent = '加载中...'; // 初始显示
      userCard.appendChild(userCount); // 添加数量
      const userButton = document.createElement('button'); // 创建跳转按钮
      userButton.className = 'button'; // 主按钮样式
      userButton.type = 'button'; // 指定类型
      userButton.textContent = '管理用户'; // 按钮文案
      userButton.addEventListener('click', () => navigate('#/users')); // 点击跳转用户页
      userCard.appendChild(userButton); // 添加按钮
      statsWrapper.appendChild(userCard); // 渲染卡片
    }
    const loadingIndicator = spinner(); // 创建全局加载指示器
    container.appendChild(loadingIndicator); // 渲染加载状态
    try { // 请求统计数据
      const [docRes, userRes] = await Promise.all([ // 并发请求
        getDocuments({ limit: 1, offset: 0 }), // 获取文档总数
        user?.is_admin ? getUsers({ limit: 1, offset: 0 }) : Promise.resolve(null), // 管理员获取用户总数
      ]); // Promise.all 结束
      const docTotal = docRes?.total ?? docRes?.items?.length ?? 0; // 解析文档数量
      docCount.textContent = `${docTotal} 篇`; // 显示文档数量
      if (user?.is_admin && userCard && userCount) { // 管理员时填充用户数量
        const usersTotal = userRes?.total ?? userRes?.items?.length ?? 0; // 解析用户数量
        userCount.textContent = `${usersTotal} 人`; // 显示用户数量
      }
    } catch (error) { // 捕获错误
      toast('加载统计信息失败', 'error'); // 显示错误提示
    } finally { // 收尾处理
      loadingIndicator.remove(); // 移除加载动画
    }
    const quickLinks = document.createElement('div'); // 创建快捷入口
    quickLinks.style.marginTop = '32px'; // 与统计区域保持间距
    quickLinks.style.display = 'flex'; // 使用弹性布局
    quickLinks.style.flexWrap = 'wrap'; // 支持换行
    quickLinks.style.gap = '12px'; // 设置间距
    const toDocuments = document.createElement('button'); // 创建文档快捷按钮
    toDocuments.className = 'button'; // 主按钮样式
    toDocuments.type = 'button'; // 指定类型
    toDocuments.textContent = '快速创建文档'; // 按钮文本
    toDocuments.addEventListener('click', () => navigate('#/documents')); // 跳转文档页
    quickLinks.appendChild(toDocuments); // 添加按钮
    const toDomains = document.createElement('button'); // 创建域管理按钮
    toDomains.className = 'button button--ghost'; // 次级样式
    toDomains.type = 'button'; // 指定类型
    toDomains.textContent = '维护域配置'; // 按钮文案
    toDomains.addEventListener('click', () => navigate('#/domains')); // 跳转域管理
    quickLinks.appendChild(toDomains); // 添加按钮
    if (user?.is_admin) { // 管理员显示邀请按钮
      const toUsers = document.createElement('button'); // 创建按钮
      toUsers.className = 'button button--ghost'; // 次级样式
      toUsers.type = 'button'; // 指定类型
      toUsers.textContent = '邀请同事'; // 按钮文案
      toUsers.addEventListener('click', () => navigate('#/users')); // 跳转用户页
      quickLinks.appendChild(toUsers); // 添加按钮
    }
    container.appendChild(quickLinks); // 渲染快捷入口
  }, // mount 结束
  unmount() { // 卸载逻辑
    if (containerRef) { // 若存在容器
      containerRef.innerHTML = ''; // 清空内容
    }
    containerRef = null; // 释放引用
  }, // unmount 结束
}; // 模块导出结束
