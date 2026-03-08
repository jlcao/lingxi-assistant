# 灵犀智能助手 - Agent 开发指南

## 项目背景

灵犀智能助手是一个基于 Plan+ReAct 模式的智能助手系统，包含 Python 后端引擎和 Vue+Electron 桌面前端。

> 注意：详细的项目需求将在定义后添加到 task.json 文件中。

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

### 文档目录说明

`docs/` 目录存放了项目的设计文档

在开发具体功能时，可以参考这些设计文档来了解功能的设计思路和实现要求。

## task.json 文件生成

重要:对于复杂任务，需要先创建或更新 `task.json` 文件，定义项目的任务结构和步骤。

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
      "steps": [
        "步骤 1 描述",
        "步骤 2 描述",
        "步骤 3 描述"
      ],
      "passes": false
    },
    {
      "id": 2,
      "title": "任务标题 2",
      "description": "任务描述 2",
      "steps": [
        "步骤 1 描述",
        "步骤 2 描述"
      ],
      "passes": false
    }
  ]
}
```

### 字段说明

- **project**: 项目名称
- **description**: 项目描述
- **tasks**: 任务列表
  - **id**: 任务 ID（唯一）
  - **title**: 任务标题
  - **description**: 任务详细描述
  - **steps**: 任务执行步骤列表
  - **passes**: 任务是否完成（默认为 false）

### 生成方法

1. **手动创建**：直接创建 task.json 文件，按照上述结构填写内容
2. **基于模板**：基于现有 task.json 模板进行修改
3. **任务分解**：将复杂任务分解为多个子任务，每个子任务包含具体的执行步骤


## 强制性：Agent 开发工作流程

每个新的 agent 会话必须遵循以下工作流程：

### 步骤 1：环境初始化 & 启动服务

使用一键启动脚本自动完成环境初始化和启动服务：

**Windows 系统：**
```bash
# 双击运行启动脚本
start_all.bat
```

**Linux/Mac 系统：**
```bash
# 先添加执行权限
chmod +x start_all.sh
# 运行启动脚本
./start_all.sh
```

脚本将自动完成以下操作：
- 检查并初始化 Python 虚拟环境
- 安装所有后端和前端依赖
- 启动后端服务（http://localhost:8000）
- 启动前端开发服务（http://localhost:5173）

**不要跳过此步骤。** 确保服务在继续之前运行。

**停止服务：**
- Windows: 运行 `stop_all.bat`
- Linux/Mac: 运行 `./stop_all.sh`

### 步骤 3：选择任务

读取 `task.json` 并选择一个任务进行工作：

选择标准（优先级顺序）：
1. 选择 `passes: false` 的任务
2. 考虑依赖关系 - 基础功能应优先完成
3. 选择最高优先级的未完成任务

### 步骤 4：实现任务

- 仔细阅读任务描述和步骤
- 实现满足所有步骤的功能
- 遵循现有代码模式和约定

### 步骤 5：全面测试

实现后，验证任务的所有步骤：

**强制测试要求：**

1. **大幅代码修改**（新建页面、重写组件、修改核心交互）：
   - 运行后端测试：`pytest`
   - 运行前端测试：`npm test`（如需设置，见下方前端测试配置）
   - **必须在浏览器中测试！** 使用 Playwright 工具
   - 验证页面能正确加载和渲染
   - 验证表单提交、按钮点击等交互功能
   - 截图确认 UI 正确显示
   - 验证功能在桌面应用中正常工作

2. **小幅代码修改**（修复 bug、调整样式、添加辅助函数）：
   - 可以使用单元测试或 lint/build 验证
   - 如有疑虑，仍建议浏览器测试

3. **所有修改必须通过**：
   - 后端：`pytest` 无错误
   - 前端：`npm run lint` 和 `npm run build` 成功
   - 浏览器/单元测试验证功能正常

**测试清单：**
- [ ] 代码没有语法错误
- [ ] 所有测试通过
- [ ] 构建成功
- [ ] 功能在浏览器中正常工作（对于 UI 相关修改）
- [ ] 功能在桌面应用中正常工作

## 前端自动化测试配置

### 测试环境设置

1. **安装测试依赖**：
   ```bash
   cd lingxi-desktop
   npm install --save-dev vitest @vue/test-utils happy-dom
   ```

2. **配置测试脚本**：在 `package.json` 中添加测试脚本
   ```json
   "scripts": {
     // 现有脚本...
     "test": "vitest run",
     "test:watch": "vitest"
   }
   ```

3. **创建测试配置文件**：`vitest.config.ts`
   ```typescript
   import { defineConfig } from 'vitest/config'
   import vue from '@vitejs/plugin-vue'

   export default defineConfig({
     plugins: [vue()],
     test: {
       environment: 'happy-dom',
       include: ['src/**/*.test.{ts,tsx,vue}']
     }
   })
   ```

### 测试策略

1. **单元测试**：
   - 测试单个组件的功能
   - 测试工具函数
   - 测试状态管理

2. **组件测试**：
   - 测试组件渲染
   - 测试组件交互
   - 测试组件生命周期

3. **端到端测试**：
   - 使用 Playwright 进行浏览器测试
   - 测试完整用户流程
   - 验证页面能正确加载和渲染
   - 验证表单提交、按钮点击等交互功能
   - 截图确认 UI 正确显示


### 测试文件结构

```
/
├── src/
│   ├── components/
│   │   ├── ChatCore.vue
│   │   ├── ChatCore.test.ts  // 组件测试文件
│   ├── utils/
│   │   ├── helpers.ts
│   │   ├── helpers.test.ts   // 工具函数测试文件
│   └── stores/
│       ├── app.ts
│       ├── app.test.ts       // 状态管理测试文件
├── tests/
│   └── e2e/                 // 端到端测试文件
│       ├── lingxi.spec.ts    // Electron 应用测试（主测试文件）
│       └── example.spec.ts   // Playwright 测试示例
└── test-results/             // 测试失败时的截图
    ├── app-startup.png
    └── input-test.png
