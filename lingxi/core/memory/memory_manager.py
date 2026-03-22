#!/usr/bin/env python3
"""记忆管理器 - 统一管理所有记忆相关功能"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime
import hashlib
from lingxi.utils.config import get_workspace_path, get_config

logger = logging.getLogger(__name__)


@dataclass
class Memory:
    """记忆数据结构"""
    id: str                    # 记忆 ID (哈希)
    content: str               # 记忆内容
    category: str              # 分类 (preference/fact/decision/todo/note)
    tags: List[str] = field(default_factory=list)  # 标签
    importance: int = 3        # 重要性 (1-5)
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = field(default_factory=lambda: datetime.now().timestamp())
    access_count: int = 0      # 访问次数
    workspace_path: str = ""   # 所属工作目录
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @staticmethod
    def compute_id(content: str, category: str) -> str:
        """计算记忆 ID"""
        text = f"{content}:{category}"
        return hashlib.md5(text.encode()).hexdigest()


class MemoryManager:
    """记忆管理器"""
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self.config = get_config()
        self.workspace_path = get_workspace_path()
        
        # 记忆存储
        self.memories: Dict[str, Memory] = {}  # 内存缓存
        self.memory_file = os.path.join(self.workspace_path, "MEMORY.md")
        
        # 数据库支持
        db_enabled = self.config.get("memory", {}).get("db_enabled", False)
        if db_enabled:
            db_path = self.config.get("memory", {}).get("db_path", "./workspace/memory.db")
            from .memory_database import MemoryDatabase
            self.db = MemoryDatabase(db_path)
            logger.info(f"记忆数据库已启用：{db_path}")
        else:
            self.db = None
        
        # 向量搜索支持
        vector_enabled = self.config.get("memory", {}).get("vector_enabled", False)
        if vector_enabled:
            try:
                from .vector_store import VectorStore
                vector_db_path = self.config.get("memory", {}).get("vector_db_path", "./workspace/chroma_db")
                self.vector_store = VectorStore(vector_db_path)
                logger.info(f"向量搜索已启用：{vector_db_path}")
            except Exception as e:
                logger.warning(f"向量搜索初始化失败：{e}")
                self.vector_store = None
        else:
            self.vector_store = None
        
        # 混合搜索
        if self.vector_store:
            from .hybrid_search import HybridSearch
            self.hybrid_search = HybridSearch(self, self.vector_store)
        else:
            self.hybrid_search = None
        
        self._initialized = True
        logger.info(f"记忆管理器已初始化，工作目录：{self.workspace_path}")
    
    def load_memory(self, workspace_path: str = None) -> int:
        """
        加载 MEMORY.md 文件
        
        Args:
            workspace_path: 工作目录路径
        
        Returns:
            加载的记忆数量
        """
        if workspace_path:
            self.workspace_path = workspace_path
        else:
            self.workspace_path = get_workspace_path()
        self.memory_file = os.path.join(self.workspace_path, "MEMORY.md")
        
        if not os.path.exists(self.memory_file):
            logger.debug(f"MEMORY.md 不存在：{self.memory_file}")
            return 0
        
        try:
            from .memory_parser import MemoryParser
            
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            parser = MemoryParser()
            memories = parser.parse(content)
            
            # 加载到内存
            count = 0
            for memory in memories:
                memory.workspace_path = self.workspace_path
                self.memories[memory.id] = memory
                count += 1
            
            logger.info(f"从 MEMORY.md 加载了 {count} 条记忆")
            return count
            
        except Exception as e:
            logger.error(f"加载 MEMORY.md 失败：{e}")
            return 0
    
    def search_memory(
        self,
        query: str,
        category: str = None,
        tags: List[str] = None,
        top_k: int = 5,
        use_vector: bool = True,
        vector_weight: float = 0.5
    ) -> List[Memory]:
        """
        搜索记忆（支持混合搜索）
        
        Args:
            query: 搜索关键词
            category: 分类过滤
            tags: 标签过滤
            top_k: 返回数量
            use_vector: 是否使用向量搜索
            vector_weight: 向量搜索权重 (0-1)
        
        Returns:
            匹配的记忆列表
        """
        # 使用混合搜索
        if self.hybrid_search and use_vector:
            results = self.hybrid_search.search(
                query=query,
                category=category,
                tags=tags,
                top_k=top_k,
                vector_weight=vector_weight
            )
            
            # 转换为 Memory 对象
            memories = []
            for result in results:
                # 移除融合相关的临时字段
                result_copy = {k: v for k, v in result.items() 
                              if k not in ['fused_score', 'keyword_rank', 'vector_rank']}
                memory = Memory(**result_copy)
                memories.append(memory)
            
            return memories
        
        # 降级到关键词搜索
        # 优先从数据库搜索
        if self.db:
            db_results = self.db.search_memories(
                query=query,
                category=category,
                tags=tags,
                workspace_path=self.workspace_path,
                limit=top_k * 2  # 多取一些用于评分
            )
            
            # 转换为 Memory 对象
            memories = []
            for data in db_results:
                memory = Memory(**data)
                memories.append(memory)
            
            # 评分和排序
            query_lower = query.lower()
            scored_memories = []
            for memory in memories:
                score = 0
                if query_lower in memory.content.lower():
                    score += 10
                if any(query_lower in tag.lower() for tag in memory.tags):
                    score += 5
                score += memory.importance
                score += min(memory.access_count, 10)
                
                if score > 0:
                    scored_memories.append((score, memory))
            
            scored_memories.sort(key=lambda x: x[0], reverse=True)
            results = [m for s, m in scored_memories[:top_k]]
            
            # 更新访问计数
            if self.db:
                for memory in results:
                    memory.access_count += 1
                    self.db.update_access_count(memory.id, query)
            
            return results
        
        # 降级到内存搜索
        memories = list(self.memories.values())
        
        # 分类过滤
        if category:
            memories = [m for m in memories if m.category == category]
        
        # 标签过滤
        if tags:
            memories = [m for m in memories if any(t in m.tags for t in tags)]
        
        # 关键词匹配
        query_lower = query.lower()
        scored_memories = []
        
        for memory in memories:
            score = 0
            
            # 内容匹配
            if query_lower in memory.content.lower():
                score += 10
            
            # 标签匹配
            if any(query_lower in tag.lower() for tag in memory.tags):
                score += 5
            
            # 重要性加权
            score += memory.importance
            
            # 访问次数加权
            score += min(memory.access_count, 10)
            
            if score > 0:
                scored_memories.append((score, memory))
        
        # 按分数排序
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        
        # 返回 top_k 并增加访问计数
        results = []
        for score, memory in scored_memories[:top_k]:
            memory.access_count += 1
            results.append(memory)
        
        return results
    
    def save_memory(
        self,
        content: str,
        category: str = "note",
        tags: List[str] = None,
        importance: int = 3,
        metadata: Dict[str, Any] = None
    ) -> Memory:
        """
        保存新记忆
        
        Args:
            content: 记忆内容
            category: 分类
            tags: 标签
            importance: 重要性 (1-5)
            metadata: 额外元数据
        
        Returns:
            保存的记忆对象
        """
        # 检查是否已存在
        memory_id = Memory.compute_id(content, category)
        if memory_id in self.memories:
            logger.debug(f"记忆已存在：{memory_id}")
            return self.memories[memory_id]
        
        # 创建新记忆
        memory = Memory(
            id=memory_id,
            content=content,
            category=category,
            tags=tags or [],
            importance=importance,
            created_at=datetime.now().timestamp(),
            updated_at=datetime.now().timestamp(),
            access_count=0,
            workspace_path=self.workspace_path,
            metadata=metadata or {}
        )
        
        # 保存到内存
        self.memories[memory.id] = memory
        
        # 保存到数据库
        if self.db:
            self.db.save_memory(memory.to_dict())
        
        logger.info(f"保存记忆：{memory.id} ({memory.category})")
        return memory
    
    def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        if memory_id in self.memories:
            del self.memories[memory_id]
            logger.info(f"删除记忆：{memory_id}")
            return True
        return False
    
    def update_memory(self, memory_id: str, **kwargs) -> Optional[Memory]:
        """更新记忆"""
        if memory_id not in self.memories:
            return None
        
        memory = self.memories[memory_id]
        
        # 更新字段
        for key, value in kwargs.items():
            if hasattr(memory, key):
                setattr(memory, key, value)
        
        memory.updated_at = datetime.now().timestamp()
        
        logger.info(f"更新记忆：{memory_id}")
        return memory
    
    def get_memories_by_category(self, category: str = None) -> List[Memory]:
        """按分类获取记忆"""
        memories = list(self.memories.values())
        if category:
            memories = [m for m in memories if m.category == category]
        return memories
    
    def get_memory_stats(self) -> dict:
        """获取记忆统计信息"""
        if self.db:
            return self.db.get_stats(self.workspace_path)
        
        # 降级到内存统计
        stats = {
            "total": len(self.memories),
            "by_category": {},
            "by_importance": {i: 0 for i in range(1, 6)},
            "workspace_path": self.workspace_path
        }
        
        for memory in self.memories.values():
            # 按分类统计
            cat = memory.category
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1
            
            # 按重要性统计
            stats["by_importance"][memory.importance] += 1
        
        return stats
    
    def save_to_file(self):
        """保存记忆到 MEMORY.md 文件"""
        try:
            # 按分类组织
            by_category = {}
            for memory in self.memories.values():
                cat = memory.category
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(memory)
            
            # 生成文件内容
            lines = []
            lines.append("# MEMORY.md - 长期记忆")
            lines.append("")
            lines.append(f"**最后更新：** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            lines.append("")
            
            # 分类映射
            category_names = {
                "preference": "用户偏好",
                "fact": "重要事实",
                "decision": "历史决策",
                "todo": "待办事项",
                "note": "笔记"
            }
            
            for cat, memories in by_category.items():
                cat_name = category_names.get(cat, cat)
                lines.append(f"## {cat_name}")
                lines.append("")
                
                for memory in sorted(memories, key=lambda m: m.importance, reverse=True):
                    lines.append(f"- {memory.content}")
                
                lines.append("")
            
            # 写入文件
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                f.write("\n".join(lines))
            
            logger.info(f"记忆已保存到：{self.memory_file}")
            
        except Exception as e:
            logger.error(f"保存 MEMORY.md 失败：{e}")
