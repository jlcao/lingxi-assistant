---
# 🤖 AI Agent Mandatory Workflow (强制性工作流)

**CRITICAL: You MUST follow these steps in EXACT order. DO NOT skip any step!**

## 🎯 The 8-Step Process (8 步流程)

```
┌──────────────────────────────────────────────────────────┐
│  STEP 1  │  Read task.json → Select passes:false task   │
│  步骤 1  │  读取 task.json → 选择未完成的任务            │
├──────────────────────────────────────────────────────────┤
│  STEP 2  │  Run start_all.bat/sh → Wait for services    │
│  步骤 2  │  运行启动脚本 → 等待服务启动                  │
├──────────────────────────────────────────────────────────┤
│  STEP 3  │  Implement task → Write code                 │
│  步骤 3  │  实现任务 → 编写代码                          │
├──────────────────────────────────────────────────────────┤
│  STEP 4  │  Run pytest → All tests must pass            │
│  步骤 4  │  运行测试 → 所有测试必须通过                  │
├──────────────────────────────────────────────────────────┤
│  STEP 5  │  Update progress.txt → Log your work         │
│  步骤 5  │  更新进度文件 → 记录工作内容                  │
├──────────────────────────────────────────────────────────┤
│  STEP 6  │  Update task.json → Mark passes: true        │
│  步骤 6  │  更新任务文件 → 标记为已完成                  │
├──────────────────────────────────────────────────────────┤
│  STEP 7  │  Git commit → All changes in ONE commit      │
│  步骤 7  │  Git 提交 → 所有更改在一个提交中              │
├──────────────────────────────────────────────────────────┤
│  STEP 8  │  Verify git status is clean                  │
│  步骤 8  │  验证 git 状态干净                            │
└──────────────────────────────────────────────────────────┘
```

## ⚠️ Critical Rules (关键规则)

1. **NEVER start coding without reading task.json first**
2. **NEVER skip running start_all.bat/sh**
3. **NEVER commit without running tests**
4. **NEVER mark passes: true without ALL tests passing**
5. **ALWAYS commit ALL changes together (code + progress.txt + task.json)**

## ✅ Pre-Commit Checklist (提交前检查)

Before you run `git commit`, verify:
- [ ] I have read task.json and selected a task
- [ ] I have run start_all.bat/sh and services are running
- [ ] I have completed ALL steps in the task
- [ ] I have run `pytest` and ALL tests pass
- [ ] I have updated progress.txt with my work
- [ ] I have updated task.json marking passes: true
- [ ] I am committing ALL changes in ONE commit

**If ANY checkbox is unchecked, STOP and complete it first!**

---

# 灵犀智能助手 - Agent 开发指南

## 项目背景

灵犀智能助手是一个基于 Plan+ReAct 模式的智能助手系统，包含 Python 后端引擎和 Vue+Electron 桌面前端。

## 项目架构

```
/
├── lingxi/          # Python 后端项目
│   ├── core/        # 核心引擎模块
│   │   ├── engine/  # 执行引擎（PlanReAct、ReAct 等）
│   │   ├── session/ # 会话管理
│   │   └── skills/  # 技能系统
│   ├── tests/       # 后端测试目录
│   ├── web/         # Web 服务和 API
│   └── utils/       # 工具函数
├── lingxi-desktop/  # 桌面前端应用
│   ├── electron/    # Electron 主进程
│   ├── src/         # Vue 前端代码
│   └── tests/       # 前端测试目录
│       └── e2e/     # 端到端测试
├── docs/            # 项目设计文档目录
├── AGENTS.md        # 本文件 - Agent 开发指南
├── CLAUDE.md        # 参考开发指南
└── task.json        # 任务定义（真实来源）
```

## 任务管理

### task.json 结构

```json
{
  "project": "项目名称",
  "description": "项目描述",
  "tasks": [
    {
      "id": 1,
      "title": "任务标题",
      "description": "任务描述",
      "steps": ["步骤 1", "步骤 2", "步骤 3"],
      "passes": false
    }
  ]
}
```

### 任务选择优先级

1. 选择 `passes: false` 的任务
2. 考虑依赖关系 - 基础功能优先
3. 选择最高优先级的未完成任务

