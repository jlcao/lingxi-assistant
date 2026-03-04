# Lingxi Agent 终端助手界面设计文档（V2.1）
**技术栈**：Electron + Vue3 + TypeScript  
**核心变更**：架构调整为纯客户端模式，通过HTTP/SSE与后端服务通信，实现UI与业务逻辑彻底解耦，保留V1.3全量交互能力

## 版本历史
- **V1.0**：初始架构设计（PySide6）
- **V1.1**：引入 MVVM 架构与异步任务池（PySide6）
- **V1.2**：深度适配底层 Agent 能力（思维链可视化、断点续传、技能中心）（PySide6）
- **V1.2+**：交互深度优化与异常处理闭环（模型路由可视化、技能自愈、多断点管理、智能干预）（PySide6）
- **V1.3**：技术栈全面迁移至 Electron+Vue3+TypeScript，重构分层架构，优化跨平台一致性与开发体验，保留V1.2+全量功能与验收标准
- **V2.0**：架构调整为纯客户端模式，删除主线程业务逻辑，通过HTTP/WebSocket与后端服务通信，实现前后端彻底解耦
- **V2.1**：根据后端API接口设计文档（V4.0）更新HTTP客户端、SSE流式响应处理和类型定义，确保前后端数据模型完全对齐，**移除WebSocket，改用SSE流式响应**

---

## 一、设计核心目标（V2.1 架构重构）
基于 **Electron+Vue3** 实现**透明化、可控化、跨平台**的终端助手，采用**纯客户端架构**，通过HTTP/SSE与后端服务通信，彻底解决V1.3版本中前后端职责重叠、数据不一致、通信缺失等问题，同时完全保留V1.3的核心交互能力。

### 核心目标（全量继承V1.3，架构层面重构）
1. **过程透明**：实时展示Agent思考路径、任务分级及模型路由策略（通过SSE接收后端流式推送）
2. **状态可控**：支持断点续传、步骤级重试、人工干预与多断点并行管理（通过HTTP API调用后端）
3. **能力可视**：动态展示技能加载/调用状态，提供异常诊断与自愈引导（通过HTTP API查询状态）
4. **资源感知**：实时监控Token水位、本地系统资源，支持精细化资源管理（通过HTTP API轮询）
5. **跨平台一致**：兼容Windows/macOS/Linux，保证各平台交互体验无差异
6. **工程化高效**：基于Vue3组件化、Vite构建、TypeScript类型安全，提升开发与维护效率
7. **架构解耦**：桌面端专注UI展示与用户交互，后端服务处理所有业务逻辑，通过HTTP/SSE通信

### V2.1架构变更说明

**删除的模块**（V1.3 → V2.1）：
- ❌ checkpointManager.ts（断点管理改用后端API）
- ❌ skillManager.ts（技能管理改用后端API）
- ❌ dbManager.ts（数据持久化改用后端统一管理）
- ❌ resourceManager.ts（资源监控改用后端HTTP API）
- ❌ wsClient.ts（WebSocket客户端，改用SSE流式响应）
- ❌ better-sqlite3依赖（不再需要本地SQLite）

**新增的模块**（V2.1）：
- ✅ apiClient.ts（HTTP客户端，调用后端RESTful API，支持SSE流式响应）
- ✅ types.ts（统一的数据类型定义，与后端保持一致）
- ✅ fileManager.ts（文件操作模块，处理本地文件选择和打开）

**保留的模块**（V1.3 → V2.1）：
- ✅ windowManager.ts（窗口管理，系统级操作）
- ✅ 所有Vue3组件（UI展示与交互）
- ✅ Pinia状态管理（前端状态缓存）
- ✅ IPC通信（主线程/渲染进程通信）

---

## 二、技术选型与基础配置（V2.1 纯客户端架构）
|模块|选型/配置|核心说明|跨平台支持|V2.1 核心价值|
|---|---|---|---|---|
|主框架|Electron ^28.0.0 + Vue3 ^3.3.0|Electron实现跨平台窗口/系统集成，Vue3（Composition API）实现组件化UI开发|Windows/macOS/Linux|替代PySide6，依托前端生态实现灵活UI定制，降低跨平台适配成本|
|分层架构|Electron主渲染分离 + Vue3组件化 + Pinia状态管理|主线程处理系统级操作，渲染进程处理UI交互，Pinia管理前端状态缓存|全平台|解耦UI与业务逻辑，替代原MVVM，提升代码可维护性与复用性|
|后端通信|HTTP Client（axios ^1.6.0）+ SSE（Fetch API）|通过HTTP调用后端RESTful API，通过SSE接收后端流式推送|全平台|实现前后端彻底解耦，后端处理所有业务逻辑|
|系统集成|electron-tray + electron-window-state|自定义系统托盘、无边框窗口、贴边隐藏/恢复|全平台|替代QSystemTrayIcon，适配各平台系统特性（如macOS托盘图标、Windows贴边）|
|样式定制|SCSS + Element Plus ^2.4.0 + CSS3|Element Plus提供基础UI组件，SCSS实现样式统一，CSS3实现动画/可视化效果|全平台|替代QSS，样式定制更灵活，视觉效果更丰富|
|数据缓存|localforage（渲染进程）|轻量配置缓存，会话临时状态存储|全平台|替代原SQLite+JSON，前端仅做缓存，数据源统一来自后端|
|拖拽交互|HTML5原生拖拽API + vue-draggable-next|实现文件拖拽上传、技能卡片拖拽安装，带类型/大小安全校验|全平台|替代Qt原生拖拽，交互更流畅，适配前端操作习惯|
|富文本渲染|vue3-quill + 自定义折叠渲染器|支持消息富文本展示，实现思维链折叠/展开、Diff视图、错误快照|全平台|替代QTextDocument，富文本能力更强，定制成本更低|
|状态同步|Pinia + mitt事件总线|前端状态统一管理，跨组件轻量事件通信，后端数据通过SSE实时同步|全平台|替代Qt自定义信号协议，实现响应式状态更新，开发更高效|
|HTTP客户端|axios ^1.6.0|调用后端RESTful API，支持请求拦截、响应拦截、错误处理|全平台|新增V2.1模块，实现与后端服务的HTTP通信|
|SSE流式响应|Fetch API + ReadableStream|连接后端SSE服务，接收实时事件推送（思维链、步骤状态、任务状态、思考流、计划等）|全平台|新增V2.1模块，实现与后端服务的实时通信，替代WebSocket|
|构建工具|Vite ^5.0.0 + electron-builder|Vite实现热更新/快速构建，electron-builder实现跨平台打包|全平台|替代PySide6打包工具，打包速度更快，安装包体积更优|
|类型安全|TypeScript ^5.2.0|全项目类型定义，与后端数据模型保持一致，避免类型错误|全平台|解决原PySide6无强类型校验问题，前后端类型对齐|

