#!/usr/bin/env python3
"""记忆搜索引擎"""

import logging
from typing import List, Dict, Any
from .memory_manager import Memory, MemoryManager

logger = logging.getLogger(__name__)


class MemorySearch:
    """记忆搜索引擎"""
    
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
    
    def search(
        self,
        query: str,
        category: str = None,
        tags: List[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        搜索记忆
        
        Args:
            query: 搜索词
            category: 分类过滤
            tags: 标签过滤
            top_k: 返回数量
        
        Returns:
            搜索结果列表（包含分数）
        """
        memories = self.memory_manager.search_memory(
            query=query,
            category=category,
            tags=tags,
            top_k=top_k
        )
        
        # 转换为字典并添加分数（简化版，实际分数在 search_memory 中计算）
        results = []
        for memory in memories:
            result = memory.to_dict()
            result["score"] = memory.access_count  # 简化分数
            results.append(result)
        
        return results
    
    def search_by_category(self, category: str, limit: int = 20) -> List[Dict[str, Any]]:
        """按分类搜索"""
        memories = self.memory_manager.get_memories_by_category(category)
        memories.sort(key=lambda m: (m.importance, m.access_count), reverse=True)
        memories = memories[:limit]
        
        return [m.to_dict() for m in memories]
