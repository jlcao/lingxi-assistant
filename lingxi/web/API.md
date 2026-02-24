# 灵犀智能助手 RESTful API 和 WebSocket 服务文档

## 概述

灵犀智能助手 V3.0 提供完整的 RESTful API 和 WebSocket 服务，支持桌面端客户端接入。

### 服务地址

- HTTP API: `http://localhost:5000/api`
- WebSocket: `ws://localhost:5000/ws`
- Web界面: `http://localhost:5000/static/index.html`

### API 文档

启动服务后访问 `http://localhost:5000/docs` 查看 Swagger UI 交互式文档。

## RESTful API

### 1. 会话管理 API

#### 1.1 创建会话

```http
POST /api/sessions
Content-Type: application/json

{
  "user_name": "default"
}
```

**响应示例:**
```json
{
  "session_id": "uuid",
  "user_name": "default",
  "created_at": "2026-02-24T10:00:00Z",
  "updated_at": "2026-02-24T10:00:00Z"
}
```

#### 1.2 获取会话列表

```http
GET /api/sessions
```

**响应示例:**
```json
{
  "success": true,
  "sessions": [...],
  "count": 1
}
```

#### 1.3 获取会话详情

```http
GET /api/sessions/{session_id}
```

#### 1.4 获取会话历史

```http
GET /api/sessions/{session_id}/history?max_turns=20
```

#### 1.5 重命名会话

```http
PATCH /api/sessions/{session_id}?new_title=新标题
```

#### 1.6 删除会话

```http
DELETE /api/sessions/{session_id}
```

### 2. 任务执行 API

#### 2.1 执行任务

```http
POST /api/tasks/execute
Content-Type: application/json

{
  "task": "查北京天气",
  "session_id": "uuid",
  "model_override": null
}
```

**响应示例:**
```json
{
  "execution_id": "uuid",
  "task": "查北京天气",
  "task_level": "simple",
  "model": "qwen-plus",
  "status": "completed",
  "current_step": 0,
  "total_steps": 0,
  "result": {
    "content": "北京今天天气晴朗，温度15°C"
  },
  "created_at": 1708764000.0,
  "updated_at": 1708764010.0
}
```

#### 2.2 获取任务状态

```http
GET /api/tasks/{execution_id}/status
```

#### 2.3 重试任务

```http
POST /api/tasks/{execution_id}/retry
Content-Type: application/json

{
  "step_index": 2,
  "user_input": null
}
```

#### 2.4 取消任务

```http
POST /api/tasks/{execution_id}/cancel
```

### 3. 断点管理 API

#### 3.1 获取断点列表

```http
GET /api/checkpoints
```

**响应示例:**
```json
{
  "checkpoints": [
    {
      "session_id": "uuid",
      "task": "规划旅行",
      "current_step": 2,
      "total_steps": 5,
      "execution_status": "paused",
      "updated_at": 1708764000.0
    }
  ],
  "count": 1
}
```

#### 3.2 获取断点状态

```http
GET /api/checkpoints/{session_id}/status
```

#### 3.3 恢复断点

```http
POST /api/checkpoints/{session_id}/resume
```

#### 3.4 删除断点

```http
DELETE /api/checkpoints/{session_id}
```

#### 3.5 清理过期断点

```http
POST /api/checkpoints/cleanup?ttl_hours=24
```

### 4. 技能管理 API

#### 4.1 获取技能列表

```http
GET /api/skills?enabled_only=false
```

**响应示例:**
```json
{
  "skills": [
    {
      "skill_id": "weather",
      "name": "天气查询",
      "description": "查询指定城市的天气信息",
      "version": "1.0.0",
      "status": "available"
    }
  ],
  "count": 1
}
```

#### 4.2 获取技能详情

```http
GET /api/skills/{skill_id}
```

#### 4.3 安装技能

```http
POST /api/skills/install
Content-Type: application/json

{
  "skill_data": {
    "name": "weather",
    "version": "1.0.0",
    "description": "天气查询技能",
    "author": "author",
    "dependencies": [],
    "entry_point": "main.py"
  },
  "skill_files": {
    "main.py": "base64_encoded_content",
    "skill_manifest.json": "base64_encoded_content"
  },
  "overwrite": false
}
```

#### 4.4 诊断技能

```http
GET /api/skills/{skill_id}/diagnose
```

#### 4.5 重新加载技能

```http
POST /api/skills/{skill_id}/reload
```

#### 4.6 卸载技能