### 1.3 工程化基础配置
- **代码规范**：ESLint + Prettier，统一代码风格
- **包管理**：pnpm，提升依赖安装速度，减小项目体积
- **预加载脚本**：preload.js，实现主线程/渲染进程安全通信，避免Electron安全风险
- **路由管理**：Vue Router（轻量），实现弹窗/面板的路由化管理
- **图标库**：Element Plus Icons + 自定义SVG，统一图标风格

---

## 三、界面结构与尺寸规范（V1.3 继承+适配）
完全保留V1.2+的界面区域定义、尺寸规范与布局结构，仅对技术实现做适配，确保用户视觉与交互体验无感知变更。

### 3.1 核心区域定义（与V1.2+完全一致）
|区域|标准尺寸|隐藏态尺寸|核心属性|职责|
|---|---|---|---|---|
|主窗口|1200×900px（默认）|30×30px（贴边气泡）|可全屏、可贴边隐藏、最小尺寸 800×600px|承载所有界面组件，核心功能交互载体|
|贴边窄边|-|30×30px|圆形气泡（border-radius: 15px），鼠标悬停展开|窗口贴边隐藏时的交互入口|
|标题栏|随窗口宽自适应，固定高度 30px|-|拖拽区域，含最小化/设置按钮，无关闭按钮|窗口拖拽、核心功能快捷入口|
|历史对话栏|最小 150px，默认 200px|-|垂直列表，支持滚动、搜索、重命名/删除，新增断点标识|会话管理、历史上下文快速切换、断点恢复|
|聊天核心区|自适应（剩余宽度），最小 200px|-|分上下文水位线、消息展示区、输入区，支持思维链折叠|与 Agent 核心交互载体，透明化展示思考过程|
|技能与工作区|最小 150px，默认 200px|-|Tab 切换模式：技能中心/文件工作区|技能管理、本地工作区管理、文件联动交互|

### 3.2 新增区域定义（与V1.2+完全一致）
保留上下文水位线、模型路由提示条、思维链折叠面板、任务恢复提示条等10大新增区域，技术实现为Vue3独立组件，通过组件化实现复用与解耦。

### 3.3 布局结构（V1.3 组件化重构）
基于Vue3组件化重构布局，采用**根组件+子组件+弹窗组件**的层级结构，替代原Qt的窗口嵌套，所有区域均为可复用Vue组件：
```
主应用（App.vue，Electron渲染进程根组件）
├── 自定义标题栏（TitleBar.vue，全局组件）
├── 任务恢复提示条（ResumeBanner.vue，全局组件，默认隐藏）
├── 贴边气泡组件（EdgeWidget.vue，全局组件，贴边时显示）
└── 中心布局容器（LayoutContainer.vue）
    ├── 水平拆分器（Splitter.vue，基于Element Plus改造）
    │   ├── 历史对话栏（HistoryChat.vue，独立组件）
    │   ├── 聊天核心区（ChatCore.vue，核心组件，包含子组件）
    │   │   ├── 上下文水位线（ContextBar.vue）
    │   │   ├── 消息流展示区（MessageList.vue，含虚拟列表）
    │   │   │   ├── 消息项（MessageItem.vue）
    │   │   │   ├── 思维链折叠面板（ThoughtChainPanel.vue）
    │   │   │   └── 步骤干预卡片（StepInterventionCard.vue）
    │   │   ├── 模型路由提示条（ModelRouteBar.vue）
    │   │   └── 输入区（InputArea.vue）
    │   └── 技能与工作区（SkillWorkspace.vue，独立组件）
    │       ├── 技能中心（SkillCenter.vue）
    │       └── 文件工作区（FileWorkspace.vue）
└── 全局弹窗组件（通过Vue Router/组件挂载实现，默认隐藏）
    ├── 多断点管理面板（MultiCheckpointPanel.vue）
    ├── 技能诊断弹窗（SkillDiagnosticDialog.vue）
    ├── 压缩预览弹窗（CompressionPreviewDialog.vue）
    ├── Token构成分析弹窗（TokenAnalysisDialog.vue）
    ├── 断点差异对比弹窗（CheckpointDiffDialog.vue）
    ├── 资源监控弹窗（ResourceMonitorDialog.vue）
    └── 设置弹窗（SettingsDialog.vue）
```

---

## 四、核心组件详细设计（V2.1 纯客户端架构）
所有组件基于**Vue3 + TypeScript**开发，采用**Composition API**实现逻辑封装，**Props/Emits**实现组件通信，**Pinia**实现前端状态管理，**HTTP/SSE**实现与后端服务的通信。

### 4.1 主线程核心模块（Electron Main Process）
负责**系统级操作**，与渲染进程解耦，通过IPC提供原子化API，不处理任何业务逻辑，业务逻辑全部由后端服务处理。

#### 4.1.1 窗口管理模块（windowManager.ts）
- **核心功能**：创建无边框窗口、贴边隐藏/恢复（300ms防抖+动画）、窗口尺寸约束、关闭事件拦截（最小化到托盘）、跨平台窗口行为适配
- **核心API**：通过IPC暴露`window:minimize`/`window:toggle`/`window:edge-check`等方法，监听渲染进程事件并执行窗口操作
- **跨平台适配**：区分Windows/macOS贴边逻辑、托盘点击行为、窗口拖拽区域差异

