#!/usr/bin/env python3
"""搜索记忆技能"""

from typing import Dict, Any
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from lingxi.core.memory import MemoryManager, MemorySearch


def execute(parameters: Dict[str, Any]) -> str:
    """
    执行记忆搜索
    
    参数：
    - query: 搜索关键词（必填）
    - category: 分类过滤（可选）
    - tags: 标签过滤（可选）
    - top_k: 返回数量（可选，默认 5）
    """
    query = parameters.get("query")
    if not query:
        return "❌ 错误：缺少 query 参数"
    
    category = parameters.get("category")
    tags_param = parameters.get("tags", "")
    top_k = parameters.get("top_k", 5)
    
    # 解析标签
    tags = [t.strip() for t in tags_param.split(',') if t.strip()] if tags_param else []
    
    # 获取记忆管理器
    memory_manager = MemoryManager()
    memory_manager.load_memory()
    search_engine = MemorySearch(memory_manager)
    
    # 搜索
    results = search_engine.search(
        query=query,
        category=category,
        tags=tags,
        top_k=top_k
    )
    
    if not results:
        return f"📚 未找到关于 '{query}' 的记忆"
    
    # 格式化结果
    formatted = []
    formatted.append(f"📚 找到 {len(results)} 条相关记忆：\n")
    
    for i, result in enumerate(results, 1):
        importance_stars = '⭐' * result['importance']
        formatted.append(f"{i}. 【{result['category']}】({importance_stars})")
        formatted.append(f"   {result['content']}")
        if result.get('tags'):
            formatted.append(f"   标签：{', '.join(result['tags'])}")
        formatted.append("")
    
    return "\n".join(formatted)
