---
name: memory_search
description: 搜索长期记忆。当用户询问之前提到的内容、偏好、习惯或历史决策时使用此技能。
version: "1.0.0"
trigger_conditions: "用户询问记忆、历史、偏好、习惯时触发"
execution_guidelines: "1. 验证 query 参数\n2. 支持分类过滤\n3. 支持标签过滤\n4. 返回格式化的搜索结果"
author: "Lingxi Team"
license: MIT
---

# Memory Search Skill

搜索长期记忆，支持关键词搜索、分类过滤和标签过滤。

## 参数

- **query** (required): 搜索关键词
- **category** (optional): 分类过滤 (preference/fact/decision/todo/note)
- **tags** (optional): 标签过滤，逗号分隔
- **top_k** (optional): 返回数量，默认 5

## 示例

```
# 搜索所有相关记忆
memory_search(query="编程语言")

# 按分类搜索
memory_search(query="代码", category="preference")

# 按标签搜索
memory_search(query="项目", tags="work,project")
```
