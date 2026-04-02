#!/usr/bin/env python3
"""Contract Review skill implementation - provides contract compliance review functionality"""

import logging
import os
from typing import Dict, Any

# 模块级别的调用计数器
_call_count = 0


def execute(parameters: Dict[str, Any]) -> str:
    """Execute Contract Review skill

    Args:
        parameters: Parameters dictionary

    Returns:
        Contract Review skill usage documentation or brief confirmation
    """
    global _call_count
    _call_count += 1

    logger = logging.getLogger(__name__)

    logger.info(f"执行合同审查技能，参数: {parameters}")

    try:
        skill_dir = os.path.dirname(__file__)
        skill_md_path = os.path.join(skill_dir, "SKILL.md")

        if not os.path.exists(skill_md_path):
            return "合同审查技能已加载，但需要根据具体任务调用相应的工具脚本。"

        with open(skill_md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 提取YAML frontmatter后的内容
        if content.startswith('---'):
            end_idx = content.find('---', 3)
            if end_idx > 0:
                documentation = content[end_idx + 3:].strip()

                # 智能返回策略：
                # 1. 第一次调用返回完整说明
                # 2. 后续调用返回简短确认
                if _call_count == 1:
                    return f"合同审查技能使用说明:\n\n{documentation}\n\n注意: 此技能需要根据具体任务调用相应的工具脚本。"
                else:
                    return "合同审查技能已加载，但需要根据具体任务调用相应的工具脚本。"

        return "合同审查技能已加载，但需要根据具体任务调用相应的工具脚本。"

    except Exception as e:
        logger.error(f"执行合同审查技能失败: {e}")
        return f"错误: 合同审查技能执行失败 - {str(e)}"
