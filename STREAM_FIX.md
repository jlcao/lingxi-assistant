# 流式响应修复说明

## 问题描述

**现象**: 前端发送流式请求后，任务在 `base.py#L617-618` 返回生成器后被"夯住"，无法继续执行。

**日志表现**:
```
🚀 任务开始处理...
2026-03-06 14:27:19,768 - lingxi.core.event.SessionStore_subscriber - INFO - 收到 task_start 事件
2026-03-06 14:27:19,780 - lingxi.core.event.SessionStore_subscriber - INFO - 创建任务
2026-03-06 14:27:19,796 - lingxi.core.event.SessionStore_subscriber - INFO - 任务创建成功
# 之后没有任何输出，任务被夯住
```

## 根本原因

在 `lingxi/web/stream_executor.py` 中，`execute_with_stream_events` 函数使用 `asyncio.to_thread()` 在后台线程中执行引擎：

```python
def run_engine():
    set_ids(session_id, task_id, execution_id, task)
    return engine.process(task, task_info, history, session_id, stream)  # 返回生成器

async with StreamEventCollector(session_id, execution_id) as collector:
    task_executor = asyncio.create_task(
        asyncio.to_thread(run_engine)
    )
    async for event in collector.events():
        yield event
```

**问题**: 当 `stream=True` 时，`engine.process()` 返回一个**生成器对象**，但生成器对象本身不会自动执行。它需要被消费（迭代）才能触发实际的执行逻辑。

在后台线程中，生成器被创建后立即返回，但主线程只等待 `task_executor` 完成，并没有消费这个生成器，导致：
1. 生成器没有被迭代
2. `_execute_task_stream` 方法没有被调用
3. 事件没有被发布
4. 前端收不到任何响应

## 解决方案

在后台线程中消费生成器，触发实际执行：

```python
def run_engine():
    set_ids(session_id, task_id, execution_id, task)
    result = engine.process(task, task_info, history, session_id, stream)
    # 如果返回的是生成器，需要消费它以触发实际执行
    if hasattr(result, '__iter__'):
        # 消费生成器以触发实际执行
        for _ in result:
            pass
    return result
```

## 修复文件

- `lingxi/web/stream_executor.py` - 修改 `run_engine` 函数，添加生成器消费逻辑

## 修复验证

### 方法 1: 使用测试脚本

```bash
python test_stream_fix.py
```

### 方法 2: 手动测试

1. 启动 Web 服务器：
   ```bash
   python start_web_server.py
   ```

2. 使用 curl 测试：
   ```bash
   curl -X POST http://localhost:8000/api/tasks/stream \
     -H "Content-Type: application/json" \
     -H "Accept: text/event-stream" \
     -d '{"session_id": "session_xxx", "task": "翻译：Hello, World! 到中文"}'
   ```

3. 观察日志输出，应该能看到完整的事件流：
   ```
   task_start -> think_start -> think_stream -> think_final -> task_end -> stream_end
   ```

### 方法 3: 前端测试

在前端应用中发送流式请求，观察是否能正常接收事件。

## 技术细节

### 生成器执行机制

生成器是惰性求值的，只有被迭代时才会执行：

```python
def my_generator():
    print("开始执行")
    yield 1
    print("继续执行")
    yield 2

# 这不会打印任何内容
gen = my_generator()

# 这会触发执行
for item in gen:
    print(item)
```

### asyncio.to_thread() 行为

`asyncio.to_thread()` 会在单独的线程中运行同步函数：

```python
async def main():
    result = await asyncio.to_thread(sync_function)
    # 如果 sync_function 返回生成器，生成器不会自动执行
```

### 事件驱动架构

系统使用事件驱动架构，引擎执行过程中发布事件：

```
引擎执行 -> 发布事件 -> StreamEventCollector 收集 -> 前端接收
```

如果生成器不被消费，引擎不会执行，事件也不会发布。

## 相关代码

### base.py#L617-618

```python
if stream:
    return stream_generator()  # 返回生成器对象
else:
    for _ in stream_generator():
        pass
    return ""
```

### stream_executor.py (修复前)

```python
def run_engine():
    set_ids(session_id, task_id, execution_id, task)
    return engine.process(task, task_info, history, session_id, stream)
```

### stream_executor.py (修复后)

```python
def run_engine():
    set_ids(session_id, task_id, execution_id, task)
    result = engine.process(task, task_info, history, session_id, stream)
    # 如果返回的是生成器，需要消费它以触发实际执行
    if hasattr(result, '__iter__'):
        for _ in result:
            pass
    return result
```

## 影响范围

- ✅ 修复前端流式请求被夯住的问题
- ✅ 不影响命令行模式（命令行模式不使用 stream_executor）
- ✅ 不影响非流式请求
- ✅ 事件收集器正常工作
- ✅ SSE 流式响应正常

## 测试用例

### 测试 1: 简单任务
```json
{
  "session_id": "session_xxx",
  "task": "翻译：Hello 到中文"
}
```

### 测试 2: 复杂任务
```json
{
  "session_id": "session_xxx",
  "task": "分析当前目录下的文件结构"
}
```

### 测试 3: 错误处理
```json
{
  "session_id": "session_xxx",
  "task": ""  // 空任务
}
```

## 总结

**问题**: 生成器在后台线程中创建但未被消费，导致任务执行被阻塞。

**解决**: 在后台线程中消费生成器，触发实际执行。

**验证**: 通过测试脚本和手动测试确认修复有效。

现在流式响应应该能正常工作了！🎉
