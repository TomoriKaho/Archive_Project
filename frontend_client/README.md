# Archive AI Client Frontend

该目录包含面向终端用户的 Vue 3 客户端（搜索入口 + 聊天界面）。

## 技术栈
- Vue 3 + Vue CLI
- Vue Router 4
- Pinia 3
- Axios
- Sass

## 快速开始
```bash
cd frontend_client
npm install
npm run serve          # 默认在 http://localhost:8081
```

创建 `.env.local` 后配置后端接口地址与 Token 键名：
```bash
VUE_APP_API_BASE_URL=http://localhost:18000/api
VUE_APP_TOKEN_STORAGE_KEY=archive_ai_client_token
```

## 可用脚本
```bash
npm run serve    # 开发环境
npm run build    # 构建生产包（输出到 dist/）
```

## 目录结构
```
src/
  assets/styles/      # 全局样式（含主题与布局基础）
  components/         # 复用组件（搜索入口、聊天侧栏、聊天窗口）
  router/             # 路由与导航守卫
  services/           # Axios 实例与后端 API 封装
  store/              # Pinia 状态（认证、对话、领域）
  views/              # 页面：登录、首页、聊天
```
