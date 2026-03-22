#!/usr/bin/env python3
"""用户记忆和工作记忆管理器"""

import os
import logging
from typing import Dict, Any, List, Optional
from .memory_manager import MemoryManager, Memory

logger = logging.getLogger(__name__)


class UserMemoryManager:
    """用户记忆管理器（单例）
    
    管理跨项目的用户级记忆，如用户偏好、个人信息等
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        # 获取用户记忆存储路径
        self.user_memory_path = "~/.lingxi/memory"
        # 扩展用户目录路径
        self.user_memory_path = os.path.expanduser(self.user_memory_path)
        # 确保用户目录存在
        os.makedirs(self.user_memory_path, exist_ok=True)
        
        # 初始化记忆管理器
        self.memory_manager = MemoryManager()
        # 加载用户记忆
        self.memory_manager.load_memory(self.user_memory_path)
        
        self._initialized = True
        logger.info(f"用户记忆管理器已初始化，存储路径：{self.user_memory_path}")
    
    def save_memory(
        self,
        content: str,
        category: str = "note",
        tags: List[str] = None,
        importance: int = 3,
        metadata: Dict[str, Any] = None
    ) -> Memory:
        """保存用户记忆"""
        return self.memory_manager.save_memory(
            content=content,
            category=category,
            tags=tags,
            importance=importance,
            metadata=metadata
        )
    
    def search_memory(
        self,
        query: str,
        category: str = None,
        tags: List[str] = None,
        top_k: int = 5,
        use_vector: bool = True,
        vector_weight: float = 0.5
    ) -> List[Memory]:
        """搜索用户记忆"""
        return self.memory_manager.search_memory(
            query=query,
            category=category,
            tags=tags,
            top_k=top_k,
            use_vector=use_vector,
            vector_weight=vector_weight
        )
    
    def save_to_file(self):
        """持久化用户记忆到文件"""
        self.memory_manager.save_to_file()
        logger.info("用户记忆已持久化")
    
    def get_stats(self) -> dict:
        """获取用户记忆统计信息"""
        return self.memory_manager.get_memory_stats()
    
    def load_all_memories(self) -> int:
        """加载所有用户记忆
        
        Returns:
            加载的记忆数量
        """
        count = self.memory_manager.load_memory(self.user_memory_path)
        logger.info(f"已加载 {count} 条用户记忆")
        return count


class WorkspaceMemoryManager:
    """工作记忆管理器
    
    管理特定项目的工作记忆，如项目事实、决策、待办事项等
    """
    
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        # 确保工作目录存在
        os.makedirs(workspace_path, exist_ok=True)
        
        # 初始化记忆管理器
        self.memory_manager = MemoryManager()
        # 加载工作记忆
        self.memory_manager.load_memory(workspace_path)
        
        logger.info(f"工作记忆管理器已初始化，存储路径：{workspace_path}")
    
    def save_memory(
        self,
        content: str,
        category: str = "note",
        tags: List[str] = None,
        importance: int = 3,
        metadata: Dict[str, Any] = None
    ) -> Memory:
        """保存工作记忆"""
        return self.memory_manager.save_memory(
            content=content,
            category=category,
            tags=tags,
            importance=importance,
            metadata=metadata
        )
    
    def search_memory(
        self,
        query: str,
        category: str = None,
        tags: List[str] = None,
        top_k: int = 5,
        use_vector: bool = True,
        vector_weight: float = 0.5
    ) -> List[Memory]:
        """搜索工作记忆"""
        return self.memory_manager.search_memory(
            query=query,
            category=category,
            tags=tags,
            top_k=top_k,
            use_vector=use_vector,
            vector_weight=vector_weight
        )
    
    def save_to_file(self):
        """持久化工作记忆到文件"""
        self.memory_manager.save_to_file()
        logger.info(f"工作记忆已持久化到：{self.workspace_path}")
    
    def get_stats(self) -> dict:
        """获取工作记忆统计信息"""
        return self.memory_manager.get_memory_stats()


def search_combined_memory(
    query: str,
    workspace_path: str,
    category: str = None,
    tags: List[str] = None,
    top_k: int = 5
) -> List[Memory]:
    """搜索用户记忆和工作记忆（工作记忆优先）
    
    Args:
        query: 搜索关键词
        workspace_path: 工作目录路径
        category: 分类过滤
        tags: 标签过滤
        top_k: 返回数量
    
    Returns:
        合并后的记忆列表
    """
    # 初始化管理器
    user_manager = UserMemoryManager()
    workspace_manager = WorkspaceMemoryManager(workspace_path)
    
    # 搜索用户记忆
    user_results = user_manager.search_memory(
        query=query,
        category=category,
        tags=tags,
        top_k=top_k
    )
    
    # 搜索工作记忆
    workspace_results = workspace_manager.search_memory(
        query=query,
        category=category,
        tags=tags,
        top_k=top_k
    )
    
    # 合并结果（工作记忆优先）
    combined_results = []
    seen_ids = set()
    
    # 先添加工作记忆结果
    for memory in workspace_results:
        if memory.id not in seen_ids:
            combined_results.append(memory)
            seen_ids.add(memory.id)
    
    # 再添加用户记忆结果
    for memory in user_results:
        if memory.id not in seen_ids and len(combined_results) < top_k:
            combined_results.append(memory)
            seen_ids.add(memory.id)
    
    return combined_results[:top_k]


def save_memory_with_context(
    content: str,
    category: str = "note",
    tags: List[str] = None,
    importance: int = 3,
    metadata: Dict[str, Any] = None,
    workspace_path: str = None,
    is_project_specific: bool = False
) -> Memory:
    """根据上下文保存记忆到适当的存储位置
    
    Args:
        content: 记忆内容
        category: 分类
        tags: 标签
        importance: 重要性
        metadata: 元数据
        workspace_path: 工作目录路径
        is_project_specific: 是否为项目特定记忆
    
    Returns:
        保存的记忆对象
    """
    # 项目特定记忆或特定分类的记忆保存到工作记忆
    if is_project_specific or category in ["decision", "todo", "note"]:
        if not workspace_path:
            raise ValueError("保存项目特定记忆需要指定工作目录路径")
        workspace_manager = WorkspaceMemoryManager(workspace_path)
        return workspace_manager.save_memory(
            content=content,
            category=category,
            tags=tags,
            importance=importance,
            metadata=metadata
        )
    else:
        # 其他记忆保存到用户记忆
        user_manager = UserMemoryManager()
        return user_manager.save_memory(
            content=content,
            category=category,
            tags=tags,
            importance=importance,
            metadata=metadata
        )


def save_all_memories(
    workspace_path: str
) -> None:
    """持久化所有记忆
    
    Args:
        workspace_path: 工作目录路径
    """
    # 持久化用户记忆
    user_manager = UserMemoryManager()
    user_manager.save_to_file()
    
    # 持久化工作记忆
    workspace_manager = WorkspaceMemoryManager(workspace_path)
    workspace_manager.save_to_file()
    
    logger.info("用户记忆和工作记忆已全部持久化")
