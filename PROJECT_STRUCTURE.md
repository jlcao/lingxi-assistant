# 灵犀智能助手项目结构文档

## 1. 项目概览

灵犀智能助手是一个基于 Plan+ReAct 模式的智能助手系统，包含 Python 后端引擎和 Vue+Electron 桌面前端。系统支持多轮对话、技能调用、工作目录管理等功能。

### 核心功能
- 基于 LLM 的智能对话
- 多轮对话上下文管理
- 技能系统（内置和用户技能）
- 工作目录管理
- 会话历史管理
- 流式响应
- WebSocket 实时通信

## 2. 项目结构

### 2.1 目录结构

```
/
├── lingxi/          # Python 后端项目
│   ├── core/        # 核心引擎模块
│   │   ├── assistant/    # 助手实现
│   │   ├── engine/        # 执行引擎（PlanReAct、ReAct 等）
│   │   ├── session/      # 会话管理
│   │   ├── skills/        # 技能系统
│   │   ├── llm/           # LLM 客户端
│   │   ├── prompts/        # 提示词模板
│   │   ├── memory/        # 记忆系统
│   │   └── event/          # 事件系统
│   ├── web/         # Web 服务和 API
│   ├── management/  # 工作目录管理
│   └── utils/       # 工具函数
├── lingxi-desktop/  # 桌面前端应用
│   ├── electron/    # Electron 主进程
│   ├── src/         # Vue 前端代码
│   └── tests/       # 前端测试目录
├── docs/            # 项目设计文档目录
├── tests/           # 测试目录
└── scripts/         # 脚本文件
```

### 2.2 核心模块说明

| 模块 | 主要职责 | 文件位置 | 关键文件 |
|------|---------|----------|----------|
| 后端服务 | FastAPI 服务器和 WebSocket | lingxi/web/ | fastapi_server.py, websocket.py |
| 助手核心 | 处理用户输入和执行逻辑 | lingxi/core/assistant/ | async_main.py |
| 推理引擎 | Plan+ReAct 推理逻辑 | lingxi/core/engine/ | async_plan_react.py, async_react_core.py |
| 会话管理 | 会话历史和任务管理 | lingxi/core/session/ | session_manager.py, task_manager.py |
| 技能系统 | 技能注册和调用 | lingxi/core/skills/ | skill_system.py, registry.py |
| LLM 客户端 | 与 LLM 服务通信 | lingxi/core/llm/ | async_llm_client.py |
| 前端应用 | 用户界面和交互 | lingxi-desktop/src/ | App.vue, ChatCore.vue |
| 状态管理 | 前端状态管理 | lingxi-desktop/src/stores/ | app.ts, workspace.ts |

## 3. 核心流程

### 3.1 服务启动流程

1. **启动脚本**：`start_web_server.py`
2. **初始化助手**：创建 `AsyncLingxiAssistant` 实例
3. **初始化 WebSocket 管理器**：创建 `WebSocketManager` 实例
4. **启动 FastAPI 服务器**：`run_server()` 函数
5. **注册 API 路由**：包括任务、检查点、技能、配置、会话、工作区等
6. **启动 WebSocket 端点**：`/ws` 路径

### 3.2 请求处理流程

1. **WebSocket 连接**：前端通过 WebSocket 连接后端
2. **消息接收**：`websocket_endpoint` 接收前端消息
3. **消息处理**：`WebSocketManager.handle_message` 处理不同类型的消息
4. **输入处理**：`AsyncLingxiAssistant.process_input` 处理用户输入
5. **任务分析**：`AsyncPlanReActEngine._analyze_task_and_plan` 分析任务并生成计划
6. **计划执行**：`AsyncPlanReActEngine._execute_plan_steps` 执行计划步骤
7. **技能调用**：通过 `SkillCaller` 调用相应技能
8. **结果返回**：通过 WebSocket 流式返回结果

### 3.3 前端交互流程

1. **应用初始化**：`App.vue` 的 `initializeApp` 函数
2. **工作区加载**：加载当前工作区信息
3. **会话列表加载**：加载会话历史
4. **WebSocket 连接**：建立与后端的 WebSocket 连接
5. **消息发送**：用户输入通过 WebSocket 发送到后端
6. **实时响应**：接收后端的流式响应并更新界面
7. **状态更新**：更新会话状态、步骤状态等

## 4. 核心文件详解

### 4.1 后端核心文件

#### start_web_server.py
- **功能**：启动 WebSocket 服务器
- **关键流程**：
  - 加载配置
  - 初始化 `AsyncLingxiAssistant`
  - 初始化 `WebSocketManager`
  - 启动 FastAPI 服务器

#### lingxi/web/fastapi_server.py
- **功能**：FastAPI 服务器实现
- **关键组件**：
  - `app`：FastAPI 应用实例
  - `websocket_endpoint`：WebSocket 端点
  - `run_server`：启动服务器函数
  - API 路由注册

#### lingxi/core/assistant/async_main.py
- **功能**：异步灵犀助手主类
- **关键方法**：
  - `process_input`：异步处理用户输入
  - `stream_process_input`：异步流式处理用户输入
  - `install_skill_async`：异步安装技能

