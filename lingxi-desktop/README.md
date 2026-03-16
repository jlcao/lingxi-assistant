# Lingxi Desktop

Lingxi Agent 终端助手 - V2.0 纯客户端架构

## 技术栈

- **Electron** ^28.0.0 - 跨平台桌面应用框架
- **Vue 3** ^3.3.4 - 渐进式 JavaScript 框架
- **TypeScript** ^5.3.3 - JavaScript 的超集
- **Vite** ^5.0.10 - 下一代前端构建工具
- **Element Plus** ^2.4.4 - Vue 3 组件库
- **Pinia** ^2.1.7 - Vue 状态管理库
- **Axios** ^1.6.2 - HTTP 客户端
- **WebSocket** ^8.19.0 - 实时双向通信
- **Vue Router** ^4.2.5 - 官方路由管理器
- **Sass** ^1.69.5 - CSS 预处理器

## 项目结构

```
lingxi-desktop/
├── electron/                    # Electron 主进程代码
│   ├── main/                   # 主进程模块
│   │   ├── index.ts            # 主进程入口，IPC 处理器注册
│   │   ├── windowManager.ts    # 窗口管理（最小化到托盘、边缘隐藏）
│   │   ├── apiClient.ts        # HTTP API 客户端（带重试机制）
│   │   ├── wsClient.ts         # WebSocket 客户端（心跳、重连）
│   │   └── fileManager.ts      # 文件管理（选择、保存、目录树）
│   └── preload/                # 预加载脚本
│       └── index.ts            # IPC 桥接，暴露 API 给渲染进程
├── src/                        # 渲染进程代码
│   ├── components/             # Vue 组件
│   │   ├── chat/              # 聊天相关组件
│   │   │   ├── ContextBar.vue      # 上下文工具栏
│   │   │   ├── InputArea.vue       # 输入区域
│   │   │   ├── MessageList.vue     # 消息列表
│   │   │   ├── ModelRouteBar.vue   # 模型路由展示栏
│   │   │   ├── StepInterventionCard.vue  # 步骤干预卡片
│   │   │   └── ThoughtChainPanel.vue   # 思考链面板
│   │   ├── workspace/         # 工作区组件
│   │   │   ├── FileWorkspace.vue   # 文件工作区
│   │   │   └── SkillCenter.vue     # 技能中心
│   │   ├── ChatCore.vue            # 聊天核心组件
│   │   ├── EdgeWidget.vue          # 边缘小部件
│   │   ├── HistoryChat.vue         # 历史聊天
│   │   ├── LayoutContainer.vue     # 布局容器
│   │   ├── ResumeBanner.vue        # 恢复横幅
│   │   ├── SkillWorkspace.vue      # 技能工作区
│   │   ├── Splitter.vue            # 分割器
│   │   └── TitleBar.vue            # 自定义标题栏
│   ├── stores/                # Pinia 状态管理
│   │   └── app.ts             # 应用全局状态
│   ├── router/                # Vue Router 路由
│   │   └── index.ts           # 路由配置
│   ├── styles/                # 全局样式
│   │   ├── main.scss          # 主样式文件
│   │   └── variables.scss     # SCSS 变量定义
│   ├── types/                 # TypeScript 类型定义
│   │   ├── electron.d.ts      # Electron API 类型
│   │   └── index.ts           # 通用类型定义
│   ├── views/                 # 页面级组件
│   │   ├── Home.vue           # 主页
│   │   └── Settings.vue       # 设置页
│   ├── App.vue                # 根组件
│   └── main.ts                # 渲染进程入口
├── index.html                 # HTML 模板
├── package.json               # 项目配置
├── tsconfig.json              # TypeScript 配置
└── vite.config.ts             # Vite 配置
```

## 开发

### 安装依赖

```bash
pnpm install
```

### 启动开发服务器

```bash
npm run dev
```

### 启动 Electron 应用

```bash
npm run electron:dev
```

## 构建

### 构建前端资源

```bash
npm run build
```

### 打包 Electron 应用

```bash
npm run electron:build
```

### 打包特定平台

```bash
npm run electron:build:win    # Windows (NSIS + 便携版)
npm run electron:build:mac    # macOS (DMG + ZIP)
npm run electron:build:linux  # Linux (AppImage + deb)
```