```http
DELETE /api/skills/{skill_id}
```

### 5. 资源监控 API

#### 5.1 获取资源使用情况

```http
GET /api/resources
```

**响应示例:**
```json
{
  "cpu_percent": 45.2,
  "memory_percent": 62.8,
  "disk_percent": 35.1,
  "memory_used_mb": 1024.5,
  "memory_total_mb": 8192.0,
  "disk_used_gb": 256.3,
  "disk_total_gb": 1024.0,
  "token_usage": {
    "current": 12500,
    "limit": 100000,
    "percent": 12.5
  },
  "timestamp": 1708764000.0
}
```

#### 5.2 获取资源统计信息

```http
GET /api/resources/stats
```

### 6. 配置管理 API

#### 6.1 获取配置

```http
GET /api/config
```

**响应示例:**
```json
{
  "llm": {
    "provider": "dashscope",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "max_tokens": 4000,
    "temperature": 0.7,
    "timeout": 30,
    "models": {...},
    "default_model": "qwen-plus"
  },
  "task_classification": {...},
  "execution_mode": {...},
  "skill_call": {...},
  "session": {...},
  "logging": {...},
  "system": {...},
  "web": {...}
}
```

#### 6.2 更新配置

```http
PUT /api/config
Content-Type: application/json

{
  "llm": {
    "temperature": 0.8
  },
  "execution_mode": {
    "simple": {
      "max_loop": 10
    }
  }
}
```

#### 6.3 获取配置区块列表

```http
GET /api/config/sections
```

#### 6.4 验证配置

```http
GET /api/config/validate
```

**响应示例:**
```json
{
  "valid": true,
  "error_count": 0,
  "warning_count": 1,
  "results": [
    {
      "section": "llm",
      "field": "provider",
      "status": "ok",
      "message": "LLM提供商: dashscope"
    },
    {
      "section": "llm",
      "field": "api_key",
      "status": "warning",
      "message": "API密钥未配置，请设置环境变量或配置文件"
    }
  ]
}
```

### 7. 聊天 API

#### 7.1 发送聊天消息

```http
POST /api/chat
Content-Type: application/json

{
  "message": "你好",
  "session_id": "default"
}
```

**响应示例:**
```json
{
  "response": "你好！有什么可以帮助你的吗？",
  "session_id": "default"
}
```

### 8. 健康检查 API

#### 8.1 健康检查

```http
GET /api/health
```

**响应示例:**
```json
{
  "status": "healthy",
  "service": "lingxi-web",
  "version": "0.1.0"
}
```

## WebSocket 服务

### 连接

```javascript
const ws = new WebSocket('ws://localhost:5000/ws');
```

### 消息类型

#### 1. 聊天消息

**发送:**
```json
{
  "type": "chat",
  "content": "你好",
  "session_id": "default"
}
```

**接收:**
```json
{
  "type": "chat",
  "success": true,
  "data": {
    "content": "你好！有什么可以帮助你的吗？",
    "session_id": "default"
  },
  "timestamp": 1708764000.0
}
```

#### 2. 流式聊天

**发送:**
```json
{
  "type": "stream_chat",
  "content": "你好",
  "session_id": "default"
}
```

**接收:**
```json
{
  "type": "stream_start",
  "success": true,
  "data": {"session_id": "default"},
  "timestamp": 1708764000.0
}
```

```json
{
  "type": "stream_chunk",
  "stream": true,
  "chunk_index": 0,
  "is_last": false,
  "content": "你好",
  "metadata": {},
  "timestamp": 1708764000.0
}
```

```json
{
  "type": "stream_end",
  "success": true,
  "data": {"session_id": "default"},
  "timestamp": 1708764001.0
}
```

#### 3. 命令消息

**发送:**
```json
{
  "type": "command",
  "command": "help",
  "session_id": "default",
  "args": {}
}
```

**接收:**
```json
{
  "type": "command",
  "success": true,
  "data": {
    "command": "help",
    "result": {
      "available_commands": [...]
    }
  },
  "timestamp": 1708764000.0
}
```

#### 4. 会话管理

**发送:**
```json
{
  "type": "session",
  "action": "switch",
  "new_session_id": "new_uuid"
}
```

#### 5. 检查点管理

**发送:**
```json
{
  "type": "checkpoint",
  "action": "status",
  "session_id": "default"
}
```

#### 6. 技能管理

**发送:**
```json
{
  "type": "skill",
  "action": "list"
}
```

#### 7. 上下文管理

