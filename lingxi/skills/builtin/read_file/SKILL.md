---
name: read_file
description: "读取文件内容，支持搜索、流式读取、编码自动检测"
version: "2.0.0"
trigger_conditions: "用户请求读取文件、查看文件内容、搜索文件中的文本时触发"
execution_guidelines: "1. 验证 file_path 参数是否为绝对路径\n2. 大文件自动使用流式读取\n3. 自动检测文件编码\n4. 搜索时显示上下文"
author: "Lingxi Team"
license: MIT
---

# Read File Skill v2.0

## 新增功能

- ✅ **流式读取** - 支持大文件分块读取，避免内存溢出
- ✅ **编码检测** - 自动检测文件编码（支持 UTF-8、GBK、Big5 等）
- ✅ **行数限制** - 默认限制 1000 行，防止输出过大
- ✅ **搜索增强** - 支持不区分大小写搜索

## 参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| **file_path** | string | ✅ | - | 文件绝对路径 |
| **search_text** | string | ❌ | - | 搜索关键词 |
| **context_lines** | number | ❌ | 5 | 搜索上下文行数 |
| **stream** | boolean | ❌ | false | 是否流式读取 |
| **chunk_size** | number | ❌ | 8192 | 流式读取块大小（字节） |
| **max_lines** | number | ❌ | 1000 | 最大读取行数 |
| **encoding** | string | ❌ | - | 文件编码（可选） |
| **detect_encoding** | boolean | ❌ | true | 自动检测编码 |

## 使用示例

```python
# 读取小文件
read_file(file_path="/path/to/file.txt")

# 搜索文件内容
read_file(
    file_path="/path/to/file.txt",
    search_text="Python",
    context_lines=3
)

# 流式读取大文件
read_file(
    file_path="/path/to/large.log",
    stream=true,
    chunk_size=16384,
    max_lines=5000
)

# 指定编码读取
read_file(
    file_path="/path/to/gbk_file.txt",
    encoding="gbk",
    detect_encoding=false
)
```

## 依赖

- `chardet` - 编码检测库
