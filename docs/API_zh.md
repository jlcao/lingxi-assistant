# DeerFlow API 文档

## 目录

- [健康检查](#健康检查)
- [模型管理](#模型管理)
- [MCP 配置](#mcp-配置)
- [记忆管理](#记忆管理)
- [技能管理](#技能管理)
- [工件管理](#工件管理)
- [文件上传](#文件上传)
- [线程管理](#线程管理)
- [代理管理](#代理管理)
- [建议生成](#建议生成)
- [渠道管理](#渠道管理)
- [助手兼容接口](#助手兼容接口)
- [运行管理](#运行管理)

***

## 健康检查

### GET /health

获取服务健康状态

**响应示例：**

```json
{
  "status": "healthy",
  "service": "deer-flow-gateway"
}
```

***

## 模型管理

### GET /api/models

获取所有可用的 AI 模型列表

**响应示例：**

```json
{
  "models": [
    {
      "name": "gpt-4",
      "model": "gpt-4",
      "display_name": "GPT-4",
      "description": "OpenAI GPT-4 model",
      "supports_thinking": false,
      "supports_reasoning_effort": false
    }
  ]
}
```

### GET /api/models/{model\_name}

获取指定模型的详细信息

**路径参数：**

- `model_name`: 模型名称

**响应示例：**

```json
{
  "name": "gpt-4",
  "model": "gpt-4",
  "display_name": "GPT-4",
  "description": "OpenAI GPT-4 model",
  "supports_thinking": false,
  "supports_reasoning_effort": false
}
```

***

## MCP 配置

### GET /api/mcp/config

获取 MCP（Model Context Protocol）服务器配置

**响应示例：**

```json
{
  "mcp_servers": {
    "github": {
      "enabled": true,
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {"GITHUB_TOKEN": "ghp_xxx"},
      "url": null,
      "headers": {},
      "oauth": null,
      "description": "GitHub MCP server for repository operations"
    }
  }
}
```

### PUT /api/mcp/config

更新 MCP 服务器配置

**请求体：**

```json
{
  "mcp_servers": {
    "github": {
      "enabled": true,
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {"GITHUB_TOKEN": "$GITHUB_TOKEN"},
      "url": null,
      "headers": {},
      "oauth": null,
      "description": "GitHub MCP server for repository operations"
    }
  }
}
```

**响应示例：**

```json
{
  "mcp_servers": {
    "github": {
      "enabled": true,
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {"GITHUB_TOKEN": "$GITHUB_TOKEN"},
      "url": null,
      "headers": {},
      "oauth": null,
      "description": "GitHub MCP server for repository operations"
    }
  }
}
```

***

## 记忆管理

### GET /api/memory

获取全局记忆数据

**响应示例：**

```json
{
  "version": "1.0",
  "lastUpdated": "2024-01-15T10:30:00Z",
  "user": {
    "workContext": {"summary": "Working on DeerFlow project", "updatedAt": "..."},
    "personalContext": {"summary": "Prefers concise responses", "updatedAt": "..."},
    "topOfMind": {"summary": "Building memory API", "updatedAt": "..."}
  },
  "facts": [
    {
      "id": "fact_abc123",
      "content": "User prefers TypeScript over JavaScript",
      "category": "preference",
      "confidence": 0.9,
      "createdAt": "2024-01-15T10:30:00Z",
      "source": "thread_xyz"
    }
  ]
}
```

### POST /api/memory/reload

从存储文件重新加载记忆数据

### DELETE /api/memory

清空所有记忆数据

### POST /api/memory/facts

创建记忆事实

**请求体：**

```json
{
  "content": "Fact content",
  "category": "context",
  "confidence": 0.5
}
```

### DELETE /api/memory/facts/{fact\_id}

删除记忆事实

**路径参数：**

- `fact_id`: 事实 ID

### PATCH /api/memory/facts/{fact\_id}

更新记忆事实

**路径参数：**

- `fact_id`: 事实 ID

**请求体：**

```json
{
  "content": "Updated fact content",
  "category": "context",
  "confidence": 0.8
}
```

### GET /api/memory/export

导出记忆数据

### POST /api/memory/import

导入记忆数据

**请求体：** 记忆数据结构

### GET /api/memory/config

获取记忆系统配置

**响应示例：**

```json
{
  "enabled": true,
  "storage_path": ".deer-flow/memory.json",
  "debounce_seconds": 30,
  "max_facts": 100,
  "fact_confidence_threshold": 0.7,
  "injection_enabled": true,
  "max_injection_tokens": 2000
}
```

### GET /api/memory/status

获取记忆系统状态（配置 + 数据）

***

## 技能管理

### GET /api/skills

获取所有技能列表

**响应示例：**

```json
{
  "skills": [
    {
      "name": "skill-name",
      "description": "Skill description",
      "license": "MIT",
      "category": "public",
      "enabled": true
    }
  ]
}
```

### POST /api/skills/install

从 .skill 文件安装技能

**请求体：**

```json
{
  "thread_id": "thread-id",
  "path": "mnt/user-data/outputs/my-skill.skill"
}
```

### GET /api/skills/custom

获取自定义技能列表

### GET /api/skills/custom/{skill\_name}

获取自定义技能内容

**路径参数：**

- `skill_name`: 技能名称

### PUT /api/skills/custom/{skill\_name}

编辑自定义技能

**路径参数：**

- `skill_name`: 技能名称

**请求体：**

```json
{
  "content": "SKILL.md content"
}
```

### DELETE /api/skills/custom/{skill\_name}

删除自定义技能

**路径参数：**

- `skill_name`: 技能名称

### GET /api/skills/custom/{skill\_name}/history

获取自定义技能历史

**路径参数：**

- `skill_name`: 技能名称

### POST /api/skills/custom/{skill\_name}/rollback

回滚自定义技能

**路径参数：**

- `skill_name`: 技能名称

**请求体：**

```json
{
  "history_index": -1
}
```

### GET /api/skills/{skill\_name}

获取技能详情

**路径参数：**

- `skill_name`: 技能名称

### PUT /api/skills/{skill\_name}

更新技能启用状态

**路径参数：**

- `skill_name`: 技能名称

**请求体：**

```json
{
  "enabled": true
}
```

***

## 工件管理

### GET /api/threads/{thread\_id}/artifacts/{path:path}

获取工件文件

**路径参数：**

- `thread_id`: 线程 ID
- `path`: 工件路径（支持虚拟路径，如 mnt/user-data/outputs/file.txt）

**查询参数：**

- `download` (可选, boolean): 是否强制下载

***

## 文件上传

### POST /api/threads/{thread\_id}/uploads

上传文件到线程

**路径参数：**

- `thread_id`: 线程 ID

**请求：** multipart/form-data，包含 files 字段

**响应示例：**

```json
{
  "success": true,
  "files": [
    {
      "filename": "file.txt",
      "size": "1024",
      "path": "/path/to/file.txt",
      "virtual_path": "mnt/user-data/uploads/file.txt",
      "artifact_url": "/api/threads/thread-id/artifacts/mnt/user-data/uploads/file.txt",
      "markdown_file": "file.md",
      "markdown_path": "/path/to/file.md",
      "markdown_virtual_path": "mnt/user-data/uploads/file.md",
      "markdown_artifact_url": "/api/threads/thread-id/artifacts/mnt/user-data/uploads/file.md"
    }
  ],
  "message": "Successfully uploaded 1 file(s)"
}
```

### GET /api/threads/{thread\_id}/uploads/list

列出已上传的文件

**路径参数：**

- `thread_id`: 线程 ID

**响应示例：**

```json
{
  "files": [
    {
      "filename": "file.txt",
      "size": 1024,
      "path": "/path/to/file.txt",
      "virtual_path": "mnt/user-data/uploads/file.txt",
      "artifact_url": "/api/threads/thread-id/artifacts/mnt/user-data/uploads/file.txt"
    }
  ]
}
```

### DELETE /api/threads/{thread\_id}/uploads/{filename}

删除已上传的文件

**路径参数：**

- `thread_id`: 线程 ID
- `filename`: 文件名

**响应示例：**

```json
{
  "success": true,
  "message": "File deleted"
}
```

***

## 线程管理

### DELETE /api/threads/{thread\_id}

删除线程数据

**路径参数：**

- `thread_id`: 线程 ID

**响应示例：**

```json
{
  "success": true,
  "message": "Deleted local thread data for thread-id"
}
```

### POST /api/threads

创建新线程

**请求体：**

```json
{
  "thread_id": "optional-id",
  "metadata": {}
}
```

**响应示例：**

```json
{
  "thread_id": "thread-id",
  "status": "idle",
  "created_at": "1620000000.0",
  "updated_at": "1620000000.0",
  "metadata": {},
  "values": {},
  "interrupts": {}
}
```

### POST /api/threads/search

搜索线程

**请求体：**

```json
{
  "metadata": {},
  "limit": 100,
  "offset": 0,
  "status": "idle"
}
```

**响应示例：**

```json
[
  {
        "thread_id": "be8cf505-065b-4fcf-954a-d3085c38f091",
        "status": "idle",
        "created_at": "1776213851.8429692",
        "updated_at": "1776213851.8429692",
        "metadata": {
            "thinking_enabled": true,
            "is_plan_mode": false,
            "subagent_enabled": false,
            "thread_id": "be8cf505-065b-4fcf-954a-d3085c38f091",
            "run_id": "019d74e9-074d-7223-a982-20c911d13710",
            "graph_id": "lead_agent",
            "assistant_id": "bee7d354-5df5-5f26-a978-10ea053f620d",
            "user_id": "",
            "created_by": "system",
            "agent_name": "default",
            "model_name": "doubao-seed-2.0-pro",
            "reasoning_effort": null,
            "run_attempt": 1,
            "langgraph_version": "1.0.9",
            "langgraph_api_version": "0.7.65",
            "langgraph_plan": "enterprise",
            "langgraph_host": "self-hosted",
            "langgraph_api_url": "http://127.0.0.1:2024",
            "langgraph_auth_user_id": "",
            "langgraph_request_id": "a11ad238-c616-4db7-a1e9-6208df4706a0"
        },
        "values": {
            "title": "智能助手问候对话"
        },
        "interrupts": {}
    }
]
```

### PATCH /api/threads/{thread\_id}

更新线程元数据

**路径参数：**

- `thread_id`: 线程 ID

**请求体：**

```json
{
  "metadata": {}
}
```

**响应示例：**

```json
{
  "thread_id": "thread-id",
  "status": "idle",
  "created_at": "1620000000.0",
  "updated_at": "1620000001.0",
  "metadata": {}
}
```

### GET /api/threads/{thread\_id}

获取线程信息

**路径参数：**

- `thread_id`: 线程 ID

**响应示例：**

```json
{
  "thread_id": "thread-id",
  "status": "idle",
  "created_at": "1620000000.0",
  "updated_at": "1620000000.0",
  "metadata": {},
  "values": {},
  "interrupts": {}
}
```

### GET /api/threads/{thread\_id}/state

获取线程状态

**路径参数：**

- `thread_id`: 线程 ID

**响应示例：**

```json
{
  "values": {},
  "next": [],
  "metadata": {},
  "checkpoint": {
    "id": "checkpoint-id",
    "ts": "1620000000.0"
  },
  "checkpoint_id": "checkpoint-id",
  "parent_checkpoint_id": null,
  "created_at": "1620000000.0",
  "tasks": []
}
```

### POST /api/threads/{thread\_id}/state

更新线程状态

**路径参数：**

- `thread_id`: 线程 ID

**请求体：**

```json
{
  "values": {},
  "checkpoint_id": "checkpoint-id",
  "checkpoint": {},
  "as_node": "node-name"
}
```

**响应示例：**

```json
{
  "values": {},
  "next": [],
  "metadata": {},
  "checkpoint_id": "new-checkpoint-id",
  "created_at": "1620000001.0"
}
```

### POST /api/threads/{thread\_id}/history

获取线程历史

**路径参数：**

- `thread_id`: 线程 ID

**请求体：**

```json
{
  "limit": 10,
  "before": "checkpoint-id"
}
```

**响应示例：**

```json
[
  {
    "checkpoint_id": "checkpoint-id",
    "parent_checkpoint_id": null,
    "metadata": {},
    "values": {},
    "created_at": "1620000000.0",
    "next": []
  }
]
```

***

## 代理管理

### GET /api/agents

获取自定义代理列表

**响应示例：**

```json
{
  "agents": [
    {
      "name": "agent-name",
      "description": "Agent description",
      "model": "gpt-4",
      "tool_groups": ["group1"],
      "soul": "SOUL.md content"
    }
  ]
}
```

### GET /api/agents/check

检查代理名称可用性

**查询参数：**

- `name`: 代理名称

**响应示例：**

```json
{
  "available": true,
  "name": "agent-name"
}
```

### GET /api/agents/{name}

获取自定义代理详情

**路径参数：**

- `name`: 代理名称

### POST /api/agents

创建自定义代理

**请求体：**

```json
{
  "name": "agent-name",
  "description": "Agent description",
  "model": "gpt-4",
  "tool_groups": ["group1"],
  "soul": "SOUL.md content"
}
```

### PUT /api/agents/{name}

更新自定义代理

**路径参数：**

- `name`: 代理名称

**请求体：**

```json
{
  "description": "Updated description",
  "model": "gpt-4",
  "tool_groups": ["group1"],
  "soul": "Updated SOUL.md content"
}
```

### DELETE /api/agents/{name}

删除自定义代理

**路径参数：**

- `name`: 代理名称

### GET /api/user-profile

获取用户配置文件

**响应示例：**

```json
{
  "content": "USER.md content"
}
```

### PUT /api/user-profile

更新用户配置文件

**请求体：**

```json
{
  "content": "USER.md content"
}
```

***

## 建议生成

### POST /api/threads/{thread\_id}/suggestions

生成后续问题建议

**路径参数：**

- `thread_id`: 线程 ID

**请求体：**

```json
{
  "messages": [
    {
      "role": "user",
      "content": "Message content"
    }
  ],
  "n": 3,
  "model_name": "gpt-4"
}
```

**响应示例：**

```json
{
  "suggestions": [
    "Follow-up question 1",
    "Follow-up question 2",
    "Follow-up question 3"
  ]
}
```

***

## 渠道管理

### GET /api/channels/

获取渠道状态

**响应示例：**

```json
{
  "service_running": true,
  "channels": {}
}
```

### POST /api/channels/{name}/restart

重启指定渠道

**路径参数：**

- `name`: 渠道名称

**响应示例：**

```json
{
  "success": true,
  "message": "Channel name restarted successfully"
}
```

***

## 助手兼容接口

### POST /api/assistants/search

搜索助手

**请求体：**

```json
{
  "graph_id": "lead_agent",
  "name": "agent-name",
  "limit": 10,
  "offset": 0
}
```

### GET /api/assistants/{assistant\_id}

获取助手详情

**路径参数：**

- `assistant_id`: 助手 ID

### GET /api/assistants/{assistant\_id}/graph

获取助手图结构

**路径参数：**

- `assistant_id`: 助手 ID

### GET /api/assistants/{assistant\_id}/schemas

获取助手 JSON Schema

**路径参数：**

- `assistant_id`: 助手 ID

***

## 运行管理

### POST /api/threads/{thread\_id}/runs

创建后台运行

**路径参数：**

- `thread_id`: 线程 ID

**请求体：**

```json
{
  "assistant_id": "lead_agent",
  "input": {"messages": []},
  "command": {},
  "metadata": {},
  "config": {},
  "context": {},
  "webhook": "",
  "checkpoint_id": "",
  "checkpoint": {},
  "interrupt_before": [],
  "interrupt_after": [],
  "stream_mode": [],
  "stream_subgraphs": false,
  "stream_resumable": null,
  "on_disconnect": "cancel",
  "on_completion": "keep",
  "multitask_strategy": "reject",
  "after_seconds": null,
  "if_not_exists": "create",
  "feedback_keys": []
}
```

**响应示例：**

```json
{
  "run_id": "run-id",
  "thread_id": "thread-id",
  "assistant_id": "lead_agent",
  "status": "pending",
  "metadata": {},
  "kwargs": {},
  "multitask_strategy": "reject",
  "created_at": "",
  "updated_at": ""
}
```

### POST /api/threads/{thread\_id}/runs/stream

创建运行并通过 SSE 流式传输事件

**路径参数：**

- `thread_id`: 线程 ID

**请求体：** 同创建运行

**响应：** SSE 流式传输

### POST /api/threads/{thread\_id}/runs/wait

创建运行并等待完成

**路径参数：**

- `thread_id`: 线程 ID

**请求体：** 同创建运行

**响应示例：**

```json
{
  "messages": [],
  "title": "Run title"
}
```

### GET /api/threads/{thread\_id}/runs

列出线程的所有运行

**路径参数：**

- `thread_id`: 线程 ID

**响应示例：**

```json
[
  {
    "run_id": "run-id",
    "thread_id": "thread-id",
    "assistant_id": "lead_agent",
    "status": "completed",
    "metadata": {},
    "kwargs": {},
    "multitask_strategy": "reject",
    "created_at": "",
    "updated_at": ""
  }
]
```

### GET /api/threads/{thread\_id}/runs/{run\_id}

获取运行详情

**路径参数：**

- `thread_id`: 线程 ID
- `run_id`: 运行 ID

**响应示例：**

```json
{
  "run_id": "run-id",
  "thread_id": "thread-id",
  "assistant_id": "lead_agent",
  "status": "completed",
  "metadata": {},
  "kwargs": {},
  "multitask_strategy": "reject",
  "created_at": "",
  "updated_at": ""
}
```

### POST /api/threads/{thread\_id}/runs/{run\_id}/cancel

取消运行

**路径参数：**

- `thread_id`: 线程 ID
- `run_id`: 运行 ID

**查询参数：**

- `wait` (可选, boolean): 是否等待完成
- `action` (可选, string): 取消动作（interrupt 或 rollback）

**响应状态码：** 202 Accepted 或 204 No Content

### GET /api/threads/{thread\_id}/runs/{run\_id}/join

加入现有运行的 SSE 流

**路径参数：**

- `thread_id`: 线程 ID
- `run_id`: 运行 ID

**响应：** SSE 流式传输

### GET/POST /api/threads/{thread\_id}/runs/{run\_id}/stream

加入现有运行的 SSE 流或取消后流式传输

**路径参数：**

- `thread_id`: 线程 ID
- `run_id`: 运行 ID

**查询参数：**

- `action` (可选, string): 取消动作
- `wait` (可选, int): 是否等待

**响应：** SSE 流式传输

### POST /api/runs/stream

无状态运行流式传输

**请求体：** 同创建运行

**响应：** SSE 流式传输

### POST /api/runs/wait

无状态运行并等待完成

**请求体：** 同创建运行

**响应示例：**

```json
{
  "messages": [],
  "title": "Run title"
}
```