```

### 测试示例

**Electron 应用测试示例**（完整测试套件）：

完整的 Electron 应用测试包括：
- 应用启动测试
- UI 组件可见性测试
- 版本号验证测试
- 输入交互测试
- 截图验证

测试文件应包含：
1. `beforeAll` 钩子：启动 Electron 应用并等待页面加载
2. `afterAll` 钩子：正确关闭应用（带错误处理）
3. 多个测试用例：覆盖不同的功能和 UI 组件

**组件测试示例**：
```typescript
import { mount } from '@vue/test-utils'
import { describe, it, expect } from 'vitest'
import ChatCore from './ChatCore.vue'

describe('ChatCore.vue', () => {
  it('renders message list', () => {
    const wrapper = mount(ChatCore)
    expect(wrapper.find('.message-list').exists()).toBe(true)
  })

  it('handles user input', async () => {
    const wrapper = mount(ChatCore)
    const input = wrapper.find('input')
    await input.setValue('Hello')
    expect(input.element.value).toBe('Hello')
  })
})
```

### 运行测试

**运行单元测试**：
```bash
# 运行所有测试
npm test

# 运行特定测试文件
npm test src/components/ChatCore.test.ts

# 监视模式运行测试
npm run test:watch
```

**运行 E2E 测试（Electron 应用）**：
```bash
# 运行所有 E2E 测试
npm run test:e2e

# 运行特定测试文件
npm run test:e2e tests/e2e/lingxi.spec.ts

# 运行特定测试用例
npm run test:e2e -- --grep "应用应该能够输入文本"

# 以有头模式运行（显示浏览器窗口）
npm run test:e2e -- --headed

# 调试模式运行
npm run test:e2e -- --debug

# 生成 HTML 报告
npx playwright show-report
```

**测试最佳实践**：
1. 在 CI/CD 环境中使用无头模式（默认）
2. 本地调试时使用有头模式（`--headed`）
3. 失败时自动截图（已配置 `screenshot: 'only-on-failure'`）
4. 录制测试视频以便调试（已配置 `video: 'retain-on-failure'`）
5. 使用 trace 进行详细的问题追踪

### 常见问题和解决方案

1. **测试在 afterAll hook 超时**：
   - 原因：应用关闭时 WebSocket 连接或其他异步操作仍在进行
   - 解决方案：在 afterAll 中添加错误处理和超时控制，使用 `process().kill()` 强制终止

2. **无法获取输入框的值**：
   - 原因：Element Plus 等 UI 库可能使用非标准的 DOM 结构
   - 解决方案：使用 `evaluate` 方法直接访问 DOM 元素的 `value` 属性

3. **测试启动多个 Electron 进程**：
   - 原因：配置了多个浏览器项目（chromium、firefox、webkit）
   - 解决方案：只配置 chromium 项目，设置 `workers: 1` 禁止并行执行

4. **EPIPE broken pipe 错误**：
   - 原因：应用关闭时尝试写入已关闭的流
   - 解决方案：在 afterAll 中添加 try-catch 错误处理，忽略关闭时的错误

### 步骤 6：更新进度

将工作内容写入 `progress.txt`：

```
## [日期] - 任务：[任务描述]

### 完成的工作：
- [具体修改内容]

### 测试：
- [测试方式和结果]

### 备注：
- [对未来 Agent 的相关说明]
```

### 步骤 7：提交更改（包含 task.json 更新）

**重要：所有更改必须在同一个 commit 中提交，包括 task.json 的更新！**

流程：
1. 更新 `task.json`，将任务的 `passes` 从 `false` 改为 `true`
2. 更新 `progress.txt` 记录工作内容
3. 一次性提交所有更改：

```bash
git add .
git commit -m "[任务描述] - 完成"
```

**规则：**
- 只有在所有步骤都验证通过后才标记 `passes: true`
- 永远不要删除或修改任务描述
- 永远不要从列表中移除任务
- **一个 task 的所有内容（代码、progress.txt、task.json）必须在同一个 commit 中提交**

## 阻塞处理

**如果任务无法完成测试或需要人工介入，必须遵循以下规则：**

### 需要停止任务并请求人工帮助的情况：

1. **缺少环境配置**：
   - 配置文件需要填写真实的 API 密钥
   - 外部服务需要开通账号

2. **外部依赖不可用**：
   - 第三方 API 服务宕机
   - 需要人工授权的流程

3. **测试无法进行**：
   - 功能依赖外部系统尚未部署
   - 需要特定硬件环境

### 阻塞时的正确操作：

**禁止：**
- ❌ 提交 git commit
- ❌ 将 task.json 的 passes 设为 true
- ❌ 假装任务已完成

**必须：**
- ✅ 在 progress.txt 中记录当前进度和阻塞原因
- ✅ 输出清晰的阻塞信息，说明需要人工做什么
- ✅ 停止任务，等待人工介入

### 阻塞信息格式：

```
🚫 任务阻塞 - 需要人工介入

