import { authRegister } from '../api.js'; // 导入注册接口
import { toast, spinner } from '../ui/components.js'; // 引入提示与加载组件
import { navigate } from '../app.js'; // 导入导航函数

let containerRef = null; // 保存容器引用
let formRef = null; // 保存表单引用
let submitHandler = null; // 保存提交处理器

export default { // 导出注册视图
  async mount(container) { // 挂载视图
    containerRef = container; // 记录容器
    const title = document.createElement('h1'); // 创建标题
    title.textContent = '注册'; // 设置标题文本
    container.appendChild(title); // 渲染标题
    const hint = document.createElement('p'); // 创建提示段落
    hint.textContent = '注册新账号时 is_admin 会强制为普通用户以确保安全。'; // 设置提示说明
    container.appendChild(hint); // 添加提示
    formRef = document.createElement('form'); // 创建注册表单
    formRef.setAttribute('aria-label', '注册表单'); // 设置无障碍描述
    const emailGroup = document.createElement('div'); // 邮箱输入容器
    emailGroup.className = 'form-group'; // 应用样式
    const emailLabel = document.createElement('label'); // 邮箱标签
    emailLabel.className = 'label'; // 设置样式
    emailLabel.setAttribute('for', 'register-email'); // 关联输入框
    emailLabel.textContent = '邮箱'; // 标签文本
    emailGroup.appendChild(emailLabel); // 添加标签
    const emailInput = document.createElement('input'); // 邮箱输入框
    emailInput.className = 'input'; // 应用样式
    emailInput.type = 'email'; // 指定类型
    emailInput.required = true; // 设置必填
    emailInput.id = 'register-email'; // 指定 ID
    emailInput.name = 'email'; // 指定 name
    emailInput.placeholder = 'user@example.com'; // 提示文本
    emailGroup.appendChild(emailInput); // 添加输入框
    formRef.appendChild(emailGroup); // 将组加入表单
    const nameGroup = document.createElement('div'); // 姓名输入容器
    nameGroup.className = 'form-group'; // 应用样式
    const nameLabel = document.createElement('label'); // 姓名标签
    nameLabel.className = 'label'; // 设置样式
    nameLabel.setAttribute('for', 'register-full-name'); // 关联输入框
    nameLabel.textContent = '姓名（可选）'; // 标签文本
    nameGroup.appendChild(nameLabel); // 添加标签
    const nameInput = document.createElement('input'); // 姓名输入框
    nameInput.className = 'input'; // 应用样式
    nameInput.type = 'text'; // 指定类型
    nameInput.id = 'register-full-name'; // 指定 ID
    nameInput.name = 'full_name'; // 指定 name
    nameInput.placeholder = '请输入昵称或姓名'; // 提示文本
    nameGroup.appendChild(nameInput); // 添加输入框
    formRef.appendChild(nameGroup); // 将组加入表单
    const passwordGroup = document.createElement('div'); // 密码输入容器
    passwordGroup.className = 'form-group'; // 应用样式
    const passwordLabel = document.createElement('label'); // 密码标签
    passwordLabel.className = 'label'; // 设置样式
    passwordLabel.setAttribute('for', 'register-password'); // 关联输入框
    passwordLabel.textContent = '密码（至少 8 位）'; // 标签文本
    passwordGroup.appendChild(passwordLabel); // 添加标签
    const passwordInput = document.createElement('input'); // 密码输入框
    passwordInput.className = 'input'; // 应用样式
    passwordInput.type = 'password'; // 指定类型
    passwordInput.required = true; // 设置必填
    passwordInput.minLength = 8; // 设置最小长度
    passwordInput.id = 'register-password'; // 指定 ID
    passwordInput.name = 'password'; // 指定 name
    passwordInput.placeholder = '至少 8 位密码'; // 提示文本
    passwordGroup.appendChild(passwordInput); // 添加输入框
    formRef.appendChild(passwordGroup); // 将组加入表单
    const actions = document.createElement('div'); // 操作区
    actions.style.display = 'flex'; // 横向布局
    actions.style.alignItems = 'center'; // 垂直居中
    actions.style.gap = '12px'; // 元素间距
    const submitBtn = document.createElement('button'); // 提交按钮
    submitBtn.className = 'button'; // 主按钮样式
    submitBtn.type = 'submit'; // 指定提交类型
    submitBtn.textContent = '注册'; // 按钮文本
    actions.appendChild(submitBtn); // 添加按钮
    const backLink = document.createElement('button'); // 返回登录按钮
    backLink.className = 'button button--ghost'; // 次级样式
    backLink.type = 'button'; // 指定类型
    backLink.textContent = '已有账号？去登录'; // 按钮文本
    backLink.addEventListener('click', () => navigate('#/login')); // 点击跳回登录
    actions.appendChild(backLink); // 添加按钮
    formRef.appendChild(actions); // 将操作区加入表单
    submitHandler = async (event) => { // 定义提交处理
      event.preventDefault(); // 阻止默认行为
      submitBtn.disabled = true; // 禁用按钮
      const loading = spinner(); // 创建加载图标
      submitBtn.appendChild(loading); // 添加到按钮
      const formData = new FormData(formRef); // 读取表单数据
      const email = formData.get('email'); // 获取邮箱
      const password = formData.get('password'); // 获取密码
      const full_name = formData.get('full_name') || null; // 获取姓名
      try { // 捕获异常
        await authRegister({ email, password, full_name }); // 调用注册接口
        toast('注册成功，请使用账号登录', 'success'); // 提示成功
        navigate('#/login'); // 跳转登录
      } catch (error) { // 处理错误
        toast(error.message || '注册失败，请检查输入', 'error'); // 提示错误
      } finally { // 收尾处理
        submitBtn.disabled = false; // 恢复按钮
        loading.remove(); // 移除加载动画
      }
    }; // 提交处理结束
    formRef.addEventListener('submit', submitHandler); // 绑定提交事件
    containerRef.appendChild(formRef); // 渲染表单
  }, // mount 结束
  unmount() { // 卸载视图
    if (formRef && submitHandler) { // 若存在表单事件
      formRef.removeEventListener('submit', submitHandler); // 移除监听
    }
    if (containerRef) { // 存在容器
      containerRef.innerHTML = ''; // 清空内容
    }
    containerRef = null; // 重置容器引用
    formRef = null; // 重置表单引用
    submitHandler = null; // 重置事件处理器
  }, // unmount 结束
}; // 模块导出结束
