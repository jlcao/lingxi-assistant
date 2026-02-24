# 灵犀智能助手启动指南

## 概述

灵犀智能助手支持两种启动模式：
- **CLI模式**: 命令行交互模式
- **Web模式**: Web服务器模式（RESTful API + WebSocket）

## 启动方式

### 1. CLI模式（默认）

直接运行或使用`--session`参数指定会话ID：

```bash
python -m lingxi
```

或指定会话：

```bash
python -m lingxi --session my_session
```

CLI模式支持的命令：
- `/help` - 显示帮助
- `/clear` - 清空当前会话
- `/status` - 显示检查点状态
- `/skills` - 列出可用技能
- `/install <path>` - 安装技能
- `/context-stats` - 显示上下文统计
- `/compress` - 手动触发上下文压缩
- `/search <query>` - 检索相关历史
- `/session [id]` - 创建新会话或切换到指定会话
- `/exit` - 退出系统

### 2. Web模式

使用`--web`参数启动Web服务器：

```bash
python -m lingxi --web
```

或指定配置文件：

```bash
python -m lingxi --web --config config.yaml
```

Web模式启动后，可以访问：
- **Web界面**: http://localhost:5000/static/index.html
- **API文档**: http://localhost:5000/docs
- **RESTful API**: http://localhost:5000/api
- **WebSocket**: ws://localhost:5000/ws

#### Web服务配置

在`config.yaml`中配置Web服务：

```yaml
web:
  host: "localhost"
  port: 5000
  debug: false
```

#### API端点

Web模式提供以下API端点：

**会话管理**
- `POST /api/sessions` - 创建会话
- `GET /api/sessions` - 获取会话列表
- `GET /api/sessions/{id}` - 获取会话详情
- `GET /api/sessions/{id}/history` - 获取会话历史
- `DELETE /api/sessions/{id}` - 删除会话
- `PATCH /api/sessions/{id}` - 重命名会话

**任务执行**
- `POST /api/tasks/execute` - 执行任务
- `GET /api/tasks/{id}/status` - 获取任务状态
- `POST /api/tasks/{id}/retry` - 重试任务
- `POST /api/tasks/{id}/cancel` - 取消任务

**断点管理**
- `GET /api/checkpoints` - 获取断点列表
- `GET /api/checkpoints/{id}/status` - 获取断点状态
- `POST /api/checkpoints/{id}/resume` - 恢复断点
- `DELETE /api/checkpoints/{id}` - 删除断点
- `POST /api/checkpoints/cleanup` - 清理过期断点

**技能管理**
- `GET /api/skills` - 获取技能列表
- `GET /api/skills/{id}` - 获取技能详情
- `POST /api/skills/install` - 安装技能
- `GET /api/skills/{id}/diagnose` - 诊断技能
- `POST /api/skills/{id}/reload` - 重新加载技能
- `DELETE /api/skills/{id}` - 卸载技能

**资源监控**
- `GET /api/resources` - 获取资源使用情况
- `GET /api/resources/stats` - 获取资源统计信息

**配置管理**
- `GET /api/config` - 获取配置
- `PUT /api/config` - 更新配置
- `GET /api/config/sections` - 获取配置区块列表
- `GET /api/config/validate` - 验证配置

**聊天**
- `POST /api/chat` - 发送聊天消息

**健康检查**
- `GET /api/health` - 健康检查
- `GET /api/status` - 获取服务器状态

详细API文档请参考 [API.md](lingxi/web/API.md)

## 其他命令行选项

### 配置文件

```bash
python -m lingxi --config custom_config.yaml
```

### 检查点管理

```bash
# 清理过期检查点
python -m lingxi --cleanup-checkpoints

# 列出活跃检查点
python -m lingxi --list-checkpoints

# 清除指定会话的检查点
python -m lingxi --clear-checkpoint session_id
```

### 技能管理

```bash
# 列出可用技能
python -m lingxi --list-skills

# 安装技能
python -m lingxi --install-skill /path/to/skill --skill-name my_skill

# 覆盖安装技能
python -m lingxi --install-skill /path/to/skill --overwrite
```

## 模块结构

