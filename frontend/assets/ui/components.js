let toastContainer = null; // 缓存 toast 容器避免重复创建

export function toast(message, type = 'info') { // 全局提示组件
  if (!toastContainer) { // 首次调用时初始化容器
    toastContainer = document.getElementById('toast-container'); // 尝试从页面找到容器
    if (!toastContainer) { // 若不存在则手动创建
      toastContainer = document.createElement('div'); // 创建容器元素
      toastContainer.id = 'toast-container'; // 设置 ID 便于复用
      toastContainer.className = 'toast-container'; // 应用样式
      toastContainer.setAttribute('role', 'status'); // 提示屏幕阅读器
      toastContainer.setAttribute('aria-live', 'polite'); // 配置无障碍
      document.body.appendChild(toastContainer); // 挂载到页面
    }
  }
  const toastEl = document.createElement('div'); // 创建单个 toast 元素
  toastEl.className = `toast toast--${type}`; // 根据类型设置样式
  toastEl.setAttribute('role', 'alert'); // 标记为警示信息
  toastEl.textContent = message; // 写入提示文本
  toastContainer.appendChild(toastEl); // 加入容器显示
  setTimeout(() => { // 三秒后自动隐藏
    toastEl.style.opacity = '0'; // 逐渐透明
    toastEl.style.transform = 'translateY(-10px)'; // 添加位移动画
    setTimeout(() => toastEl.remove(), 300); // 动画结束后移除节点
  }, 3000); // 保持三秒可见
}

export function confirmDialog(message, onConfirm) { // 简易确认对话框
  const backdrop = document.createElement('div'); // 创建遮罩层
  backdrop.className = 'dialog-backdrop'; // 应用遮罩样式
  backdrop.setAttribute('role', 'dialog'); // 标明对话框语义
  backdrop.setAttribute('aria-modal', 'true'); // 告知屏幕阅读器锁定焦点
  const dialog = document.createElement('div'); // 创建对话框面板
  dialog.className = 'dialog'; // 应用面板样式
  backdrop.appendChild(dialog); // 将面板放入遮罩
  const text = document.createElement('p'); // 展示提示文本
  text.textContent = message; // 写入提示内容
  dialog.appendChild(text); // 添加到对话框
  const actions = document.createElement('div'); // 创建按钮区域
  actions.className = 'dialog__actions'; // 设置布局样式
  dialog.appendChild(actions); // 添加到面板
  const cancelBtn = document.createElement('button'); // 取消按钮
  cancelBtn.className = 'button button--ghost'; // 使用次级按钮样式
  cancelBtn.type = 'button'; // 指定按钮类型
  cancelBtn.textContent = '取消'; // 按钮文案
  cancelBtn.addEventListener('click', () => backdrop.remove()); // 点击取消关闭对话框
  actions.appendChild(cancelBtn); // 放入按钮区域
  const confirmBtn = document.createElement('button'); // 确认按钮
  confirmBtn.className = 'button'; // 主按钮样式
  confirmBtn.type = 'button'; // 指定类型
  confirmBtn.textContent = '确认'; // 按钮文案
  confirmBtn.addEventListener('click', () => { // 绑定确认逻辑
    backdrop.remove(); // 先关闭对话框
    if (typeof onConfirm === 'function') { // 判断回调是否存在
      onConfirm(); // 执行确认回调
    }
  });
  actions.appendChild(confirmBtn); // 添加按钮
  document.body.appendChild(backdrop); // 将对话框挂载到页面
  confirmBtn.focus(); // 将焦点移至确认按钮
}

export function spinner() { // 简易加载指示器
  const node = document.createElement('span'); // 创建 span 元素
  node.className = 'spinner'; // 应用旋转样式
  node.setAttribute('aria-hidden', 'true'); // 对屏幕阅读器隐藏
  return node; // 返回节点供调用方使用
}

