#!/usr/bin/env python3
"""记忆提取器 - 从对话中自动提取重要信息"""

import re
import logging
from typing import List, Dict, Any
from datetime import datetime
from .memory_manager import Memory, MemoryManager

logger = logging.getLogger(__name__)


class MemoryExtractor:
    """记忆提取器"""
    
    def __init__(self, memory_manager: MemoryManager):
        self.memory_manager = memory_manager
        self.extraction_patterns = self._load_patterns()
    
    def _load_patterns(self) -> Dict[str, str]:
        """加载提取模式"""
        return {
            # 用户偏好
            "preference": r"(我喜欢|我讨厌|我习惯|我经常|我很少|我不喜欢|我偏好|我常用).+",
            # 重要事实
            "fact": r"(记住|重要的是|关键是|注意|记住我|别忘了).+",
            # 决策
            "decision": r"(决定了|确定了|就这样吧|采用|选择|使用).+",
            # 待办事项
            "todo": r"(我要|我需要|记得|别忘了|待会|稍后|以后要).+",
            # 项目信息
            "project": r"(项目是|正在做|开发中|产品是|公司是).+"
        }
    
    def extract_from_message(self, message: str, role: str = "user") -> List[Memory]:
        """从单条消息中提取记忆"""
        memories = []
        
        for category, pattern in self.extraction_patterns.items():
            matches = re.findall(pattern, message, re.IGNORECASE)
            for match in matches:
                # 提取完整句子
                full_match = self._extract_full_sentence(message, match)
                
                if full_match and len(full_match) > 5:
                    memory = Memory(
                        id=Memory.compute_id(full_match, category),
                        content=full_match,
                        category=category,
                        tags=[],
                        importance=self._calculate_importance(category, full_match),
                        created_at=datetime.now().timestamp(),
                        updated_at=datetime.now().timestamp(),
                        access_count=0,
                        workspace_path=self.memory_manager.workspace_path,
                        metadata={
                            "source": "conversation",
                            "role": role,
                            "extracted_at": datetime.now().isoformat()
                        }
                    )
                    memories.append(memory)
        
        return memories
    
    def _extract_full_sentence(self, text: str, keyword: str) -> str:
        """提取完整句子"""
        # 找到关键词位置
        idx = text.lower().find(keyword.lower())
        if idx < 0:
            return keyword
        
        # 向前找到句首
        start = 0
        for i in range(idx, -1, -1):
            if text[i] in '.,.!?.!.,':
                start = i + 1
                break
        
        # 向后找到句尾
        end = len(text)
        for i in range(idx, len(text)):
            if text[i] in '.!.!?':
                end = i + 1
                break
        
        return text[start:end].strip()
    
    def _calculate_importance(self, category: str, content: str) -> int:
        """计算重要性 (1-5)"""
        importance = 3  # 默认
        
        # 根据分类调整
        if category in ["fact", "decision"]:
            importance += 1
        
        # 根据关键词调整
        important_keywords = ["一定", "必须", "重要", "千万", "永远"]
        if any(kw in content for kw in important_keywords):
            importance += 1
        
        return min(importance, 5)
    
    def extract_from_session(
        self,
        session_history: List[dict],
        auto_save: bool = True,
        min_importance: int = 3
    ) -> List[Memory]:
        """
        从会话历史中提取记忆
        
        Args:
            session_history: 会话历史
            auto_save: 是否自动保存
            min_importance: 最小重要性阈值
        
        Returns:
            提取的记忆列表
        """
        all_memories = []
        
        for message in session_history:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            # 只从用户消息提取
            if role != "user":
                continue
            
            # 跳过太短的消息
            if len(content) < 10:
                continue
            
            # 提取记忆
            memories = self.extract_from_message(content, role)
            
            # 过滤低重要性
            memories = [m for m in memories if m.importance >= min_importance]
            
            # 去重（基于 ID）
            existing_ids = {m.id for m in all_memories}
            memories = [m for m in memories if m.id not in existing_ids]
            
            all_memories.extend(memories)
            
            # 自动保存
            if auto_save:
                for memory in memories:
                    # 检查是否已存在
                    if memory.id not in self.memory_manager.memories:
                        self.memory_manager.save_memory(
                            content=memory.content,
                            category=memory.category,
                            tags=memory.tags,
                            importance=memory.importance,
                            metadata=memory.metadata
                        )
                        logger.info(f"自动保存记忆：{memory.content[:50]}...")
        
        logger.info(f"从会话中提取了 {len(all_memories)} 条记忆")
        return all_memories