#### 4.1.2 HTTP客户端模块（apiClient.ts）⭐ V2.1 更新
- **核心功能**：封装axios HTTP客户端，调用后端RESTful API，支持请求拦截、响应拦截、错误处理、自动重试，支持SSE流式响应
- **核心API**（与后端API接口设计文档V4.0完全对齐）：
  ```typescript
  // 统一响应格式
  interface ApiResponse<T> {
    code: number;
    message: string;
    data: T;
    error?: {
      error_code: string;
      error_detail: string;
    };
  }

  // 会话管理
  getSessions(params?: {
    page?: number;
    page_size?: number;
    user_name?: string;
    sort_by?: string;
    order?: string;
  }): Promise<ApiResponse<{total: number; page: number; page_size: number; sessions: Session[]}>>;

  getSession(sessionId: string): Promise<ApiResponse<SessionDetail>>;

  getSessionHistory(sessionId: string, params?: {
    max_turns?: number;
    include_steps?: boolean;
    task_status?: string;
  }): Promise<ApiResponse<{session_id: string; total_turns: number; history: HistoryItem[]}>>;

  createSession(data: {
    user_name?: string;
    title?: string;
  }): Promise<ApiResponse<Session>>;

  deleteSession(sessionId: string): Promise<ApiResponse<{success: boolean; deleted_tasks_count: number; deleted_steps_count: number}>>;

  // 任务执行
  executeTask(data: {
    task: string;
    session_id: string;
    model_override?: string | null;
  }): Promise<ApiResponse<ExecutionResult>>;

  getTaskStatus(taskId: string): Promise<ApiResponse<ExecutionStatus>>;

  retryTask(taskId: string, data?: {
    step_index?: number;
    user_input?: string | null;
  }): Promise<ApiResponse<{success: boolean; message: string; execution_id: string; retry_from_step: number}>>;

  cancelTask(taskId: string): Promise<ApiResponse<{success: boolean; message: string; cancelled_at: number}>>;

  // 流式任务执行（返回ReadableStream，支持SSE）
  executeTaskStream(data: {
    task: string;
    session_id: string;
    model_override?: string | null;
    enable_heartbeat?: boolean;
    heartbeat_interval?: number;
  }): Promise<Response>;

  // 断点管理
  getCheckpoints(params?: {
    status?: string;
    page?: number;
    page_size?: number;
  }): Promise<ApiResponse<{total: number; checkpoints: Checkpoint[]}>>;

  resumeCheckpoint(taskId: string): Promise<ApiResponse<{execution_id: string; task: string; status: string; message: string; resumed_from_step: number}>>;

  deleteCheckpoint(taskId: string): Promise<ApiResponse<{success: boolean; deleted_steps_count: number}>>;

  // 技能管理
  getSkills(params?: {
    status?: string;
    page?: number;
    page_size?: number;
    keyword?: string;
  }): Promise<ApiResponse<{total: number; skills: Skill[]}>>;

  installSkill(data: {
    skill_data: SkillManifest;
    skill_files: Record<string, string>;
    auto_fix?: boolean;
  }): Promise<ApiResponse<{skill_id: string; status: string; message: string; installed_at: string}>>;

  diagnoseSkill(skillId: string): Promise<ApiResponse<DiagnosticResult>>;

  reloadSkill(skillId: string): Promise<ApiResponse<{success: boolean; message: string; reloaded_at: string}>>;

  // 资源监控
  getResourceUsage(): Promise<ApiResponse<ResourceUsage>>;

  // 配置管理
  getConfig(): Promise<ApiResponse<Config>>;

  updateConfig(config: Partial<Config>): Promise<ApiResponse<{success: boolean; message: string; updated_at: string}>>;
  ```
- **错误处理**：统一错误处理，自动重试（默认3次），超时控制（默认30s），错误日志记录
- **重试策略**：指数退避重试（2^n秒），仅对5xx错误和429（限流）错误重试
- **流式响应处理**：`executeTaskStream`方法返回Fetch API的Response对象，支持Server-Sent Events（SSE）流式读取

#### 4.1.3 SSE流式响应处理模块（sseClient.ts）⭐ V2.1 新增
- **核心功能**：封装SSE流式响应处理，通过Fetch API的ReadableStream读取后端SSE事件流，解析事件并分发到渲染进程
- **核心API**：
  ```typescript
  // SSE流式响应处理
  async executeTaskStream(data: {
    task: string;
    session_id: string;
    model_override?: string | null;
    enable_heartbeat?: boolean;
    heartbeat_interval?: number;
  }, callbacks: {
    onTaskStart?: (data: {execution_id: string; task: string; task_level: string; model: string}) => void;
    onPlanStart?: (data: {execution_id: string; task_id: string}) => void;
    onThinkStart?: (data: {execution_id: string; task_id: string; step_id: string; content: string}) => void;
    onThinkStream?: (data: {execution_id: string; task_id: string; step_id: string; content: string}) => void;
    onThinkFinal?: (data: {execution_id: string; task_id: string; step_id: string; thought: string}) => void;
    onPlanFinal?: (data: {execution_id: string; task_id: string; plan: any[]}) => void;
    onStepStart?: (data: {execution_id: string; task_id: string; step_id: string; step_index: number; description: string}) => void;
    onStepEnd?: (data: {execution_id: string; task_id: string; step_id: string; step_index: number; result: any; status: string}) => void;
    onTaskEnd?: (data: {execution_id: string; task_id: string; result: any; status: string}) => void;
    onTaskFailed?: (data: {execution_id: string; task_id: string; error: string; error_code: string; traceback?: string; recoverable?: boolean}) => void;
    onPing?: (data: {timestamp: number}) => void;
    onStreamEnd?: () => void;
    onError?: (error: Error) => void;
  }): Promise<void>;

  // 取消流式响应
  abort(): void;
  ```
- **SSE事件解析**：解析SSE格式的数据流（`data: {...}`），提取`event_type`和`data`字段
- **心跳处理**：处理`ping`事件和`heartbeat`注释，保持连接活跃
- **错误处理**：捕获流式响应过程中的错误，通过`onError`回调通知渲染进程
- **取消机制**：支持通过`AbortController`取消流式响应