## 核心特性

### 1. 纯客户端架构
- 通过 HTTP REST API 与后端服务通信
- WebSocket 实时推送 Agent 执行状态
- 前后端彻底解耦，支持独立部署

### 2. 透明化交互
- **思考链展示**：实时展示 Agent 分析、规划、执行全流程
- **模型路由**：显示智能模型选择策略及 Token 预估
- **步骤可视化**：每个执行步骤的状态、输入输出清晰可见

### 3. 状态可控
- **断点续传**：支持任务暂停与从检查点恢复
- **步骤级重试**：失败步骤可单独重试，支持人工干预
- **多断点管理**：并行管理多个检查点，灵活切换

### 4. 能力可视
- **技能中心**：卡片式展示已安装技能及状态
- **技能管理**：支持安装、诊断、重载技能
- **异常自愈**：提供诊断引导与修复建议

### 5. 资源感知
- **Token 监控**：实时展示 Token 使用量及水位
- **系统资源**：监控 CPU、内存、磁盘使用情况
- **成本预估**：任务执行前显示预计 Token 消耗

### 6. 跨平台一致
- **原生体验**：自定义标题栏、托盘图标、边缘隐藏
- **文件操作**：统一的文件选择、保存、目录浏览
- **多平台打包**：一次构建，多平台分发

## 架构设计

### 进程通信架构

```
┌─────────────────┐      IPC       ┌─────────────────┐
│  渲染进程        │ ◄────────────►  │  主进程         │
│  (Vue 3 + TS)   │                │  (Electron)     │
└─────────────────┘                └────────┬────────┘
                                            │
                          ┌─────────────────┼─────────────────┐
                          │                 │                 │
                          ▼                 ▼                 ▼
                   ┌────────────┐   ┌────────────┐   ┌────────────┐
                   │ HTTP API   │   │ WebSocket  │   │ 文件系统    │
                   │ 客户端      │   │ 客户端     │   │ 管理器      │
                   └────────────┘   └────────────┘   └────────────┘
```

### 主进程模块

- **WindowManager**：窗口生命周期管理、托盘集成、边缘隐藏
- **ApiClient**：HTTP REST 通信，支持指数退避重试（最多 3 次）
- **WsClient**：WebSocket 实时通信，支持心跳检测、自动重连（最多 10 次）
- **FileManager**：文件对话框、目录树读取、外部资源打开

### 渲染进程模块

- **ChatCore**：聊天核心逻辑，处理消息发送、会话管理
- **MessageList**：消息列表渲染，支持虚拟滚动
- **ThoughtChainPanel**：思考链可视化展示
- **ModelRouteBar**：模型路由策略展示与覆盖
- **SkillCenter**：技能管理与展示
- **Pinia Store**：全局状态管理（会话、消息、WebSocket 状态等）

## 核心 API

### Electron API（通过 preload 暴露）

