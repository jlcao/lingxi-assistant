# 灵犀个人智能助手 (Lingxi Agent)

一个基于 Python 的智能个人助手系统，支持异步 WebSocket 通讯、多级任务处理、技能扩展和会话管理。

## 功能特性

- **多级任务处理**：支持 trivial/simple/complex 三种任务级别，自动识别任务复杂度
- **智能执行引擎**：Direct、ReAct、Plan+ReAct 三种执行模式，异步引擎支持高并发
- **技能扩展系统**：支持 MCP 格式和传统格式的技能，热插拔扩展
- **会话管理**：支持多会话、检查点恢复、上下文压缩，SQLite 持久化存储
- **异步通讯架构**：WebSocket 全双工实时通讯 + HTTP SSE 辅助，解决长时间任务阻塞问题
- **长短期记忆**：结合向量检索和滑动窗口的混合记忆机制，智能上下文管理
- **RESTful API**：完整的 HTTP API 支持，方便集成到其他系统

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置

复制配置文件模板并填写必要的配置：

```bash
cp config.yaml.example config.yaml
```

编辑 `config.yaml`，配置 LLM API 密钥：

```yaml
llm:
  provider: "openai"
  model: "qwen3.5-plus"
  api_key: "your-api-key-here"
  base_url: "https://coding.dashscope.aliyuncs.com/v1"
```

### 运行

#### 交互模式（CLI）

```bash
# 启动交互模式
python -m lingxi

# 单次任务
python -m lingxi --task "你的问题"

# 指定会话
python -m lingxi --session my_session

# 列出可用技能
python -m lingxi --list-skills

# 安装技能
python -m lingxi --install-skill /path/to/skill/directory
```

#### WebSocket 服务

```bash
# 启动 WebSocket 服务器
python start_web_server.py --reload
```

连接地址：`ws://localhost:5000/ws`

#### HTTP API 服务

```bash
# 启动 HTTP 服务器（包含 WebSocket）
python start_web_server.py
```

访问地址：`http://localhost:5000`

## 交互模式命令

- `/help` - 显示帮助信息
- `/session [id]` - 创建新会话或切换到指定会话
- `/clear` - 清空当前会话
- `/status` - 显示检查点状态
- `/skills` - 列出可用技能
- `/install <path>` - 安装技能
- `/context-stats` - 显示上下文统计
- `/compress` - 手动触发上下文压缩
- `/search <query>` - 检索相关历史
- `/exit` - 退出系统

## WebSocket API

### 连接 WebSocket

```javascript
const ws = new WebSocket('ws://localhost:5000/ws');

ws.onopen = () => {
  console.log('WebSocket 连接成功');
};
```

### 发送消息

#### 普通聊天

```json
{
  "type": "chat",
  "content": "你好",
  "session_id": "default"
}
```

#### 流式聊天（推荐）

```json
{
  "type": "stream_chat",
  "content": "帮我写一首诗",
  "session_id": "default"
}
```

#### 会话管理

```json
{
  "type": "session",
  "action": "switch",
  "new_session_id": "session_123"
}
```

### 接收消息

```javascript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('收到消息:', data);
};
```

## HTTP API

### 任务管理

#### 创建任务

```bash
POST /api/v1/tasks
Content-Type: application/json

{
  "task": "查询北京天气",
  "session_id": "default",
  "stream": true
}
```

#### 获取任务状态

```bash
GET /api/v1/tasks/{task_id}
```

### 会话管理

#### 创建会话

```bash
POST /api/v1/sessions
Content-Type: application/json

{
  "user_name": "default",
  "title": "新会话"
}
```

#### 获取会话列表

```bash
GET /api/v1/sessions
```

#### 获取会话详情

```bash
GET /api/v1/sessions/{session_id}
```

### 技能管理

#### 获取技能列表

```bash
GET /api/v1/skills
```

#### 安装技能

```bash
POST /api/v1/skills/install
Content-Type: application/json

{
  "skill_path": "/path/to/skill"
}
```

### 检查点管理

#### 获取检查点状态

```bash
GET /api/v1/checkpoints/{session_id}
```

#### 清除检查点

```bash
DELETE /api/v1/checkpoints/{session_id}
```