export function badge(text) { // 创建徽章
  const node = document.createElement('span'); // 创建 span 元素
  node.className = 'badge'; // 设置徽章样式
  node.textContent = text; // 填充文本
  return node; // 返回徽章节点
}

export function renderTable(items, columns) { // 通用表格渲染函数
  if (!items || items.length === 0) { // 当数据为空时
    const empty = document.createElement('div'); // 创建空状态节点
    empty.className = 'table-empty'; // 应用空状态样式
    empty.textContent = '暂无数据'; // 提示文本
    return empty; // 返回空状态
  }
  const table = document.createElement('table'); // 创建表格元素
  const thead = document.createElement('thead'); // 创建表头
  const headRow = document.createElement('tr'); // 表头行
  columns.forEach((col) => { // 遍历列定义
    const th = document.createElement('th'); // 创建表头单元格
    th.textContent = col.label; // 设置列标题
    headRow.appendChild(th); // 加入表头行
  });
  thead.appendChild(headRow); // 将表头行加入表头
  table.appendChild(thead); // 将表头加入表格
  const tbody = document.createElement('tbody'); // 创建表体
  items.forEach((item) => { // 遍历数据行
    const row = document.createElement('tr'); // 创建表格行
    columns.forEach((col) => { // 遍历列
      const cell = document.createElement('td'); // 创建单元格
      if (typeof col.render === 'function') { // 自定义渲染函数
        const content = col.render(item); // 调用渲染函数
        if (content instanceof Node) { // 若返回 DOM
          cell.appendChild(content); // 直接插入节点
        } else {
          cell.textContent = content ?? ''; // 否则转为字符串
        }
      } else {
        const value = item[col.key]; // 取默认字段
        cell.textContent = value !== undefined && value !== null ? String(value) : ''; // 显示文本或空字符串
      }
      row.appendChild(cell); // 单元格加入行
    });
    tbody.appendChild(row); // 行加入表体
  });
  table.appendChild(tbody); // 表体加入表格
  return table; // 返回表格节点
}

export function renderPagination({ total = 0, limit = 20, offset = 0, onChange }) { // 渲染分页控件
  const wrapper = document.createElement('div'); // 创建容器
  wrapper.className = 'pagination'; // 设置样式
  const totalPages = Math.max(1, Math.ceil(total / (limit || 1))); // 计算总页数
  const currentPage = Math.floor(offset / limit) + 1; // 计算当前页
  const prevBtn = document.createElement('button'); // 创建上一页按钮
  prevBtn.className = 'pagination__button'; // 应用样式
  prevBtn.type = 'button'; // 指定类型
  prevBtn.textContent = '上一页'; // 按钮文案
  prevBtn.disabled = currentPage <= 1; // 首页禁用
  wrapper.appendChild(prevBtn); // 添加到容器
  const info = document.createElement('span'); // 创建信息文本
  info.textContent = `第 ${currentPage} / ${totalPages} 页，总计 ${total} 条`; // 显示分页信息
  wrapper.appendChild(info); // 添加到容器
  const nextBtn = document.createElement('button'); // 创建下一页按钮
  nextBtn.className = 'pagination__button'; // 应用样式
  nextBtn.type = 'button'; // 指定类型
  nextBtn.textContent = '下一页'; // 按钮文案
  nextBtn.disabled = currentPage >= totalPages; // 末页禁用
  wrapper.appendChild(nextBtn); // 添加到容器
  prevBtn.addEventListener('click', () => { // 绑定上一页事件
    if (currentPage > 1 && typeof onChange === 'function') { // 确保可翻页且存在回调
      onChange({ limit, offset: offset - limit }); // 通知外部更新分页
    }
  });
  nextBtn.addEventListener('click', () => { // 绑定下一页事件
    if (currentPage < totalPages && typeof onChange === 'function') { // 检查页码与回调
      onChange({ limit, offset: offset + limit }); // 通知外部更新分页
    }
  });
  return wrapper; // 返回分页控件
}
