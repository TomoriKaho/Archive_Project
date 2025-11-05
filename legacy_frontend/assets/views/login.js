import { authLogin, authMe } from '../api.js'; // 导入登录与用户信息接口
import { toast, spinner } from '../ui/components.js'; // 引入提示和加载组件
import { setToken, setCurrentUser, navigate } from '../app.js'; // 引入应用状态操作与导航函数

let containerRef = null; // 记录容器引用以便卸载时清空
let formRef = null; // 保存表单节点
let submitHandler = null; // 缓存提交事件处理函数

export default { // 导出视图对象
  async mount(container) { // 挂载视图
    containerRef = container; // 保存容器引用
    const title = document.createElement('h1'); // 创建标题
    title.textContent = '登录'; // 设置标题文本
    container.appendChild(title); // 插入标题
    const hint = document.createElement('p'); // 创建提示文本
    hint.textContent = '请输入邮箱和密码登录系统。'; // 设置提示内容
    container.appendChild(hint); // 添加提示
    formRef = document.createElement('form'); // 创建表单元素
    formRef.setAttribute('aria-label', '登录表单'); // 设置无障碍描述
    const emailGroup = document.createElement('div'); // 创建邮箱输入容器
    emailGroup.className = 'form-group'; // 应用表单组样式
    const emailLabel = document.createElement('label'); // 创建邮箱标签
    emailLabel.className = 'label'; // 设置样式
    emailLabel.setAttribute('for', 'login-email'); // 关联输入框
    emailLabel.textContent = '邮箱'; // 标签文本
    emailGroup.appendChild(emailLabel); // 添加标签
    const emailInput = document.createElement('input'); // 创建邮箱输入框
    emailInput.className = 'input'; // 设置样式
    emailInput.type = 'email'; // 指定类型
    emailInput.required = true; // 设置必填
    emailInput.id = 'login-email'; // 指定 ID
    emailInput.name = 'email'; // 指定 name
    emailInput.placeholder = 'user@example.com'; // 提示文本
    emailGroup.appendChild(emailInput); // 添加输入框
    formRef.appendChild(emailGroup); // 将组加入表单
    const passwordGroup = document.createElement('div'); // 创建密码输入容器
    passwordGroup.className = 'form-group'; // 应用样式
    const passwordLabel = document.createElement('label'); // 创建密码标签
    passwordLabel.className = 'label'; // 设置样式
    passwordLabel.setAttribute('for', 'login-password'); // 关联输入框
    passwordLabel.textContent = '密码'; // 标签文本
    passwordGroup.appendChild(passwordLabel); // 添加标签
    const passwordInput = document.createElement('input'); // 创建密码输入框
    passwordInput.className = 'input'; // 设置样式
    passwordInput.type = 'password'; // 指定类型
    passwordInput.required = true; // 必填
    passwordInput.minLength = 8; // 最小长度
    passwordInput.id = 'login-password'; // 设置 ID
    passwordInput.name = 'password'; // 设置 name
    passwordInput.placeholder = '至少 8 位密码'; // 提示文本
    passwordGroup.appendChild(passwordInput); // 添加输入框
    formRef.appendChild(passwordGroup); // 将组加入表单
    const actions = document.createElement('div'); // 创建操作区域
    actions.style.display = 'flex'; // 设置水平布局
    actions.style.alignItems = 'center'; // 垂直居中
    actions.style.gap = '12px'; // 元素间距
    const submitBtn = document.createElement('button'); // 创建提交按钮
    submitBtn.className = 'button'; // 应用主按钮样式
    submitBtn.type = 'submit'; // 指定提交类型
    submitBtn.textContent = '登录'; // 按钮文本
    actions.appendChild(submitBtn); // 添加按钮
    const registerLink = document.createElement('button'); // 创建注册跳转按钮
    registerLink.className = 'button button--ghost'; // 使用次级样式
    registerLink.type = 'button'; // 普通按钮
    registerLink.textContent = '没有账号？去注册'; // 按钮文本
    registerLink.addEventListener('click', () => navigate('#/register')); // 点击跳转注册
    actions.appendChild(registerLink); // 添加跳转按钮
    formRef.appendChild(actions); // 将操作区加入表单
    submitHandler = async (event) => { // 定义提交事件
      event.preventDefault(); // 阻止默认行为
      submitBtn.disabled = true; // 禁用提交按钮
      const loading = spinner(); // 创建加载指示器
      submitBtn.appendChild(loading); // 将加载图标放入按钮
      const formData = new FormData(formRef); // 读取表单数据
      const email = formData.get('email'); // 获取邮箱
      const password = formData.get('password'); // 获取密码
      try { // 捕获错误
        const loginRes = await authLogin({ email, password }); // 调用登录接口
        setToken(loginRes.access_token); // 写入 token
        const me = await authMe(); // 拉取当前用户
        setCurrentUser(me); // 缓存用户信息
        toast('登录成功，欢迎回来', 'success'); // 显示成功提示
        navigate('#/dashboard'); // 跳转仪表盘
      } catch (error) { // 登录失败处理
        if (error.status === 401) { // 未授权
          toast('邮箱或密码错误', 'error'); // 显示错误提示
        } else {
          toast(error.message || '登录失败，请稍后重试', 'error'); // 其他错误提示
        }
      } finally { // 最终处理
        submitBtn.disabled = false; // 恢复按钮
        loading.remove(); // 移除加载动画
      }
    }; // 提交事件定义结束
    formRef.addEventListener('submit', submitHandler); // 绑定表单提交
    containerRef.appendChild(formRef); // 渲染表单
  }, // mount 结束
  unmount() { // 卸载逻辑
    if (formRef && submitHandler) { // 如果表单与处理器存在
      formRef.removeEventListener('submit', submitHandler); // 移除事件监听
    }
    if (containerRef) { // 存在容器时
      containerRef.innerHTML = ''; // 清空内容
    }
    containerRef = null; // 释放容器引用
    formRef = null; // 释放表单引用
    submitHandler = null; // 清空事件处理器
  }, // unmount 结束
}; // 模块导出结束