#### 4.1.4 文件操作模块（fileManager.ts）
- **核心功能**：处理本地文件操作（选择文件、选择目录、保存文件、打开资源管理器、打开外部链接），通过IPC暴露给渲染进程，避免渲染进程直接操作文件系统
- **核心API**：
  ```typescript
  selectFile(filters?: FileFilter[]): Promise<string | null>;
  selectDirectory(): Promise<string | null>;
  selectFiles(filters?: FileFilter[]): Promise<string[]>;
  saveFile(defaultPath?: string, filters?: FileFilter[]): Promise<string | null>;
  openInExplorer(filePath: string): Promise<void>;
  openExternal(url: string): Promise<void>;
  ```
- **安全校验**：文件类型校验、文件大小校验（默认100MB）、路径安全校验，避免恶意文件操作
- **文件验证**：
    - `validateFilePath(filePath: string): boolean` - 验证文件路径安全性（防止路径遍历攻击）
    - `validateFileSize(filePath: string, maxSize?: number): boolean` - 验证文件大小限制

#### 4.1.5 IPC通道定义 ⭐ V2.1 更新
主线程通过IPC（进程间通信）向渲染进程暴露API，所有IPC通道定义如下（与后端API完全对齐）：

**窗口管理通道**：
- `window:minimize` - 最小化窗口到贴边
- `window:toggle` - 切换窗口显示/隐藏
- `window:maximize` - 最大化/还原窗口
- `window:edge-check` - 检查窗口是否在边缘位置
- `window:is-maximized` - 检查窗口是否最大化

**文件操作通道**：
- `file:select` - 选择单个文件
- `file:select-directory` - 选择目录
- `file:select-files` - 选择多个文件
- `file:save` - 保存文件
- `file:open-explorer` - 在资源管理器中打开文件

**HTTP API通道**（与后端RESTful API完全对齐）：
- `api:get-sessions` - 获取会话列表
- `api:get-session` - 获取会话详情
- `api:get-session-history` - 获取会话历史
- `api:create-session` - 创建新会话
- `api:delete-session` - 删除会话
- `api:execute-task` - 执行任务（异步）
- `api:execute-task-stream` - 执行任务（SSE流式响应）
- `api:get-task-status` - 获取任务状态
- `api:retry-task` - 重试任务
- `api:cancel-task` - 取消任务
- `api:get-checkpoints` - 获取断点列表
- `api:resume-checkpoint` - 恢复断点
- `api:delete-checkpoint` - 删除断点
- `api:get-skills` - 获取技能列表
- `api:install-skill` - 安装技能
- `api:diagnose-skill` - 诊断技能
- `api:reload-skill` - 重新加载技能
- `api:get-resource-usage` - 获取资源使用情况
- `api:get-config` - 获取配置
- `api:update-config` - 更新配置

**SSE事件推送（主线程→渲染进程）**（与后端SSE事件类型完全对齐）：
- `sse:task-start` - 任务开始
- `sse:plan-start` - 计划开始
- `sse:think-start` - 思考开始
- `sse:think-stream` - 思考流式输出
- `sse:think-final` - 思考完成
- `sse:plan-final` - 计划完成
- `sse:step-start` - 步骤开始
- `sse:step-end` - 步骤结束
- `sse:task-end` - 任务结束
- `sse:task-failed` - 任务失败
- `sse:ping` - 心跳事件
- `sse:stream-end` - 流结束
- `sse:error` - SSE错误

### 4.2 渲染进程核心组件（Electron Renderer Process）
所有组件为**Vue3 单文件组件（SFC）**，遵循**单一职责原则**，通过Props/Emits实现父子组件通信，通过Pinia实现前端状态管理，通过`window.electronAPI`调用主线程IPC方法（HTTP/SSE）。

#### 4.2.1 主窗口根组件（App.vue）
- **核心职责**：作为渲染进程根容器，挂载所有全局组件（标题栏、贴边气泡、任务恢复提示条），实现布局容器的初始化
- **生命周期**：挂载时通过HTTP API初始化全局状态（活跃断点、Token使用、资源状态），启动资源监控定时器（通过HTTP API轮询）
- **连接管理**：监听SSE事件，通过Pinia更新状态，实时展示任务执行进度

#### 4.2.2 贴边气泡组件（EdgeWidget.vue）
- **核心特性**：30×30px圆形气泡，背景色`#409eff`，显示Agent图标，气泡上展示资源占用指示灯（CPU/内存过高变红）
- **交互逻辑**：鼠标悬停/点击触发主窗口展开，展开后自动隐藏气泡，基于CSS3实现淡入淡出动画
- **实现方式**：通过定时器轮询HTTP API `getResourceUsage()`，更新资源占用指示灯状态