## 技能开发

### 快速开始

1. 在 `.lingxi/skills/` 目录下创建技能目录
2. 创建配置文件（`SKILL.md` 或 `skill.json`）
3. 重启系统，技能会自动注册

### MCP 格式技能

```yaml
---
skill_id: my_skill
skill_name: My Skill
description: 技能描述
version: 1.0.0
author: Your Name
---

技能说明...
```

### 技能示例

```python
# .lingxi/skills/my_skill/main.py

def execute(query: str) -> dict:
    """执行技能"""
    result = do_something(query)
    return {
        "success": True,
        "data": result
    }
```

### 安装技能

```bash
# 命令行安装
python -m lingxi --install-skill /path/to/skill

# 交互模式安装
/install /path/to/skill

# 自然语言安装
安装技能 /path/to/skill
```

## 项目结构

```
lingxi/
├── lingxi/                      # 核心代码
│   ├── core/                    # 核心模块
│   │   ├── engine/             # 执行引擎
│   │   │   ├── direct.py       # 直接执行引擎
│   │   │   ├── react_core.py   # ReAct 引擎核心
│   │   │   ├── plan_react.py   # 计划 +ReAct 引擎
│   │   │   ├── async_react_core.py  # 异步 ReAct 引擎
│   │   │   └── async_plan_react.py  # 异步计划 +ReAct 引擎
│   │   ├── event/              # 事件系统
│   │   │   ├── publisher.py    # 事件发布器
│   │   │   ├── console_subscriber.py    # 控制台订阅者
│   │   │   ├── SessionStore_subscriber.py  # 会话存储订阅者
│   │   │   └── websocket_subscriber.py   # WebSocket 订阅者
│   │   ├── async_llm_client.py # 异步 LLM 客户端
│   │   ├── async_main.py       # 异步助手主类
│   │   ├── session.py          # 会话管理
│   │   ├── classifier.py       # 任务分类器
│   │   ├── prompts.py          # 提示词模板
│   │   └── skill_caller.py     # 技能调用器
│   ├── context/                # 上下文管理
│   │   ├── manager.py          # 上下文管理器
│   │   └── long_term_memory.py # 长期记忆
│   ├── skills/                 # 技能管理
│   │   ├── builtin/            # 内置技能
│   │   ├── registry.py         # 技能注册表
│   │   └── skill_loader.py     # 技能加载器
│   ├── web/                    # Web 服务
│   │   ├── websocket.py        # WebSocket 服务
│   │   ├── fastapi_server.py   # FastAPI 服务器
│   │   └── routes/             # API 路由
│   │       ├── tasks.py        # 任务 API
│   │       ├── sessions.py     # 会话 API
│   │       ├── skills.py       # 技能 API
│   │       └── checkpoints.py  # 检查点 API
│   ├── utils/                  # 工具函数
│   │   ├── config.py           # 配置管理
│   │   └── logging.py          # 日志管理
│   └── __main__.py             # CLI 入口
├── docs/                       # 文档
├── tests/                      # 测试
├── config.yaml                 # 配置文件
├── requirements.txt            # 依赖
└── start_web_server.py         # Web 服务启动脚本
```

## 配置说明

### 主要配置项

#### LLM 配置

```yaml
llm:
  provider: "openai"           # LLM 提供商
  model: "qwen3.5-plus"        # 默认模型
  api_key: "your-api-key"      # API 密钥
  base_url: "https://..."      # API 基础 URL
  max_tokens: 32000            # 最大 Token 数
  temperature: 0.7             # 温度参数
  
  # 分级模型配置
  models:
    trivial:
      model: "kimi-k2.5"       # trivial 任务模型
    simple:
      model: "kimi-k2.5"       # simple 任务模型
    complex:
      model: "kimi-k2.5"       # complex 任务模型
```

#### 任务分类配置

```yaml
task_classification:
  strategy: "llm_first"              # 分类策略
  llm_confidence_threshold: 0.7      # LLM 置信度阈值
  fallback_to_rule: true             # 失败时使用规则分类
```

#### 执行模式配置