```typescript
window.electronAPI = {
  window: {
    minimize(),           // 最小化窗口
    toggle(),             // 切换窗口显示/隐藏
    maximize(),           // 最大化/还原窗口
    isMaximized(),        // 检查是否最大化
    edgeCheck()           // 检查边缘位置
  },
  file: {
    select(filters),      // 选择文件
    selectDirectory(),    // 选择目录
    selectFiles(filters), // 选择多个文件
    save(defaultPath),    // 保存文件
    openExplorer(path),   // 在资源管理器中打开
    readDirectoryTree(path, maxDepth) // 读取目录树
  },
  api: {
    getSessions(),                    // 获取会话列表
    getSessionHistory(id, maxTurns),  // 获取会话历史
    createSession(userName),          // 创建会话
    deleteSession(id),                // 删除会话
    updateSessionName(id, name),      // 更新会话名称
    clearSessionHistory(id),          // 清除会话历史
    executeTask(task, sessionId),     // 执行任务
    getTaskStatus(taskId),            // 获取任务状态
    retryTask(taskId, stepIndex),     // 重试任务
    cancelTask(taskId),               // 取消任务
    getCheckpoints(),                 // 获取检查点
    resumeCheckpoint(sessionId),      // 恢复检查点
    getSkills(),                      // 获取技能列表
    installSkill(skillData, files),   // 安装技能
    diagnoseSkill(skillId),           // 诊断技能
    getResourceUsage(),               // 获取资源使用情况
    getConfig(),                      // 获取配置
    updateConfig(config)              // 更新配置
  },
  ws: {
    connect(sessionId),     // 连接 WebSocket
    disconnect(),           // 断开 WebSocket
    isConnected(),          // 检查连接状态
    sendMessage(message),   // 发送消息
    onConnected(callback),  // 连接成功回调
    onDisconnected(cb),     // 断开连接回调
    onThoughtChain(cb),     // 思考链更新回调
    onStepStart(cb),        // 步骤开始回调
    onStepEnd(cb),          // 步骤结束回调
    onTaskStart(cb),        // 任务开始回调
    onTaskEnd(cb),          // 任务结束回调
    onThinkStart(cb),       // 思考开始回调
    onThinkStream(cb),      // 思考流式回调
    onThinkFinal(cb),       // 思考最终结果回调
    onPlanStart(cb),        // 规划开始回调
    onPlanFinal(cb),        // 规划最终结果回调
    onTaskFailed(cb)        // 任务失败回调
  }
}
```

### HTTP API 端点

后端服务默认运行在 `http://127.0.0.1:5000`

- `GET /api/sessions` - 获取会话列表
- `GET /api/sessions/:id` - 获取会话详情
- `GET /api/sessions/:id/history` - 获取会话历史
- `POST /api/sessions` - 创建会话
- `DELETE /api/sessions/:id` - 删除会话
- `PATCH /api/sessions/:id` - 更新会话
- `DELETE /api/sessions/:id/history` - 清除会话历史
- `POST /api/tasks/execute` - 执行任务
- `GET /api/tasks/:id/status` - 获取任务状态
- `POST /api/tasks/:id/retry` - 重试任务
- `POST /api/tasks/:id/cancel` - 取消任务

### WebSocket 消息类型

- `thought_chain` - 思考链更新
- `step_start` - 步骤开始
- `step_end` - 步骤结束
- `task_start` - 任务开始
- `task_end` - 任务结束
- `task_failed` - 任务失败
- `think_start` - 思考开始
- `think_stream` - 思考流式输出
- `think_final` - 思考最终结果
- `plan_start` - 规划开始
- `plan_final` - 规划最终结果
- `heartbeat` - 心跳包

## 配置说明

### TypeScript 配置

- 严格模式启用（`strict: true`）
- 路径别名：`@/*` -> `src/*`, `@main/*` -> `electron/main/*`
- 目标环境：ES2020

### Vite 配置

- 开发服务器端口：5173
- Electron 主进程输出：`dist-electron/main`
- Electron 预加载输出：`dist-electron/preload`
- SCSS 全局变量注入

### Electron Builder 配置

- **Windows**: NSIS 安装器 + 便携版
- **macOS**: DMG + ZIP（应用类别：效率工具）
- **Linux**: AppImage + deb

## 开发规范

### 代码风格

- 使用 TypeScript 严格类型检查
- Vue 3 Composition API（`<script setup>`）
- SCSS 预处理器，使用全局变量
- Element Plus 组件库统一 UI 风格

### 提交规范

遵循 Conventional Commits 规范：
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 重构代码
- `test`: 测试相关
- `chore`: 构建/工具链相关

## 常见问题

### 1. WebSocket 连接失败

**现象**：控制台显示 `ECONNREFUSED` 错误

**解决方案**：
1. 检查后端服务是否启动（默认端口 5000）
2. 检查端口是否被占用
3. 确认后端地址配置正确

### 2. 开发环境热更新不生效

**解决方案**：
1. 确保 Vite 开发服务器正常运行（端口 5173）
2. 检查 `vite-plugin-electron` 配置
3. 重启 `npm run electron:dev`

### 3. 打包后文件路径错误

**解决方案**：
1. 使用 `__dirname` 获取绝对路径
2. 检查 `vite.config.ts` 中的输出目录配置
3. 确保资源文件在 `files` 配置中声明

## 许可证

MIT