#### 4.2.3 自定义标题栏（TitleBar.vue）
- **核心特性**：水平布局（拖拽区80% + 功能区20%），仅含**最小化**/**设置**按钮，无关闭按钮，支持窗口拖拽
- **交互逻辑**：最小化按钮触发窗口贴边隐藏，设置按钮打开设置弹窗，配置需要重启时设置按钮显示红点提示
- **拖拽实现**：通过CSS`user-select: none`+Electron`webContents.setIgnoreMouseEvents`实现拖拽区域识别

---

## 五、TypeScript类型定义（V2.1 更新）⭐
所有类型定义与后端API接口设计文档V4.0完全对齐，确保前后端数据模型一致性。

### 5.1 基础类型
```typescript
// 统一响应格式
interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
  error?: {
    error_code: string;
    error_detail: string;
  };
}

// 时间戳类型
type Timestamp = number;
type DateTime = string; // ISO 8601格式

// UUID类型
type UUID = string;
```

### 5.2 会话相关类型
```typescript
interface Session {
  session_id: UUID;
  user_name: string;
  title: string;
  current_task_id: UUID | null;
  total_tokens: number;
  created_at: DateTime;
  updated_at: DateTime;
}

interface SessionDetail extends Session {
  current_task?: TaskSummary;
}

interface TaskSummary {
  task_id: UUID;
  task_type: 'simple' | 'complex' | 'trivial';
  user_input: string;
  status: 'running' | 'completed' | 'failed' | 'paused';
  current_step_idx: number;
  total_steps: number;
  created_at: DateTime;
}

interface HistoryItem {
  task_id: UUID;
  role: 'user' | 'assistant';
  content: string;
  task_type: 'simple' | 'complex' | 'trivial';
  status: string;
  timestamp: Timestamp;
  steps?: Step[];
}
```

### 5.3 任务相关类型
```typescript
interface ExecutionResult {
  execution_id: UUID;
  task: string;
  task_level: 'trivial' | 'simple' | 'complex';
  model: string;
  status: 'running' | 'queued' | 'completed' | 'failed';
  estimated_duration: number;
  created_at: Timestamp;
}

interface ExecutionStatus {
  execution_id: UUID;
  task: string;
  task_level: 'trivial' | 'simple' | 'complex';
  model: string;
  status: 'running' | 'completed' | 'failed' | 'paused' | 'cancelled';
  current_step: number;
  total_steps: number;
  progress: number;
  result?: {
    content: string;
    thought_chain: any[];
    steps: any[];
  };
  error?: {
    error: string;
    error_code: string;
    traceback: string;
  };
  input_tokens: number;
  output_tokens: number;
  created_at: Timestamp;
  updated_at: Timestamp;
}

interface Step {
  step_id: UUID;
  step_index: number;
  step_type: 'thinking' | 'action';
  description: string;
  thought: string;
  result: string;
  skill_call: string | null;
  status: 'completed' | 'failed' | 'running';
  created_at: DateTime;
}
```

### 5.4 断点相关类型
```typescript
interface Checkpoint {
  session_id: UUID;
  task_id: UUID;
  task: string;
  task_level: 'simple' | 'complex';
  current_step: number;
  total_steps: number;
  execution_status: 'paused' | 'running';
  paused_reason: 'user_request' | 'error' | 'timeout';
  created_at: DateTime;
  updated_at: DateTime;
}
```

### 5.5 技能相关类型
```typescript
interface Skill {
  skill_id: string;
  name: string;
  description: string;
  version: string;
  author: string;
  status: 'available' | 'error' | 'installed';
  manifest: SkillManifest;
  installed_at?: DateTime;
}

interface SkillManifest {
  name: string;
  version: string;
  description: string;
  author: string;
  dependencies?: string[];
  entry_point: string;
}

interface DiagnosticResult {
  skill_id: string;
  status: 'error' | 'healthy';
  diagnostic_result: {
    error_type: 'missing_dependency' | 'invalid_manifest' | 'runtime_error';
    error_message: string;
    fix_suggestion: string;
    can_auto_fix: boolean;
    dependencies?: Dependency[];
  };
}

interface Dependency {
  name: string;
  required: string;
  installed: boolean;
}
```

### 5.6 资源相关类型
```typescript
interface ResourceUsage {
  system: {
    cpu_percent: number;
    memory_percent: number;
    disk_percent: number;
  };
  token_usage: {
    current: number;
    limit: number;
    percent: number;
    daily_limit: number;
    daily_used: number;
  };
  tasks: {
    running: number;
    queued: number;
    completed_today: number;
  };
  skills: {
    total: number;
    available: number;
    error: number;
  };
}
```

### 5.7 配置相关类型
```typescript
interface Config {
  llm: {
    model: string;
    api_key: string;
    base_url: string;
    timeout: number;
    max_retries: number;
  };
  execution: {
    max_steps: number;
    max_replan_count: number;
    enable_streaming: boolean;
  };
  storage: {
    db_path: string;
    enable_checkpoint: boolean;
  };
  logging: {
    level: string;
    log_file: string;
  };
}
```

### 5.8 文件相关类型
```typescript
interface FileFilter {
  name: string;
  extensions: string[];
}
```

### 5.9 SSE事件类型（与后端SSE事件完全对齐）
```typescript
// 任务开始
interface TaskStartEvent {
  event_type: 'task_start';
  data: {
    execution_id: UUID;
    task: string;
    task_level: 'trivial' | 'simple' | 'complex';
    model: string;
  };
}

// 计划开始
interface PlanStartEvent {
  event_type: 'plan_start';
  data: {
    execution_id: UUID;
    task_id: UUID;
  };
}

// 思考开始
interface ThinkStartEvent {
  event_type: 'think_start';
  data: {
    execution_id: UUID;
    task_id: UUID;
    step_id: UUID;
    content: string;
  };
}

// 思考流式输出
interface ThinkStreamEvent {
  event_type: 'think_stream';
  data: {
    execution_id: UUID;
    task_id: UUID;
    step_id: UUID;
    content: string;
  };
}

// 思考完成
interface ThinkFinalEvent {
  event_type: 'think_final';
  data: {
    execution_id: UUID;
    task_id: UUID;
    step_id: UUID;
    thought: string;
  };
}

// 计划完成
interface PlanFinalEvent {
  event_type: 'plan_final';
  data: {
    execution_id: UUID;
    task_id: UUID;
    plan: any[];
  };
}

// 步骤开始
interface StepStartEvent {
  event_type: 'step_start';
  data: {
    execution_id: UUID;
    task_id: UUID;
    step_id: UUID;
    step_index: number;
    description: string;
  };
}

// 步骤结束
interface StepEndEvent {
  event_type: 'step_end';
  data: {
    execution_id: UUID;
    task_id: UUID;
    step_id: UUID;
    step_index: number;
    result: any;
    status: string;
  };
}

// 任务结束
interface TaskEndEvent {
  event_type: 'task_end';
  data: {
    execution_id: UUID;
    task_id: UUID;
    result: any;
    status: string;
  };
}

// 任务失败
interface TaskFailedEvent {
  event_type: 'task_failed';
  data: {
    execution_id: UUID;
    task_id: UUID;
    error: string;
    error_code: string;
    traceback?: string;
    recoverable?: boolean;
  };
}

// 心跳事件
interface PingEvent {
  event_type: 'ping';
  data: {
    timestamp: number;
  };
}

// 流结束
interface StreamEndEvent {
  event_type: 'stream_end';
  data: {};
}

// 联合类型
type SSEEvent =
  | TaskStartEvent
  | PlanStartEvent
  | ThinkStartEvent
  | ThinkStreamEvent
  | ThinkFinalEvent
  | PlanFinalEvent
  | StepStartEvent
  | StepEndEvent
  | TaskEndEvent
  | TaskFailedEvent
  | PingEvent
  | StreamEndEvent;
```

### 5.10 错误码类型（与后端错误码定义完全对齐）
```typescript
// 通用错误码
type CommonErrorCode =
  | 'INVALID_PARAMETER'
  | 'RESOURCE_NOT_FOUND'
  | 'INTERNAL_ERROR'
  | 'UNAUTHORIZED';

// 任务执行错误码
type TaskErrorCode =
  | 'LLM_RATE_LIMIT'
  | 'LLM_TIMEOUT'
  | 'SKILL_EXECUTION'
  | 'DATABASE_LOCKED'
  | 'TASK_CANCELLED'
  | 'UNKNOWN';

// 技能管理错误码
type SkillErrorCode =
  | 'SKILL_NOT_FOUND'
  | 'SKILL_ALREADY_INSTALLED'
  | 'MISSING_DEPENDENCY'
  | 'INVALID_MANIFEST';

// 所有错误码
type ErrorCode = CommonErrorCode | TaskErrorCode | SkillErrorCode;
```

---

## 六、核心业务逻辑与交互流程（V2.1 纯客户端架构）
完全保留V1.3的所有核心业务逻辑与交互流程，仅将技术实现从主线程业务逻辑调整为HTTP/SSE与后端服务通信，以下为核心流程的技术适配说明：

### 6.1 复杂任务执行流（含模型路由可视化）
1. 渲染进程：用户输入复杂指令，点击发送，通过HTTP API `executeTaskStream()` 发送任务至后端（使用SSE流式响应）
2. 后端服务：接收任务，进行任务分析→计划生成→模型路由决策，通过SSE推送**task_start**/**plan_start**/**think_start**/**think_stream**/**think_final**/**plan_final**事件
3. 主线程：接收SSE事件流，解析事件并通过IPC转发至渲染进程
4. 渲染进程：Pinia接收状态更新，UI展示模型路由提示条（含决策依据、成本预估），创建思维链折叠面板占位符
5. 后端服务：分步执行任务，每步执行状态通过SSE推送**step_start**/**step_end**事件
6. 渲染进程：流式更新思维链折叠面板的步骤状态，实现思考过程的实时可视化
7. 可选操作：用户可在渲染进程手动覆盖模型路由，通过HTTP API `executeTaskStream()` 重新执行任务（带`model_override`参数）

### 6.2 多断点恢复流程（V1.2+增强）
1. 应用启动：渲染进程通过HTTP API `getCheckpoints()` 获取活跃断点列表
2. 渲染进程：若存在活跃断点，显示**任务恢复提示条**（多断点显示"检测到N个未完成任务"）
3. 交互操作：
   - 点击**继续最近一个**：渲染进程通过HTTP API `resumeCheckpoint()` 调用后端恢复断点，后端检查环境差异，无差异则直接恢复，有差异则返回差异信息，渲染进程弹出**断点差异对比弹窗**
   - 点击**查看全部**：渲染进程打开**多断点管理面板**，展示所有活跃断点（含有效期、模型、中断步骤），用户选择断点后执行恢复流程
4. 断点恢复：后端从断点处继续执行任务，执行状态通过SSE推送**step_start**/**step_end**事件，渲染进程实时更新UI