```yaml
execution_mode:
  trivial:
    name: "direct"                   # 直接回答
    max_tokens: 1000
  
  simple:
    name: "react"                    # ReAct 模式
    max_loop: 5                      # 最大循环次数
    timeout_seconds: 30              # 超时时间
  
  complex:
    name: "plan_react"               # 计划+ReAct 模式
    max_plan_steps: 8                # 最大计划步骤
    enable_replanning: true          # 支持重规划
    max_replan_count: 2              # 最大重规划次数
```

#### 会话管理配置

```yaml
session:
  db_path: "data/assistant.db"       # SQLite 数据库路径
  max_history_turns: 50              # 最大历史轮次
  checkpoint_ttl_hours: 24           # 检查点生存时间
```

#### 上下文管理配置

```yaml
context_management:
  token_budget:
    max_tokens: 8000                 # 上下文窗口上限
    compression_trigger: 0.7         # 触发压缩的阈值
    critical_threshold: 0.9          # 强制压缩阈值
  
  retention:
    user_input_keep_turns: 10        # 保留用户输入轮次
    tool_result_keep_turns: 5        # 保留工具结果轮次
    task_boundary_archive: true      # 任务完成归档
  
  compression:
    strategy: "hybrid"               # 压缩策略
    summary_ratio: 0.3               # 摘要压缩比例
    enable_llm_summary: true         # 使用 LLM 智能摘要
  
  long_term_memory:
    enabled: true                    # 启用长期记忆
    storage: "sqlite"                # 存储类型
    vector_dim: 384                  # 向量维度
    retrieval_top_k: 5               # 检索返回数量
```

#### Web 服务配置

```yaml
web:
  host: "localhost"                  # 监听地址
  port: 5000                         # 监听端口
  debug: false                       # 调试模式
  
  websocket:
    enabled: true                    # 启用 WebSocket
    path: "/ws"                      # WebSocket 路径
    ping_interval: 20                # 心跳间隔
    ping_timeout: 30                 # 心跳超时
    max_connections: 100             # 最大连接数
  
  cors:
    enabled: true                    # 启用 CORS
    allow_origins: ["*"]             # 允许的源
```

#### 技能配置

```yaml
skills:
  registry_path: "data/skills.db"          # 技能注册表路径
  config_path: "data/skills_config.json"   # 技能配置路径
  use_memory_registry: true                # 使用内存注册表
  builtin_skills_dir: "lingxi/skills/builtin"  # 内置技能目录
  user_skills_dir: ".lingxi/skills"        # 用户技能目录
  builtin_skills:                          # 内置技能列表
    - "search"
    - "create_file"
    - "delete_file"
    - "execute_command"
    - "modify_file"
    - "fetch_webpage"
    - "read_file"
```

## 架构设计

### 核心架构

```
用户输入 → 任务分析 → 模式选择 → 执行引擎 → 能力调用 → 结果输出
    │          │          │          │          │
    ▼          ▼          ▼          ▼          ▼
WebSocket   本地 SQLite  配置文件  异步引擎  MCP/Skill 注册表
    │          │                      │
    │          └───────┬──────────────┘
    │                  │
    ▼                  ▼
控制台输出       事件驱动架构
会话存储         (WebSocket/HTTP/日志)
```

### 异步架构优势

| 指标 | 同步架构 | 异步架构 | 提升 |
|------|----------|----------|------|
| 单连接延迟 | 100% | 100% | - |
| 10 并发延迟 | 1000% | 110% | 9x |
| 最大并发数 | ~10 | ~1000 | 100x |
| CPU 利用率 | 低（等待 IO） | 高 | 显著提升 |

### 事件系统

灵犀采用事件驱动架构，核心事件类型：

| 事件类型 | 说明 | 使用场景 |
|---------|------|---------|
| task_start | 任务开始处理 | 通知客户端任务已接收 |
| think_start | 思考开始 | 显示 AI 正在思考 |
| think_stream | 思考流式内容 | 实时显示思考过程 |
| plan_start | 计划开始 | 显示计划制定中 |
| plan_final | 计划完成 | 展示完整计划 |
| step_start | 步骤开始 | 显示当前执行步骤 |
| step_end | 步骤完成 | 显示步骤执行结果 |
| task_end | 任务完成 | 返回最终结果 |
| task_failed | 任务失败 | 错误处理和重试 |

