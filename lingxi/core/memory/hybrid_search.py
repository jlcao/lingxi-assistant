#!/usr/bin/env python3
"""混合搜索引擎 - 结合关键词搜索和向量语义搜索"""

import logging
from typing import List, Dict, Any
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class HybridSearch:
    """混合搜索引擎"""
    
    def __init__(self, memory_manager, vector_store: VectorStore = None):
        """
        初始化混合搜索引擎
        
        Args:
            memory_manager: MemoryManager 实例
            vector_store: VectorStore 实例（可选）
        """
        self.memory_manager = memory_manager
        self.vector_store = vector_store
    
    def search(
        self,
        query: str,
        category: str = None,
        tags: List[str] = None,
        top_k: int = 5,
        use_vector: bool = True,
        vector_weight: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        混合搜索（关键词 + 向量）
        
        Args:
            query: 搜索查询
            category: 分类过滤
            tags: 标签过滤
            top_k: 返回数量
            use_vector: 是否使用向量搜索
            vector_weight: 向量搜索权重 (0-1)
        
        Returns:
            搜索结果列表（带融合分数）
        """
        # 关键词搜索结果
        keyword_results = self.memory_manager.search_memory(
            query=query,
            category=category,
            tags=tags,
            top_k=top_k * 2  # 多取一些用于融合
        )
        
        # 向量搜索结果
        vector_results = []
        if use_vector and self.vector_store and self.vector_store.is_available():
            vector_results = self.vector_store.search(
                query=query,
                n_results=top_k * 2,
                category=category
            )
        
        # 如果没有向量搜索结果，只返回关键词搜索结果
        if not vector_results:
            return self._format_results(keyword_results)[:top_k]
        
        # 融合搜索结果
        fused_results = self._fuse_results(
            keyword_results,
            vector_results,
            vector_weight=vector_weight
        )
        
        return fused_results[:top_k]
    
    def _format_results(self, memories) -> List[Dict[str, Any]]:
        """格式化结果为统一格式"""
        results = []
        for memory in memories:
            if hasattr(memory, 'to_dict'):
                result = memory.to_dict()
            else:
                result = memory
            
            # 添加分数
            if 'score' not in result:
                result['score'] = result.get('access_count', 0)
            
            results.append(result)
        
        return results
    
    def _fuse_results(
        self,
        keyword_results,
        vector_results,
        vector_weight: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        融合关键词和向量搜索结果
        
        使用 Reciprocal Rank Fusion (RRF) 算法
        """
        # 格式化结果
        keyword_results = self._format_results(keyword_results)
        
        # 创建排名映射
        keyword_rank = {}
        for i, result in enumerate(keyword_results):
            keyword_rank[result['id']] = i + 1
        
        vector_rank = {}
        for i, result in enumerate(vector_results):
            vector_rank[result['id']] = i + 1
        
        # 合并所有结果
        all_results = {}
        for result in keyword_results + vector_results:
            if result['id'] not in all_results:
                all_results[result['id']] = result.copy()
        
        # 计算融合分数
        k = 60  # RRF 常数
        for result_id, result in all_results.items():
            keyword_reciprocal_rank = 1.0 / (k + keyword_rank.get(result_id, len(keyword_results) + 1))
            vector_reciprocal_rank = 1.0 / (k + vector_rank.get(result_id, len(vector_results) + 1))
            
            # 融合分数
            fused_score = (
                (1 - vector_weight) * keyword_reciprocal_rank +
                vector_weight * vector_reciprocal_rank
            )
            
            result['fused_score'] = fused_score
            result['keyword_rank'] = keyword_rank.get(result_id, 0)
            result['vector_rank'] = vector_rank.get(result_id, 0)
        
        # 按融合分数排序
        sorted_results = sorted(
            all_results.values(),
            key=lambda x: x['fused_score'],
            reverse=True
        )
        
        logger.debug(f"融合搜索：关键词{len(keyword_results)}条，向量{len(vector_results)}条，融合后{len(sorted_results)}条")
        
        return sorted_results