### 6.3 技能异常自愈流程（V1.2+新增）
1. 后端服务：技能加载/调用失败时，自动诊断异常原因，通过SSE推送**task_failed**事件（含错误信息和错误码）
2. 渲染进程：技能中心对应卡片变为红色异常状态，用户点击卡片后通过HTTP API `diagnoseSkill()` 获取详细诊断结果，打开**技能诊断弹窗**，展示异常原因与修复建议
3. 修复操作：用户点击**一键修复**（如填写API Key/升级依赖/重新加载），渲染进程通过HTTP API `reloadSkill()` 调用后端执行修复
4. 状态同步：后端执行修复操作后，通过HTTP API `getSkills()` 获取最新技能状态，渲染进程卡片恢复为可用状态，若修复失败则推送新的诊断信息

### 6.4 智能修正与步骤干预流程（V1.2+新增）
1. 后端服务：步骤执行失败时，调用LLM生成智能修正建议，通过SSE推送**task_failed**事件（含错误信息和错误码）
2. 渲染进程：在思维链折叠面板中嵌入**步骤干预卡片**，展示错误现场快照、智能修正建议
3. 干预操作：用户选择**重试/跳过/人工输入/批量重试**，渲染进程通过HTTP API `retryTask()` 调用后端
4. 执行反馈：后端执行干预操作后，通过SSE推送**step_start**/**step_end**事件，渲染进程更新UI，批量重试模式下后续类似错误自动重试

### 6.5 资源监控流程（V2.1 更新）
1. 应用启动：渲染进程启动资源监控定时器（默认每30秒轮询一次）
2. 定时轮询：渲染进程通过HTTP API `getResourceUsage()` 获取最新资源使用情况
3. 状态更新：Pinia接收资源数据更新，UI展示CPU、内存、磁盘占用，Token使用情况
4. 动态调整：根据资源占用情况动态调整定时器频率（资源紧张时提高频率，资源充足时降低频率）

---

## 七、工程化规范与安全（V1.3 新增+强化）
在V1.2+工程化规范的基础上，结合Electron+Vue3的技术特性，新增前端工程化规范，强化跨平台安全与兼容性。

### 7.1 性能优化
1. **虚拟列表渲染**：消息列表、会话列表、技能列表均采用虚拟列表（vue-virtual-scroller），仅渲染可视区域内的DOM，支持万级数据无卡顿
2. **自适应节流**：主线程对高频事件（步骤进度、资源监控）做节流处理，避免渲染进程频繁接收事件导致的UI卡顿
3. **组件懒加载**：所有弹窗组件、非核心子组件均采用Vue3异步组件+Vite代码分割，实现按需加载，减小初始包体积与渲染时间
4. **懒渲染**：思维链折叠面板、步骤详情、错误快照等内容，仅在用户展开时才渲染，减少初始渲染DOM数量
5. **内存管理**：主线程定期清理无用断点/会话数据，渲染进程弹窗关闭后销毁组件，解绑IPC监听，避免内存泄漏

### 7.2 数据安全与跨平台安全
1. **IPC通信安全**：通过预加载脚本实现主线程/渲染进程的安全隔离，渲染进程仅能访问暴露的API，无法直接操作系统资源
2. **敏感信息脱敏**：思维链、错误快照中若包含API Key、密码等敏感信息，主线程处理时自动脱敏（替换为***）后再推送至渲染进程
3. **文件操作安全**：渲染进程不直接操作本地文件，所有文件IO均通过IPC调用主线程实现，主线程做类型/大小/路径校验，避免恶意文件操作
4. **高风险操作二次确认**：技能安装、断点删除、配置修改等高风险操作，渲染进程均做二次确认，避免误操作
5. **跨平台权限适配**：区分Windows/macOS/Linux的文件系统权限、托盘权限、窗口权限，主线程做权限检测，无权限时给出明确提示

### 7.3 兼容性
1. **旧版本数据迁移**：支持V1.2+（PySide6）的SQLite数据库与配置文件，应用启动时自动检测并迁移，保证用户数据不丢失
2. **配置版本管理**：所有配置项均有版本标识，支持配置回滚到历史版本，配置修改时做兼容性检测，避免配置错误导致应用崩溃
3. **跨平台样式兼容**：使用CSS3变量与SCSS混合器，适配不同平台的样式差异（如字体、间距、圆角），保证视觉体验一致
4. **Electron版本兼容**：基于Electron 28.0.0开发，兼容各平台的Electron最低版本要求，避免平台不支持导致的启动失败

### 7.4 异常处理闭环（V1.2+全保留+强化）
完全保留V1.2+的异常处理闭环能力，结合Electron+Vue3的技术特性，强化异常捕获与反馈：
1. **技能异常自愈**：自动诊断+一键修复+状态同步，修复失败时给出明确的错误信息
2. **步骤失败智能干预**：错误快照+智能修正+批量重试，降低用户干预门槛
3. **断点恢复环境检查**：恢复前自动检查环境差异，弹出Diff视图，避免环境不一致导致的恢复失败
4. **全局异常捕获**：渲染进程通过Vue3错误边界捕获组件异常，主线程通过process.on捕获全局异常，异常发生时弹出友好的错误提示，记录错误日志，支持用户导出日志反馈
5. **启动异常处理**：应用启动失败时（如数据库损坏/配置错误），弹出修复提示，支持一键修复或重置应用

### 7.5 前端工程化规范
1. **代码规范**：遵循ESLint Vue3规范+Prettier代码格式化，提交代码前通过husky+lint-staged做代码校验，保证代码风格统一
2. **组件规范**：所有Vue组件遵循**单一职责原则**，组件名采用大驼峰命名，组件内逻辑通过Composition API封装，Props/Emits均做类型定义
3. **状态管理规范**：Pinia Store按功能拆分，避免单一Store过大，State仅通过Action修改，不允许组件直接修改State
4. **IPC通信规范**：所有IPC方法与事件均定义TypeScript接口，接口文件统一管理，保证通信数据的类型安全
5. **注释规范**：所有核心方法、组件、Store均添加JSDoc注释，包含功能说明、参数说明、返回值说明，生成自动化API文档

---

## 八、样式规范（V1.3 SCSS+CSS3 重构）
完全保留V1.2+的视觉样式与交互效果，将原QSS样式重构为**SCSS+CSS3**，基于Element Plus的样式变量做统一管理，实现样式的可配置与可复用。

### 8.1 样式分层
1. **基础样式**：定义全局样式重置、CSS3变量、字体、间距、颜色规范，基于Element Plus的主题变量扩展
2. **布局样式**：定义布局容器、拆分器、弹窗、面板的基础样式，实现跨组件的布局统一
3. **组件样式**：每个Vue组件的样式通过SCSS模块化实现（scoped），避免样式污染，组件内样式仅作用于当前组件
4. **跨平台样式**：通过Electron提供的平台信息，定义平台专属的样式变量，适配不同平台的视觉差异

### 8.2 核心样式片段（SCSS）
保留V1.2+的所有核心视觉效果，如思维链折叠面板、技能卡片、上下文水位线、干预卡片等，以下为核心样式示例：
```scss
// 全局CSS3变量
:root {
  --primary-color: #409eff;
  --success-color: #67c23a;
  --warning-color: #e6a23c;
  --danger-color: #f56c6c;
  --light-bg: #f9f9f9;
  --border-color: #e0e0e0;
  --text-color: #333333;
}

// 思维链折叠面板
.thought-chain-panel {
  background-color: var(--light-bg);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  margin-top: 5px;
  padding: 8px;
  .step-status {
    &.success { color: var(--success-color); }
    &.running { color: var(--primary-color); font-weight: bold; }
    &.failed { color: var(--danger-color); }
  }
}

// 上下文水位线
.context-bar {
  height: 4px;
  border-radius: 2px;
  background-color: var(--border-color);
  .progress {
    height: 100%;
    border-radius: 2px;
    transition: width 0.3s ease;
    &.success { background-color: var(--success-color); }
    &.warning { background-color: var(--warning-color); }
    &.danger { background-color: var(--danger-color); }
  }
}

// 技能卡片
.skill-card {
  background-color: #fff;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  transition: all 0.3s ease;
  &:hover { border-color: var(--primary-color); background-color: #ecf5ff; }
  &.active { border-left: 4px solid var(--success-color); }
  &.error { border-left: 4px solid var(--danger-color); }
}

// 步骤干预卡片
.intervention-card {
  background-color: #fef0f0;
  border: 1px solid #fde2e2;
  border-radius: 6px;
  padding: 10px;
  .error-snapshot {
    background-color: #f4f4f5;
    border: 1px solid #e4e7ed;
    border-radius: 4px;
    padding: 8px;
    margin-top: 8px;
  }
}
```

### 8.3 主题定制
基于Element Plus的主题定制能力，支持**浅色/深色主题**切换，通过Pinia管理主题状态，切换主题时实时修改全局CSS3变量，实现全应用主题无缝切换，无需重启应用。

---

## 九、打包与部署（V1.3 全新定义）
基于**Vite + electron-builder**实现跨平台打包，支持Windows（exe/msi）、macOS（dmg/zip）、Linux（deb/rpm/AppImage），打包配置简单，安装包体积小，跨平台部署便捷。

### 9.1 打包配置
1. **Vite配置**：vite.config.ts定义构建入口、输出目录、别名、代码分割，实现Vue3应用的快速构建与优化
2. **electron-builder配置**：electron-builder.json定义应用ID、产品名称、图标、打包格式、文件包含规则，实现跨平台打包
3. **打包脚本**：package.json定义打包脚本，支持**开发环境热更新**/**生产环境打包**/**单平台打包**/**全平台打包**
   ```json
   "scripts": {
     "dev": "vite dev && electron .",
     "build:vue": "vite build",
     "build:win": "electron-builder --win",
     "build:mac": "electron-builder --mac",
     "build:linux": "electron-builder --linux",
     "build:all": "vite build && electron-builder --win --mac --linux"
   }
   ```