## 数据库设计

### 表结构

灵犀使用 SQLite 数据库，包含三张核心表：

#### sessions 表（会话）

| 字段名 | 类型 | 说明 |
|-------|------|------|
| session_id | TEXT | 会话唯一标识（主键） |
| user_name | TEXT | 用户名 |
| title | TEXT | 会话标题 |
| current_task_id | TEXT | 当前活跃任务 ID |
| total_tokens | INTEGER | Token 使用计数 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

#### tasks 表（任务）

| 字段名 | 类型 | 说明 |
|-------|------|------|
| task_id | TEXT | 任务唯一标识（主键） |
| session_id | TEXT | 关联的会话 ID（外键） |
| task_type | TEXT | 任务类型 |
| task_level | TEXT | 任务级别（trivial/simple/complex） |
| plan | TEXT | 执行计划（JSON 格式） |
| user_input | TEXT | 用户输入 |
| result | TEXT | 执行结果 |
| status | TEXT | 任务状态 |
| current_step_idx | INTEGER | 当前步骤索引 |
| replan_count | INTEGER | 重规划次数 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

#### steps 表（步骤）

| 字段名 | 类型 | 说明 |
|-------|------|------|
| step_id | TEXT | 步骤唯一标识（主键） |
| task_id | TEXT | 关联的任务 ID（外键） |
| step_index | INTEGER | 步骤索引 |
| step_type | TEXT | 步骤类型 |
| description | TEXT | 步骤描述 |
| thought | TEXT | 思考内容 |
| result | TEXT | 执行结果 |
| skill_call | TEXT | 调用的技能 |
| status | TEXT | 步骤状态 |
| created_at | TIMESTAMP | 创建时间 |

### 数据关系

```
sessions (1) ──< tasks (1) ──< steps
```

- 一个会话包含多个任务
- 一个任务包含多个步骤
- 删除会话时自动级联删除关联的任务和步骤

## 内置技能

灵犀预置了以下内置技能：

| 技能名称 | 说明 | 示例 |
|---------|------|------|
| search | 网络搜索 | 搜索最新新闻 |
| create_file | 创建文件 | 创建 Python 脚本 |
| delete_file | 删除文件 | 删除临时文件 |
| execute_command | 执行命令 | 运行 shell 命令 |
| modify_file | 修改文件 | 更新配置文件 |
| fetch_webpage | 获取网页 | 抓取网页内容 |
| read_file | 读取文件 | 读取日志文件 |

## 技术栈

- **核心框架**: Python 3.8+
- **Web 框架**: FastAPI + Uvicorn
- **通讯协议**: WebSocket + HTTP SSE
- **数据库**: SQLite
- **LLM 客户端**: OpenAI SDK + httpx (异步)
- **事件系统**: 自定义事件发布/订阅模式
- **日志系统**: Python logging (按天轮转)

## 常见问题

### Q: 如何配置多个 LLM 模型？

A: 在 `config.yaml` 的 `llm.models` 配置中为不同任务级别指定不同模型：

```yaml
llm:
  models:
    trivial:
      model: "kimi-k2.5"
    simple:
      model: "kimi-k2.5"
    complex:
      model: "qwen3.5-plus"
```

### Q: WebSocket 连接断开怎么办？

A: WebSocket 支持自动重连，客户端实现重连逻辑即可。服务端会保留会话状态，重连后可继续。

### Q: 如何查看日志？

A: 日志文件位于 `logs/assistant.log`，按天轮转，保留最近 5 个备份。

### Q: 上下文满了怎么办？

A: 系统会自动触发上下文压缩，也可以手动执行 `/compress` 命令。

### Q: 如何备份会话数据？

A: 会话数据存储在 `data/assistant.db`，定期备份此文件即可。

## 开发计划

- [ ] 支持更多 LLM 提供商（Claude、Gemini 等）
- [ ] 增加 GUI 客户端
- [ ] 支持多模态任务（图片、音频）
- [ ] 增加技能市场
- [ ] 支持分布式部署

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

- 项目地址：https://github.com/yourusername/lingxi
- 问题反馈：请提交 Issue
