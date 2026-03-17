---
name: memory_save
description: 保存新的长期记忆。当用户明确要求记住某些内容时使用此技能。
version: "1.0.0"
trigger_conditions: "用户要求记住、记录、保存某些信息时触发"
execution_guidelines: "1. 验证 content 参数\n2. 支持分类选择\n3. 支持标签和重要性设置"
author: "Lingxi Team"
license: MIT
---

# Memory Save Skill

保存新的长期记忆。

## 参数

- **content** (required): 记忆内容
- **category** (optional): 分类 (preference/fact/decision/todo/note)，默认 note
- **tags** (optional): 标签，逗号分隔
- **importance** (optional): 重要性 (1-5)，默认 3

## 示例

```
# 保存用户偏好
memory_save(content="我喜欢使用 TypeScript", category="preference", importance=4)

# 保存重要事实
memory_save(content="当前项目是灵犀助手 v2.0", category="fact", tags="project,work", importance=5)

# 保存待办事项
memory_save(content="记得实现向量搜索功能", category="todo", importance=3)
```
