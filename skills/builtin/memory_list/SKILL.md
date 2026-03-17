---
name: memory_list
description: 列出所有记忆或按分类列出记忆。用于查看已保存的记忆内容。
version: "1.0.0"
trigger_conditions: "用户要求查看、列出记忆时使用"
execution_guidelines: "1. 支持分类过滤\n2. 支持数量限制\n3. 显示统计信息"
author: "Lingxi Team"
license: MIT
---

# Memory List Skill

列出所有记忆或按分类列出记忆。

## 参数

- **category** (optional): 分类过滤 (preference/fact/decision/todo/note)
- **limit** (optional): 数量限制，默认 20

## 示例

```
# 列出所有记忆
memory_list()

# 列出偏好分类的记忆
memory_list(category="preference")

# 限制数量
memory_list(limit=10)
```