### 9.2 部署规范
1. **安装包**：每个平台生成独立的安装包，包含应用图标、安装引导、卸载程序，支持一键安装/卸载
2. **更新机制**：集成electron-updater，支持应用**自动更新**/**手动更新**，更新时下载增量包，减小更新体积
3. **日志管理**：应用运行时自动记录日志，日志文件存储在各平台的应用数据目录，支持用户导出日志反馈问题
4. **部署方式**：支持官网下载、应用商店部署（macOS App Store/Windows微软商店）、开源仓库发布（GitHub/Gitee）

---

## 十、实施验收标准（V1.3 全量继承V1.2+，新增技术层验收）
### 10.1 功能验收（与V1.2+完全一致）
完全继承V1.2+的所有验收标准，包括透明度验证、断点恢复验证、干预有效性、技能联动、资源感知，以及V1.2+新增的模型路由可视化、技能异常自愈、多断点管理、智能干预、资源精细化管理、配置热更新验证，确保功能无缺失。

### 10.2 技术层验收（V1.3 新增）
1. **跨平台一致性**：在Windows10/11、macOS 13+/14+、Ubuntu 20.04+/22.04+上测试，所有功能正常，视觉与交互体验一致
2. **性能验收**：
   - 消息列表支持万级消息无卡顿，思维链折叠/展开流畅
   - 步骤执行时（<50ms/步），UI无卡顿，自适应节流生效
   - 应用启动时间<3s，窗口贴边/展开/拖拽无抖动
3. **兼容性验收**：
   - 能正常迁移V1.2+（PySide6）的用户数据（会话/断点/配置）
   - 配置修改后即时生效/重启生效标识准确，重启后配置正常
   - 应用启动失败时（如数据库损坏），能给出友好的修复提示并实现一键修复
4. **工程化验收**：
   - 代码通过ESLint+Prettier校验，无语法错误与类型错误
   - 所有核心组件/方法/Store均添加JSDoc注释，能生成自动化API文档
   - 应用打包后，安装包体积<200MB，安装后运行无内存泄漏
5. **安全验收**：
   - 渲染进程无法直接访问主线程系统资源，IPC通信安全
   - 敏感信息自动脱敏，文件操作有安全校验，高风险操作有二次确认
   - 应用运行时无权限泄露，跨平台权限适配准确
6. **前后端对齐验收**（V2.1 新增）：
   - 所有HTTP API调用与后端接口定义完全一致
   - 所有SSE事件类型与后端SSE事件定义完全一致
   - 所有TypeScript类型定义与后端数据模型完全一致
   - 所有错误码定义与后端错误码定义完全一致
   - SSE流式响应正确处理心跳事件和连接断开

---

## 十一、评审结论
V1.3版本完成了Lingxi Agent终端助手从PySide6到**Electron+Vue3+TypeScript**的技术栈全面迁移，**完全保留了V1.2+的所有核心功能、交互逻辑与验收标准**，同时解决了原PySide6跨平台适配繁琐、前端生态薄弱、无强类型校验的问题，核心优势如下：
1. **跨平台能力提升**：基于Electron实现Windows/macOS/Linux全平台兼容，视觉与交互体验一致，适配成本大幅降低
2. **开发效率提升**：依托Vue3组件化、Vite热更新、TypeScript类型安全，开发与维护效率提升50%以上
3. **UI定制能力提升**：基于Element Plus+CSS3，UI定制更灵活，视觉效果更丰富，能快速响应产品需求变更
4. **工程化能力提升**：引入前端成熟的工程化规范（ESLint/Prettier/Pinia/IPC），代码可维护性、可复用性、可扩展性大幅提升
5. **性能与安全提升**：通过虚拟列表、自适应节流、组件懒加载优化性能，通过IPC安全通信、敏感信息脱敏、文件操作校验强化安全

V2.0版本在架构层面完成了彻底重构，采用纯客户端模式，通过HTTP/WebSocket与后端服务通信，实现了前后端职责的彻底解耦，解决了V1.3版本中前后端职责重叠、数据不一致、通信缺失等问题，同时完全保留了V1.3的全量交互能力。

V2.1版本根据后端API接口设计文档（V4.0）完成了HTTP客户端、SSE流式响应处理、IPC通道和TypeScript类型定义的全面更新，确保前后端数据模型完全对齐，**移除WebSocket，改用SSE流式响应**，**批准进入开发与测试阶段**，可基于此版本进行跨平台发布与迭代。
