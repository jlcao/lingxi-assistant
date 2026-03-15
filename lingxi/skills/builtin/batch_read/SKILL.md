---
name: batch_read
description: "批量读取多个文件，支持通配符匹配和大小限制"
version: "1.0.0"
trigger_conditions: "用户请求读取多个文件、查看项目结构、批量分析代码时触发"
execution_guidelines: "1. 验证文件路径\n2. 限制文件大小\n3. 限制文件数量"
author: "Lingxi Team"
license: MIT
---

# Batch Read Skill

批量读取多个文件内容。

## 参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| **file_paths** | string[] | ❌ | [] | 文件路径列表 |
| **pattern** | string | ❌ | - | 文件匹配模式（如 "*.py"） |
| **directory** | string | ❌ | - | 搜索目录 |
| **max_files** | number | ❌ | 20 | 最大文件数 |
| **max_size_per_file** | number | ❌ | 102400 | 单文件最大字节数 |
| **encoding** | string | ❌ | "utf-8" | 文件编码 |

## 使用示例

```python
# 读取指定文件列表
batch_read(
    file_paths=[
        "/path/to/file1.py",
        "/path/to/file2.py",
        "/path/to/file3.py"
    ]
)

# 使用通配符读取目录下所有 Python 文件
batch_read(
    pattern="*.py",
    directory="/path/to/project",
    max_files=10
)

# 读取配置文件
batch_read(
    pattern="*.json",
    directory="/path/to/config",
    max_size_per_file=51200
)
```

## 注意事项

- 默认最多读取 20 个文件
- 单个文件默认最大 100KB
- 超过大小限制的文件会被跳过
- 使用 directory + pattern 可以递归搜索文件
