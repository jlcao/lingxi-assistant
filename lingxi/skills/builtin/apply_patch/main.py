#!/usr/bin/env python3
"""Apply patch skill - 应用统一 diff 格式补丁"""

import logging
import os
from typing import Dict, Any, List
from difflib import unified_diff


def execute(parameters: Dict[str, Any]) -> str:
    """
    应用 diff 补丁到文件

    Args:
        parameters: Parameters dictionary
            - file_path: 目标文件路径（必填）
            - patch_text: 统一 diff 格式补丁（必填）
            - dry_run: 是否仅预览不应用（可选，默认 false）
            - backup: 是否创建备份（可选，默认 true）

    Returns:
        应用结果
    """
    logger = logging.getLogger(__name__)

    file_path = parameters.get("file_path")
    patch_text = parameters.get("patch_text")
    dry_run = parameters.get("dry_run", False)
    backup = parameters.get("backup", True)

    if not file_path:
        return "❌ 错误：缺少 file_path 参数"

    if not patch_text:
        return "❌ 错误：缺少 patch_text 参数"

    if not os.path.exists(file_path):
        return f"❌ 错误：文件不存在 - {file_path}"

    logger.info(f"应用补丁到：{file_path} (预览：{dry_run}, 备份：{backup})")

    try:
        # 解析补丁
        changes = _parse_unified_diff(patch_text, logger)

        if not changes:
            logger.error("无法解析补丁")
            return "❌ 错误：无法解析补丁，请确保是统一 diff 格式"

        logger.info(f"解析到 {len(changes)} 处变更")

        # 读取原文件
        with open(file_path, 'r', encoding='utf-8') as f:
            original_lines = f.readlines()

        # 应用补丁
        modified_lines = _apply_changes(original_lines, changes, logger)

        if dry_run:
            # 预览模式：显示 diff
            diff = list(unified_diff(
                original_lines,
                modified_lines,
                fromfile='a/' + os.path.basename(file_path),
                tofile='b/' + os.path.basename(file_path)
            ))
            logger.info("预览模式，未应用补丁")
            return "🔍 预览模式（未应用补丁）:\n\n" + ''.join(diff)

        # 创建备份
        backup_path = None
        if backup:
            backup_path = file_path + '.bak'
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.writelines(original_lines)
            logger.info(f"已创建备份：{backup_path}")

        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(modified_lines)

        logger.info(f"补丁应用成功：{file_path}")
        return f"✅ 补丁应用成功：{file_path}\n修改行数：{len(changes)}\n备份文件：{backup_path if backup else '未创建'}"

    except Exception as e:
        logger.error(f"应用补丁失败：{e}")
        return f"❌ 应用失败：{e}"


def _parse_unified_diff(patch_text: str, logger: logging.Logger) -> List[Dict[str, Any]]:
    """
    解析统一 diff 格式

    返回变更列表：
    [
        {
            "operation": "add" | "remove" | "replace",
            "line_number": 10,
            "old_text": "old line",
            "new_text": "new line"
        }
    ]
    """
    changes = []
    current_line = 0

    for line in patch_text.split('\n'):
        if line.startswith('@@'):
            # 解析行号 @@ -10,3 +10,4 @@
            parts = line.split()
            if len(parts) >= 3:
                old_range = parts[1]  # -10,3
                current_line = int(old_range.split(',')[0].replace('-', ''))
                logger.debug(f"解析到行号标记：{current_line}")

        elif line.startswith('+') and not line.startswith('+++'):
            # 新增行
            changes.append({
                "operation": "add",
                "line_number": current_line,
                "new_text": line[1:]
            })
            current_line += 1

        elif line.startswith('-') and not line.startswith('---'):
            # 删除行
            changes.append({
                "operation": "remove",
                "line_number": current_line,
                "old_text": line[1:]
            })

        elif line.startswith(' '):
            # 上下文（未变更）
            current_line += 1

    return changes


def _apply_changes(original_lines: List[str], changes: List[Dict[str, Any]], logger: logging.Logger) -> List[str]:
    """应用变更到原文件"""
    modified_lines = original_lines.copy()
    offset = 0

    # 按行号排序变更，确保按顺序应用
    sorted_changes = sorted(changes, key=lambda x: x['line_number'])

    for change in sorted_changes:
        line_idx = change['line_number'] - 1 + offset

        if change['operation'] == 'add':
            # 确保不越界
            if line_idx + 1 > len(modified_lines):
                modified_lines.append(change['new_text'] + '\n')
            else:
                modified_lines.insert(line_idx + 1, change['new_text'] + '\n')
            offset += 1
            logger.debug(f"添加行 {line_idx + 1}: {change['new_text'][:50]}")

        elif change['operation'] == 'remove':
            if 0 <= line_idx < len(modified_lines):
                removed = modified_lines.pop(line_idx)
                offset -= 1
                logger.debug(f"删除行 {line_idx + 1}: {removed[:50]}")

    return modified_lines