## 开发流程详解

### 步骤 1：启动服务

**Windows:**
```bash
start_all.bat
```

**Linux/Mac:**
```bash
chmod +x start_all.sh
./start_all.sh
```

服务地址：
- 后端：http://localhost:8000
- 前端：http://localhost:5173

### 步骤 2-3：选择并实现任务

读取 `task.json`，选择任务并实现功能。

### 步骤 4：测试

**后端测试：**
```bash
pytest
```

**前端测试：**
```bash
cd lingxi-desktop
npm test
```

### 步骤 5-6：更新文档

**progress.txt 格式：**
```markdown
## [日期] - 任务：[任务描述]

### 完成的工作：
- [具体修改内容]

### 测试：
- [测试方式和结果]

### 备注：
- [相关说明]
```

**task.json 更新：**
- 将完成任务的 `passes` 从 `false` 改为 `true`

### 步骤 7-8：提交代码

```bash
git add .
git commit -m "[任务描述] - 完成"
git status  # 验证干净
```

## 测试要求

### 大幅代码修改
- ✅ 运行 `pytest` 后端测试
- ✅ 运行 `npm test` 前端测试
- ✅ 浏览器测试（Playwright）
- ✅ 验证页面加载和交互

### 小幅代码修改
- ✅ 可以使用单元测试或 lint 验证
- ✅ 如有疑虑，进行浏览器测试

### 所有修改必须通过
- ✅ 后端：`pytest` 无错误
- ✅ 前端：`npm run lint` 和 `npm run build` 成功
- ✅ 功能在浏览器中正常工作

## 阻塞处理

### 需要停止的情况：

1. **缺少环境配置** - 需要 API 密钥、外部账号
2. **外部依赖不可用** - 第三方服务宕机
3. **测试无法进行** - 依赖未部署系统

### 阻塞时的正确操作：

**禁止：**
- ❌ 提交 git commit
- ❌ 将 task.json 的 passes 设为 true
- ❌ 假装任务已完成

**必须：**
- ✅ 在 progress.txt 中记录阻塞原因
- ✅ 输出清晰的阻塞信息
- ✅ 停止任务，等待人工介入

**阻塞信息格式：**
```markdown
🚫 任务阻塞 - 需要人工介入

**当前任务**: [任务名称]
**已完成的工作**: [已完成的代码/配置]
**阻塞原因**: [具体说明]
**需要人工帮助**: [具体步骤]
```

## 开发规范

### 后端
- Python 3.8+ 语法
- PEP8 代码风格
- 类型注解
- 模块化设计

### 前端
- TypeScript 严格模式
- Vue 3 Composition API
- 组件化设计
- 响应式状态管理

### 技能
- 技能目录结构标准化
- 技能元数据完整
- 输入输出格式统一

## 关键 API

### 后端 API

- 会话管理：`/api/sessions`
- 技能管理：`/api/skills`
- 检查点：`/api/checkpoints`
- 工作目录：`/api/workspace`

### 前端 API

- WebSocket 客户端管理
- 文件系统操作
- 窗口管理

## 调试技巧

### 后端
- 设置 `logging.level` 为 `DEBUG`
- 使用 `--list-skills` 查看技能
- 使用 `--list-checkpoints` 查看检查点

### 前端
- Chrome DevTools 调试渲染进程
- 查看 Electron 主进程日志
- 检查 WebSocket 连接状态

## 最佳实践

1. **代码组织** - 按功能模块化，遵循单一职责
2. **测试策略** - 单元测试 + 集成测试 + E2E 测试
3. **性能优化** - 上下文压缩、缓存、异步处理
4. **安全性** - 验证输入、限制权限、保护密钥

## 版本控制

- 使用 Git 进行版本控制
- 遵循语义化版本规范
- 提交信息清晰明了
- **一个 task 的所有内容必须在同一个 commit 中提交**

---

## 总结

灵犀智能助手是一个基于 Plan+ReAct 模式的智能助手系统。遵循本指南的流程和规范，您可以高效地开发和测试新功能，确保系统的稳定性和可靠性。

**记住：严格按照 8 步流程执行，不要跳过任何步骤！**