```
lingxi/
├── __main__.py              # 主入口，支持CLI/Web模式
├── web/                    # Web服务模块
│   ├── __init__.py
│   ├── fastapi_server.py    # FastAPI服务器
│   ├── websocket.py         # WebSocket管理
│   ├── state.py            # 全局状态管理
│   ├── routes/             # API路由
│   │   ├── chat.py        # 聊天和会话API
│   │   ├── tasks.py       # 任务执行API
│   │   ├── checkpoints.py # 断点管理API
│   │   ├── skills.py      # 技能管理API
│   │   ├── resources.py   # 资源监控API
│   │   ├── config.py      # 配置管理API
│   │   └── health.py     # 健康检查API
│   ├── static/            # 静态文件
│   │   ├── index.html
│   │   ├── app.js
│   │   ├── styles.css
│   │   └── favicon.svg
│   └── API.md            # API文档
├── core/                  # 核心模块
│   ├── classifier.py       # 任务分类器
│   ├── mode_selector.py   # 执行模式选择器
│   ├── session.py         # 会话管理
│   ├── skill_caller.py    # 技能调用器
│   ├── llm_client.py      # LLM客户端
│   ├── prompts.py         # 提示词模板
│   └── engine/           # 执行引擎
│       ├── direct.py       # 直接响应引擎
│       ├── react.py       # ReAct引擎
│       └── plan_react.py # Plan+ReAct引擎
├── context/               # 上下文管理
│   ├── manager.py         # 上下文管理器
│   └── long_term_memory.py # 长期记忆
├── skills/                # 技能系统
│   ├── builtin.py         # 内置技能
│   ├── registry.py        # 技能注册表
│   ├── registry_memory.py # 技能注册表（内存版）
│   └── skill_loader.py   # 技能加载器
├── utils/                 # 工具模块
│   ├── config.py          # 配置管理
│   └── logging.py        # 日志管理
```

## 开发说明

### 作为模块使用

```python
from lingxi import LingxiAssistant

# 创建助手实例
assistant = LingxiAssistant("config.yaml")

# 处理输入
response = assistant.process_input("你好", "session_id")
print(response)
```

### 启动Web服务器

```python
from lingxi.web import run_server

# 启动Web服务器
run_server("config.yaml")
```

### 使用WebSocket客户端

```python
import asyncio
import websockets

async def test_websocket():
    uri = "ws://localhost:5000/ws"
    async with websockets.connect(uri) as websocket:
        # 发送消息
        message = {
            "type": "chat",
            "content": "你好",
            "session_id": "default"
        }
        await websocket.send(json.dumps(message))

        # 接收响应
        response = await websocket.recv()
        print(response)

asyncio.run(test_websocket())
```

## 故障排查

### Web模式启动失败

1. 检查端口是否被占用：
```bash
# Windows
netstat -ano | findstr :5000

# Linux/Mac
lsof -i :5000
```

2. 检查配置文件是否正确：
```bash
python -m lingxi --config config.yaml --list-skills
```

3. 查看日志文件：
```bash
tail -f logs/assistant.log
```

### 导入错误

确保已安装所有依赖：
```bash
pip install -r requirements.txt
```

### API调用失败

1. 检查服务器是否正常运行
2. 查看API文档：http://localhost:5000/docs
3. 检查CORS配置（如果从不同域访问）

## 性能优化

### Web模式

1. **启用生产级服务器**：
```bash
uvicorn lingxi.web.fastapi_server:app --host 0.0.0.0 --port 5000 --workers 4
```

2. **配置缓存**：
```yaml
llm:
  cache_enabled: true
  cache_ttl: 3600
```

3. **启用日志压缩**：
```yaml
logging:
  compression: true
```

### CLI模式

1. **使用更快的模型**：
```yaml
llm:
  models:
    trivial:
      model: "qwen-flash"
```

2. **限制历史记录**：
```yaml
session:
  max_history_turns: 20
```

## 安全建议

1. **生产环境**：
   - 不要使用`--debug`模式
   - 配置防火墙规则
   - 使用HTTPS
   - 实施认证机制

2. **API密钥**：
   - 使用环境变量存储密钥
   - 不要将密钥提交到版本控制
   - 定期轮换密钥

3. **会话管理**：
   - 定期清理过期会话
   - 限制会话数量
   - 实施会话超时

## 版本信息

- 版本: 0.2.0
- 更新日期: 2026-02-24
- Python版本: >= 3.8
