#!/usr/bin/env python3
"""列出记忆技能"""

from typing import Dict, Any
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from lingxi.core.memory import MemoryManager


def execute(parameters: Dict[str, Any]) -> str:
    """
    列出记忆
    
    参数：
    - category: 分类过滤（可选）
    - limit: 数量限制（可选，默认 20）
    """
    category = parameters.get("category")
    limit = parameters.get("limit", 20)
    
    memory_manager = MemoryManager()
    memory_manager.load_memory()
    
    # 获取统计
    stats = memory_manager.get_memory_stats()
    
    # 获取记忆
    memories = memory_manager.get_memories_by_category(category)
    memories.sort(key=lambda m: (m.importance, m.access_count), reverse=True)
    memories = memories[:limit]
    
    if not memories:
        if category:
            return f"📚 {category} 分类下暂无记忆"
        else:
            return "📚 暂无记忆"
    
    # 格式化
    formatted = []
    
    if category:
        formatted.append(f"📚 {category} 分类记忆 (共{len(memories)}条)\n")
    else:
        formatted.append(f"📚 记忆列表 (共{len(memories)}条)\n")
    
    for i, memory in enumerate(memories, 1):
        importance_stars = '⭐' * memory.importance
        content_preview = memory.content[:100] + "..." if len(memory.content) > 100 else memory.content
        
        formatted.append(f"{i}. 【{memory.category}】{importance_stars}")
        formatted.append(f"   {content_preview}")
        if memory.tags:
            formatted.append(f"   标签：{', '.join(memory.tags)}")
        formatted.append("")
    
    # 添加统计信息
    formatted.append("\n---")
    formatted.append(f"\n总记忆数：{stats['total']}")
    formatted.append(f"\n按分类:")
    for cat, count in stats['by_category'].items():
        formatted.append(f"  - {cat}: {count}")
    
    return "\n".join(formatted)