**当前任务**: [任务名称]

**已完成的工作**:
- [已完成的代码/配置]

**阻塞原因**:
- [具体说明为什么无法继续]

**需要人工帮助**:
1. [具体的步骤 1]
2. [具体的步骤 2]
...

**解除阻塞后**:
- 运行 [命令] 继续任务
```

## 开发规范

### 后端开发规范

- Python 3.8+ 语法
- PEP8 代码风格
- 类型注解
- 模块化设计
- 详细的日志记录

### 前端开发规范

- TypeScript 严格模式
- Vue 3 Composition API
- 组件化设计
- 响应式状态管理
- 清晰的错误处理

### 技能开发规范

- 技能目录结构标准化
- 技能元数据完整
- 输入输出格式统一
- 错误处理机制完善

## 关键 API

### 后端 API

1. **会话管理**：
   - 创建会话：`POST /api/sessions`
   - 获取会话历史：`GET /api/sessions/{session_id}/history`
   - 清理会话：`DELETE /api/sessions/{session_id}`

2. **技能管理**：
   - 列出技能：`GET /api/skills`
   - 安装技能：`POST /api/skills/install`
   - 卸载技能：`DELETE /api/skills/{skill_name}`

3. **检查点管理**：
   - 获取检查点：`GET /api/checkpoints`
   - 恢复检查点：`POST /api/checkpoints/{session_id}/resume`
   - 清除检查点：`DELETE /api/checkpoints/{session_id}`

### 前端 API

1. **Electron 主进程**：
   - WebSocket 客户端管理
   - 文件系统操作
   - 窗口管理

2. **Vue 组件**：
   - 聊天核心组件
   - 技能工作区
   - 历史记录管理

## 调试技巧

1. **后端调试**：
   - 设置 `logging.level` 为 `DEBUG`
   - 使用 `--list-skills` 查看可用技能
   - 使用 `--list-checkpoints` 查看检查点状态

2. **前端调试**：
   - 使用 Chrome DevTools 调试渲染进程
   - 查看 Electron 主进程日志
   - 检查 WebSocket 连接状态

3. **技能调试**：
   - 使用 `/install` 命令安装本地技能
   - 查看技能执行日志
   - 测试技能输入输出

## 常见问题

1. **WebSocket 连接失败**：
   - 检查后端服务是否运行
   - 验证端口配置是否正确
   - 查看网络防火墙设置

2. **技能执行失败**：
   - 检查技能依赖是否安装
   - 验证技能输入参数是否正确
   - 查看技能执行日志

3. **检查点恢复失败**：
   - 验证检查点数据是否完整
   - 检查任务是否匹配
   - 查看会话状态

## 最佳实践

1. **代码组织**：
   - 按功能模块化
   - 遵循单一职责原则
   - 保持代码简洁清晰

2. **测试策略**：
   - 单元测试覆盖核心功能
   - 集成测试验证模块交互
   - 端到端测试确保用户体验

3. **性能优化**：
   - 上下文压缩减少 Token 使用
   - 缓存频繁使用的结果
   - 异步处理提高响应速度

4. **安全性**：
   - 验证所有用户输入
   - 限制技能执行权限
   - 保护敏感配置信息

## 版本控制

- 使用 Git 进行版本控制
- 遵循语义化版本规范
- 提交信息清晰明了
- 定期合并到主分支

## 部署指南

1. **后端部署**：
   - 使用 Docker 容器化
   - 配置环境变量
   - 设置适当的资源限制

2. **前端打包**：
   - 构建生产版本：`npm run build`
   - 打包桌面应用：`npm run electron:build`
   - 分发安装包

## 未来发展

1. **技能生态**：
   - 技能市场
   - 技能评分系统
   - 技能推荐机制

2. **多模态支持**：
   - 图像识别
   - 语音交互
   - 视频处理

3. **智能程度提升**：
   - 更好的任务规划
   - 更准确的技能选择
   - 更自然的对话体验

---

## 总结

灵犀智能助手是一个功能强大的智能助手系统，采用 Plan+ReAct 模式实现智能任务执行。通过本开发指南，您可以了解项目架构、开发流程和最佳实践，为项目的持续发展做出贡献。

遵循本指南的流程和规范，您可以高效地开发和测试新功能，确保系统的稳定性和可靠性。