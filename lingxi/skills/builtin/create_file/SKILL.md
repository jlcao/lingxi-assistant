---
name: create_file
description: "创建或写入文件，支持追加模式、自动创建父目录"
version: "2.0.0"
trigger_conditions: "用户请求创建文件、写入文件内容、追加内容到文件时触发"
execution_guidelines: "1. 验证 file_path 参数是否为绝对路径\n2. 自动创建父目录\n3. 支持写入和追加两种模式\n4. 使用 UTF-8 编码"
author: "Lingxi Team"
license: MIT
---

# Create File Skill v2.0

## 新增功能

- ✅ **追加模式** - 支持向文件追加内容
- ✅ **自动创建父目录** - 如果父目录不存在自动创建
- ✅ **编码支持** - 可指定文件编码

## 参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| **file_path** | string | ✅ | - | 文件绝对路径 |
| **content** | string | ❌ | "" | 文件内容 |
| **mode** | string | ❌ | "write" | 写入模式："write" 或 "append" |
| **create_parent_dirs** | boolean | ❌ | true | 自动创建父目录 |
| **encoding** | string | ❌ | "utf-8" | 文件编码 |

## 使用示例

```python
# 创建新文件
create_file(
    file_path="/path/to/file.txt",
    content="Hello, World!"
)

# 追加内容到文件
create_file(
    file_path="/path/to/file.txt",
    content="\nAdditional content",
    mode="append"
)

# 创建嵌套目录的文件
create_file(
    file_path="/path/to/nested/dir/file.txt",
    content="Content",
    create_parent_dirs=true
)

# 指定编码创建文件
create_file(
    file_path="/path/to/gbk_file.txt",
    content="内容",
    encoding="gbk"
)
```

## 依赖

None