**发送:**
```json
{
  "type": "context",
  "action": "stats"
}
```

#### 8. 心跳

**发送:**
```json
{
  "type": "ping"
}
```

**接收:**
```json
{
  "type": "success",
  "success": true,
  "data": {"pong": true},
  "timestamp": 1708764000.0
}
```

### V3.0 事件类型

#### 思维链事件

```json
{
  "event_type": "thought_chain",
  "data": {
    "execution_id": "uuid",
    "thoughts": [
      {
        "step": 1,
        "type": "task_analysis",
        "content": "用户请求查询天气，这是一个简单任务",
        "confidence": 0.95,
        "timestamp": 1708764000.0
      },
      {
        "step": 2,
        "type": "model_route",
        "content": "检测到单工具调用需求，选择qwen-plus模型",
        "confidence": 0.90,
        "timestamp": 1708764001.0
      }
    ]
  }
}
```

#### 步骤状态事件

```json
{
  "event_type": "step_status",
  "data": {
    "execution_id": "uuid",
    "step_index": 1,
    "status": "running",
    "error": null,
    "timestamp": 1708764002.0
  }
}
```

#### 技能调用事件

```json
{
  "event_type": "skill_call",
  "data": {
    "execution_id": "uuid",
    "skill_id": "weather",
    "parameters": {"city": "北京"},
    "result": {"temperature": 15, "condition": "晴"},
    "timestamp": 1708764003.0
  }
}
```

#### 资源更新事件

```json
{
  "event_type": "resource_update",
  "data": {
    "cpu_percent": 45.2,
    "memory_percent": 62.8,
    "disk_percent": 35.1,
    "token_usage": {
      "current": 12500,
      "limit": 100000,
      "percent": 12.5
    }
  }
}
```

#### 模型路由事件

```json
{
  "event_type": "model_route",
  "data": {
    "task_level": "simple",
    "selected_model": "qwen-plus",
    "reason": "检测到单工具调用需求，选择标准模型",
    "estimated_tokens": 1500
  }
}
```

#### 任务完成事件

```json
{
  "event_type": "task_completed",
  "data": {
    "execution_id": "uuid",
    "task": "查北京天气",
    "status": "completed",
    "result": {"content": "北京今天天气晴朗，温度15°C"},
    "timestamp": 1708764010.0
  }
}
```

#### 任务失败事件

```json
{
  "event_type": "task_failed",
  "data": {
    "execution_id": "uuid",
    "task": "查北京天气",
    "status": "failed",
    "error": {
      "type": "skill_error",
      "message": "天气API调用失败",
      "step_index": 2
    },
    "timestamp": 1708764010.0
  }
}
```

## 启动服务

### 使用命令行

```bash
python -m web.fastapi_server
```

### 使用配置文件

在 `config.yaml` 中配置：

```yaml
web:
  host: "localhost"
  port: 5000
  debug: false
```

## 错误处理

所有 API 返回标准错误格式：

```json
{
  "detail": "错误描述"
}
```

常见 HTTP 状态码：
- `200`: 成功
- `400`: 请求参数错误
- `404`: 资源不存在
- `500`: 服务器内部错误
- `503`: 服务未初始化

## 客户端示例

### Python 客户端

```python
import requests

base_url = "http://localhost:5000/api"

# 创建会话
response = requests.post(f"{base_url}/sessions", json={"user_name": "default"})
session_id = response.json()["session_id"]

# 执行任务
response = requests.post(f"{base_url}/tasks/execute", json={
    "task": "查北京天气",
    "session_id": session_id
})
print(response.json())
```

### JavaScript 客户端

```javascript
// REST API
const response = await fetch('http://localhost:5000/api/tasks/execute', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        task: '查北京天气',
        session_id: 'default'
    })
});
const result = await response.json();

// WebSocket
const ws = new WebSocket('ws://localhost:5000/ws');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};

ws.send(JSON.stringify({
    type: 'chat',
    content: '你好',
    session_id: 'default'
}));
```

## 注意事项

1. **API密钥**: 确保在 `config.yaml` 或环境变量中配置了正确的 API 密钥
2. **CORS**: 默认允许所有来源，生产环境请限制允许的来源
3. **认证**: 当前版本未实现认证，请确保在受信任的网络环境中使用
4. **性能**: WebSocket 连接数过多可能影响性能，建议合理控制连接数
5. **日志**: 查看日志文件了解详细运行信息

## 版本信息

- API 版本: 3.0.0
- 文档更新: 2026-02-24
