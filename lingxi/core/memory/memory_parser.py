#!/usr/bin/env python3
"""MEMORY.md 解析器"""

import re
import logging
from typing import List, Dict, Tuple
from .memory_manager import Memory

logger = logging.getLogger(__name__)


class MemoryParser:
    """MEMORY.md 解析器"""
    
    def __init__(self):
        self.category_mapping = {
            "用户偏好": "preference",
            "偏好": "preference",
            "重要事实": "fact",
            "事实": "fact",
            "历史决策": "decision",
            "决策": "decision",
            "待办事项": "todo",
            "待办": "todo",
            "笔记": "note"
        }
    
    def parse(self, content: str) -> List[Memory]:
        """解析 MEMORY.md 内容"""
        memories = []
        
        # 按章节分割
        sections = self._split_sections(content)
        
        for section_name, section_content in sections.items():
            category = self._map_category(section_name)
            
            # 提取列表项
            items = self._extract_list_items(section_content)
            
            for item in items:
                if item.strip():
                    memory = Memory(
                        id=Memory.compute_id(item, category),
                        content=item.strip(),
                        category=category,
                        tags=[],
                        importance=3,
                        created_at=0,
                        updated_at=0,
                        access_count=0,
                        workspace_path="",
                        metadata={"source": "MEMORY.md", "section": section_name}
                    )
                    memories.append(memory)
        
        logger.debug(f"解析出 {len(memories)} 条记忆")
        return memories
    
    def _split_sections(self, content: str) -> Dict[str, str]:
        """按章节分割内容"""
        sections = {}
        current_section = "默认"
        current_content = []
        
        for line in content.split('\n'):
            # 检测章节标题
            if line.startswith('## '):
                # 保存前一章节
                if current_content:
                    sections[current_section] = '\n'.join(current_content)
                
                # 新章节
                current_section = line[3:].strip()
                current_content = []
            else:
                current_content.append(line)
        
        # 保存最后一章节
        if current_content:
            sections[current_section] = '\n'.join(current_content)
        
        return sections
    
    def _map_category(self, section_name: str) -> str:
        """映射章节名到分类"""
        # 直接匹配
        if section_name in self.category_mapping:
            return self.category_mapping[section_name]
        
        # 模糊匹配
        for key, value in self.category_mapping.items():
            if key in section_name or section_name in key:
                return value
        
        # 默认
        return "note"
    
    def _extract_list_items(self, content: str) -> List[str]:
        """提取列表项"""
        items = []
        
        for line in content.split('\n'):
            line = line.strip()
            
            # 匹配列表项 (- 或 * 开头)
            if line.startswith('- ') or line.startswith('* '):
                item = line[2:].strip()
                if item:
                    items.append(item)
        
        return items