#### lingxi/core/engine/async_plan_react.py
- **功能**：异步 Plan+ReAct 引擎
- **关键方法**：
  - `_analyze_task_and_plan`：分析任务并生成计划
  - `_execute_plan_steps`：执行计划步骤
  - `_execute_task_stream`：执行任务（流式）
  - `process`：处理用户输入

#### lingxi/core/engine/async_react_core.py
- **功能**：异步 ReAct 核心引擎
- **关键方法**：
  - `_build_history_context`：构建历史上下文
  - `_build_initial_messages`：构建初始消息
  - `_execute_task_stream`：执行任务流
  - `_process_llm_response`：处理 LLM 响应

#### lingxi/core/session/session_manager.py
- **功能**：会话管理器
- **关键方法**：
  - `get_history`：获取会话历史
  - `get_session_context`：获取会话上下文
  - `create_session`：创建新会话
  - `save_checkpoint`：保存检查点

### 4.2 前端核心文件

#### lingxi-desktop/src/App.vue
- **功能**：前端主应用
- **关键方法**：
  - `initializeApp`：初始化应用
  - `setupWebSocketListeners`：设置 WebSocket 监听器
  - WebSocket 事件处理（任务开始、结束、思考、步骤等）

#### lingxi-desktop/src/components/ChatCore.vue
- **功能**：聊天核心组件
- **关键功能**：
  - 消息列表显示
  - 输入区域
  - 思考链显示
  - 步骤执行显示

#### lingxi-desktop/src/components/MessageList.vue
- **功能**：消息列表组件
- **关键功能**：
  - 显示用户和助手消息
  - 显示思考过程
  - 显示步骤执行

#### lingxi-desktop/src/components/InputArea.vue
- **功能**：输入区域组件
- **关键功能**：
  - 文本输入
  - 发送消息
  - 思考模式切换

#### lingxi-desktop/src/stores/app.ts
- **功能**：应用状态管理
- **关键状态**：
  - 会话列表
  - 当前会话
  - 消息历史
  - 检查点
  - 资源使用

## 5. 数据模型

### 5.1 后端数据模型

#### 会话（Session）
- **字段**：session_id, user_name, title, current_task_id, total_tokens, created_at, updated_at
- **存储**：SQLite 数据库

#### 任务（Task）
- **字段**：task_id, session_id, task_type, plan, user_input, result, status, current_step_idx, replan_count, error_info, input_tokens, output_tokens, created_at, updated_at
- **存储**：SQLite 数据库

#### 步骤（Step）
- **字段**：step_id, task_id, step_index, description, status, thought, result, created_at, updated_at
- **存储**：SQLite 数据库

### 5.2 前端数据模型

#### 会话（Session）
- **字段**：id, name, createdAt, updatedAt

#### 消息（Turn）
- **字段**：id, role, content, time, timestamp, steps, thought, plan, executionId, status, isStreaming, isThinking

#### 步骤（Step）
- **字段**：step_index, description, status, thought, result

## 6. 前端与后端交互

### 6.1 API 接口

| 路径 | 方法 | 功能 | 模块 |
|------|------|------|------|
| /api/tasks | POST | 创建任务 | lingxi/web/routes/tasks.py |
| /api/tasks/{task_id} | GET | 获取任务 | lingxi/web/routes/tasks.py |
| /api/checkpoints | GET | 获取检查点 | lingxi/web/routes/checkpoints.py |
| /api/skills | GET | 获取技能列表 | lingxi/web/routes/skills.py |
| /api/config | GET | 获取配置 | lingxi/web/routes/config.py |
| /api/sessions | GET | 获取会话列表 | lingxi/web/routes/sessions.py |
| /api/sessions/{session_id} | GET | 获取会话信息 | lingxi/web/routes/sessions.py |
| /api/workspace | GET | 获取工作区信息 | lingxi/web/routes/workspace.py |
| /api/workspace/switch | POST | 切换工作区 | lingxi/web/routes/workspace.py |
| /ws | WebSocket | WebSocket 连接 | lingxi/web/fastapi_server.py |

### 6.2 WebSocket 事件

| 事件类型 | 方向 | 功能 | 处理函数 |
|----------|------|------|----------|
| ws:task-start | 后端→前端 | 任务开始 | onTaskStart |
| ws:task-end | 后端→前端 | 任务结束 | onTaskEnd |
| ws:think-start | 后端→前端 | 思考开始 | onThinkStart |
| ws:think-stream | 后端→前端 | 思考流式输出 | onThinkStream |
| ws:think-final | 后端→前端 | 思考结束 | onThinkFinal |
| ws:plan-start | 后端→前端 | 计划开始 | onPlanStart |
| ws:plan-final | 后端→前端 | 计划结束 | onPlanFinal |
| ws:step-start | 后端→前端 | 步骤开始 | onStepStart |
| ws:step-end | 后端→前端 | 步骤结束 | onStepEnd |
| ws:task-failed | 后端→前端 | 任务失败 | onTaskFailed |
| chat | 前端→后端 | 发送聊天消息 | handle_message |
| stream_chat | 前端→后端 | 发送流式聊天消息 | _handle_stream_chat |

