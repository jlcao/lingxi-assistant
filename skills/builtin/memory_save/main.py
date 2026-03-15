#!/usr/bin/env python3
"""保存记忆技能"""

from typing import Dict, Any
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from lingxi.core.memory import MemoryManager


def execute(parameters: Dict[str, Any]) -> str:
    """
    保存记忆
    
    参数：
    - content: 记忆内容（必填）
    - category: 分类（可选，默认 note）
    - tags: 标签（可选，逗号分隔）
    - importance: 重要性（可选，1-5，默认 3）
    """
    content = parameters.get("content")
    if not content:
        return "❌ 错误：缺少 content 参数"
    
    category = parameters.get("category", "note")
    tags_param = parameters.get("tags", "")
    importance = parameters.get("importance", 3)
    
    # 解析标签
    tags = [t.strip() for t in tags_param.split(',') if t.strip()] if tags_param else []
    
    # 获取记忆管理器
    memory_manager = MemoryManager()
    memory_manager.load_memory()
    
    # 保存
    memory = memory_manager.save_memory(
        content=content,
        category=category,
        tags=tags,
        importance=importance
    )
    
    importance_stars = '⭐' * memory.importance
    
    # 保存到文件
    memory_manager.save_to_file()
    
    return f"✅ 记忆已保存\n\n内容：{memory.content}\n分类：{memory.category}\n重要性：{importance_stars}"
