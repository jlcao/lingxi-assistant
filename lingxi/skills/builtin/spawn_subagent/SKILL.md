---
name: spawn_subagent
description: 创建子代理来执行任务
version: 1.0.0
author: Lingxi Team
license: MIT
---
# Spawn Subagent - 创建子代理技能

## 功能描述
手动创建子代理来执行任务。当需要显式创建子代理并行执行任务时使用此技能。

## 使用场景
- 需要并行执行多个独立任务
- 需要后台执行长时间运行的任务
- 需要手动控制子代理的创建和执行

## 参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| task | string | 是 | - | 任务描述 |
| workspace_path | string | 否 | null | 工作目录路径 |
| timeout | number | 否 | 300 | 超时时间（秒） |
| wait | boolean | 否 | true | 是否等待任务完成 |

## 使用示例

### 示例 1：创建子代理并等待完成
```json
{
  "skill": "spawn_subagent",
  "parameters": {
    "task": "分析项目代码结构",
    "wait": true
  }
}
```

### 示例 2：创建子代理在后台执行
```json
{
  "skill": "spawn_subagent",
  "parameters": {
    "task": "运行单元测试",
    "timeout": 600,
    "wait": false
  }
}
```

### 示例 3：指定工作目录
```json
{
  "skill": "spawn_subagent",
  "parameters": {
    "task": "构建项目",
    "workspace_path": "/home/admin/my-project",
    "timeout": 300
  }
}
```

## 返回格式

### 等待完成（wait=true）
```
子代理任务完成
任务 ID: xxx-xxx-xxx
状态：completed
结果：任务执行结果...
```

### 不等待（wait=false）
```
子代理已创建，任务 ID: xxx-xxx-xxx
状态：pending
使用 wait=False，任务在后台执行
```

## 注意事项
- 子代理任务会创建独立的会话执行
- 超时时间默认 300 秒（5 分钟）
- 长时间任务建议设置 wait=false 并在之后查询状态
- 子代理调度器必须已初始化才能使用此技能

## 相关技能
- 无（子代理功能是引擎层自动检测的，此技能用于手动控制）
