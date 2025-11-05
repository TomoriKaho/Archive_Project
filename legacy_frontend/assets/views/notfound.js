import { navigate } from '../app.js'; // 引入导航函数以便返回首页

let containerRef = null; // 保存容器引用

export default { // 导出 404 视图
  async mount(container) { // 挂载逻辑
    containerRef = container; // 保存容器引用
    const title = document.createElement('h1'); // 创建标题元素
    title.textContent = '页面未找到'; // 设置标题文本
    container.appendChild(title); // 渲染标题
    const description = document.createElement('p'); // 创建描述段落
    description.textContent = '抱歉，您访问的页面不存在。'; // 设置描述文本
    container.appendChild(description); // 渲染描述
    const backBtn = document.createElement('button'); // 创建返回按钮
    backBtn.className = 'button'; // 应用主按钮样式
    backBtn.type = 'button'; // 指定类型
    backBtn.textContent = '返回仪表盘'; // 设置按钮文本
    backBtn.addEventListener('click', () => navigate('#/dashboard')); // 点击跳转仪表盘
    container.appendChild(backBtn); // 渲染按钮
  }, // mount 结束
  unmount() { // 卸载逻辑
    if (containerRef) containerRef.innerHTML = ''; // 清空容器内容
    containerRef = null; // 释放引用
  }, // unmount 结束
}; // 模块导出结束
