# Archive Project Client Frontend

基于 Vue 3 + Vue CLI 的客户端界面，实现“搜索入口页 + 对话页面”的双页面结构：

- **主页（`/`）**：提供类似搜索引擎的单输入框，提交后跳转到对话界面；
- **对话页（`/chat`）**：包含左侧会话列表与右侧聊天窗口，可返回主页。

## 开发

```bash
npm install
npm run serve
```

默认开发服务器运行在 [http://localhost:8080](http://localhost:8080)。

## 构建

```bash
npm run build
```

打包产物输出至 `dist/` 目录。