## 7. 技能系统

### 7.1 技能类型

| 类型 | 位置 | 示例 |
|------|------|------|
| 内置技能 | lingxi/skills/builtin/ | search, read_file, create_file |
| 用户技能 | .lingxi/skills/ | docx, pdf, xlsx |

### 7.2 技能调用流程

1. **技能注册**：`SkillRegistry` 注册技能
2. **技能加载**：`SkillLoader` 加载技能模块
3. **技能调用**：`SkillCaller` 调用技能
4. **结果处理**：处理技能执行结果

### 7.3 核心技能

| 技能名称 | 功能 | 模块 |
|----------|------|------|
| search | 搜索网页 | lingxi/skills/builtin/search/ |
| read_file | 读取文件 | lingxi/skills/builtin/read_file/ |
| create_file | 创建文件 | lingxi/skills/builtin/create_file/ |
| modify_file | 修改文件 | lingxi/skills/builtin/modify_file/ |
| delete_file | 删除文件 | lingxi/skills/builtin/delete_file/ |
| execute_command | 执行命令 | lingxi/skills/builtin/execute_command/ |
| fetch_webpage | 获取网页 | lingxi/skills/builtin/fetch_webpage/ |
| batch_read | 批量读取文件 | lingxi/skills/builtin/batch_read/ |
| apply_patch | 应用补丁 | lingxi/skills/builtin/apply_patch/ |
| spawn_subagent | 生成子代理 | lingxi/skills/builtin/spawn_subagent/ |

## 8. 配置系统

### 8.1 配置文件

- **主配置**：`config.yaml`
- **示例配置**：`config.yaml.example`
- **用户配置**：`.lingxi/conf/config.yml`

### 8.2 核心配置项

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| web.host | 服务器主机 | localhost |
| web.port | 服务器端口 | 5000 |
| llm.api_key | LLM API 密钥 | - |
| llm.model | LLM 模型 | qwen-turbo |
| execution_mode.complex.max_plan_steps | 最大计划步骤 | 8 |
| context_management.compression.enabled | 启用历史压缩 | false |
| session.max_history_turns | 最大历史轮数 | 50 |

## 9. 部署与运行

### 9.1 启动方式

#### 后端启动
```bash
# Windows
start_lingxi.bat

# Linux/Mac
./start_lingxi.sh

# 直接运行
python start_web_server.py
```

#### 前端启动
```bash
# 在 lingxi-desktop 目录
npm run dev

# 构建
npm run build
```

### 9.2 环境要求

#### 后端
- Python 3.8+
- 依赖包：fastapi, uvicorn, websockets, pydantic, sqlite3

#### 前端
- Node.js 16+
- Vue 3
- Electron
- Element Plus

## 10. 开发指南

### 10.1 代码规范

- **Python**：PEP 8 规范
- **TypeScript**：严格模式
- **Vue**：组合式 API，Functional components
- **样式**：Tailwind CSS

### 10.2 测试

- **后端测试**：`lingxi/tests/`
- **前端测试**：`lingxi-desktop/tests/`
- **端到端测试**：Playwright

### 10.3 调试

- **后端调试**：设置 `web.debug: true`
- **前端调试**：Vue DevTools
- **WebSocket 调试**：浏览器开发者工具

## 11. 常见问题与解决方案

### 11.1 连接问题

- **WebSocket 连接失败**：检查服务器是否运行，端口是否被占用
- **API 404**：检查路由是否正确，服务器是否启动

### 11.2 功能问题

- **技能加载失败**：检查技能依赖是否安装，技能配置是否正确
- **LLM 响应错误**：检查 API 密钥是否正确，网络连接是否正常
- **上下文丢失**：检查会话历史是否正确存储，历史上下文构建是否正确

### 11.3 性能问题

- **响应缓慢**：检查 LLM 响应时间，网络连接速度
- **内存占用高**：检查会话历史大小，启用历史压缩

## 12. 未来发展

### 12.1 功能扩展

- **更多技能**：扩展内置技能和用户技能
- **多语言支持**：添加多语言模型和界面
- **插件系统**：支持第三方插件
- **云同步**：会话和配置云同步

### 12.2 技术优化

- **模型优化**：使用更高效的 LLM 模型
- **缓存优化**：优化上下文缓存策略
- **并行处理**：增加并行处理能力
- **容器化**：支持 Docker 部署

## 13. 总结

灵犀智能助手是一个功能完整的智能助手系统，采用现代化的技术栈和架构设计。系统通过 Python 后端提供强大的推理能力和技能系统，通过 Vue+Electron 前端提供友好的用户界面。

核心优势：
- **模块化设计**：清晰的模块划分，易于扩展
- **异步处理**：全异步架构，提高并发性能
- **实时通信**：WebSocket 实时响应，提升用户体验
- **技能系统**：灵活的技能注册和调用机制
- **上下文管理**：智能的历史上下文处理

系统已经具备完整的智能助手功能，可以通过扩展技能和优化模型进一步提升能力。