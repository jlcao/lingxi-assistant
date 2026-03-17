---
name: apply_patch
description: "应用统一 diff 格式补丁到文件，支持预览和备份"
version: "1.0.0"
trigger_conditions: "用户请求应用补丁、应用 diff、代码重构时触发"
execution_guidelines: "1. 验证 patch_text 格式\n2. 默认创建备份\n3. 支持 dry_run 预览"
author: "Lingxi Team"
license: MIT
---

# Apply Patch Skill

应用统一 diff 格式补丁到目标文件。

## 参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| **file_path** | string | ✅ | - | 目标文件路径 |
| **patch_text** | string | ✅ | - | 统一 diff 格式补丁 |
| **dry_run** | boolean | ❌ | false | 仅预览不应用 |
| **backup** | boolean | ❌ | true | 创建备份文件 |

## 使用示例

```python
# 应用补丁
apply_patch(
    file_path="/path/to/file.py",
    patch_text="""--- a/file.py
+++ b/file.py
@@ -10,3 +10,4 @@
 line 10
-old line 11
+new line 11
 line 12
+new line 13
"""
)

# 预览补丁（不应用）
apply_patch(
    file_path="/path/to/file.py",
    patch_text="...",
    dry_run=true
)

# 应用补丁但不创建备份
apply_patch(
    file_path="/path/to/file.py",
    patch_text="...",
    backup=false
)
```

## Diff 格式

支持标准统一 diff 格式：

```diff
--- a/file.py
+++ b/file.py
@@ -10,3 +10,4 @@
 context line
-removed line
+added line
 context line
```

## 注意事项

- 补丁必须是统一 diff（unified diff）格式
- 默认会创建 .bak 备份文件
- 使用 dry_run=true 可以先预览变更效果
