# E2E 联调测试报告

## 测试概览

- **测试文件**: 5 个
- **测试用例**: 15 个
- **执行时间**: 待执行
- **通过率**: 待执行

## 测试结果

### 聊天功能测试
- [ ] 发送消息并接收回复
- [ ] 显示思考链过程
- [ ] 支持多轮对话
- [ ] 创建新会话
- [ ] 切换会话

### API 连通性测试
- [ ] 后端 API 可访问
- [ ] 获取会话列表
- [ ] 发送消息

### 文件操作测试
- [ ] 上传文件
- [ ] 打开文件

### 错误处理测试
- [ ] 显示友好错误提示
- [ ] 支持重试机制

### 性能测试
- [ ] 消息响应时间 <3 秒
- [ ] 界面渲染流畅
- [ ] 内存占用稳定

## 问题汇总

1. 待执行测试后填写
2. 待执行测试后填写

## 结论

- [ ] 通过所有测试
- [ ] 通过核心测试
- [ ] 需要修复问题

---

## 测试文件清单

1. `playwright.e2e.config.ts` - E2E 测试配置文件
2. `tests/e2e/integration/chat-flow.e2e.test.ts` - 聊天功能联调测试
3. `tests/e2e/integration/api-connectivity.e2e.test.ts` - API 连通性测试
4. `tests/e2e/integration/file-operations.e2e.test.ts` - 文件操作联调测试
5. `tests/e2e/integration/error-handling.e2e.test.ts` - 错误处理测试
6. `tests/e2e/integration/performance.e2e.test.ts` - 性能基准测试

## 运行方式

```bash
# 方式 1: 使用运行脚本
./scripts/run-e2e-tests.sh

# 方式 2: 直接使用 Playwright
npx playwright test --config=playwright.e2e.config.ts

# 方式 3: 运行特定测试文件
npx playwright test --config=playwright.e2e.config.ts tests/e2e/integration/chat-flow.e2e.test.ts

# 方式 4: 带 UI 模式运行
npx playwright test --config=playwright.e2e.config.ts --ui
```

## 前置条件

1. 确保后端服务运行在 `http://localhost:5000`
2. 确保前端开发服务器运行在 `http://localhost:5173`（或让测试脚本自动启动）
3. 已安装 Playwright 浏览器：`npx playwright install`

## 输出位置

- HTML 报告：`test-results/e2e-report/index.html`
- JSON 结果：`test-results/e2e/results.json`
- 截图（失败时）：`test-results/`
- 视频（失败时）：`test-results/`
