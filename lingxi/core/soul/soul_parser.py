"""SOUL.md 解析器 - 解析 SOUL 文件为结构化数据"""

import re
from typing import Dict, List, Optional


class SoulParser:
    """SOUL.md 解析器"""
    
    def parse(self, content: str) -> dict:
        """
        解析 SOUL.md 内容为结构化数据
        
        返回格式：
        {
            "identity": {
                "name": str,
                "creature": str,
                "vibe": str,
                "emoji": str
            },
            "core_truths": List[str],
            "boundaries": List[str],
            "memory": List[str],
            "context": str,
            "raw_content": str
        }
        """
        result = {
            "identity": self._parse_identity(content),
            "core_truths": self._parse_list_section(content, "Core Truths"),
            "boundaries": self._parse_list_section(content, "Boundaries"),
            "memory": self._parse_list_section(content, "Memory"),
            "context": self._parse_section(content, "Context"),
            "raw_content": content
        }
        return result
    
    def _parse_section(self, content: str, section_name: str) -> str:
        """解析指定章节内容"""
        # 使用正则匹配章节标题和内容
        # 匹配 ## Section Name 到下一个 ## 或文件结尾
        pattern = rf'##\s*{re.escape(section_name)}\s*\n(.*?)(?=^##|\Z)'
        match = re.search(pattern, content, re.MULTILINE | re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""
    
    def _parse_identity(self, content: str) -> dict:
        """解析身份区块"""
        identity = {
            "name": "",
            "creature": "",
            "vibe": "",
            "emoji": ""
        }
        
        # 查找 Identity 或 核心身份 章节
        identity_section = self._parse_section(content, "Identity")
        if not identity_section:
            identity_section = self._parse_section(content, "核心身份")
        
        if not identity_section:
            # 尝试从文件头部查找
            identity_section = self._parse_section(content, "Core Identity")
        
        if not identity_section:
            return identity
        
        def clean_markdown(text):
            """清理 Markdown 格式（**bold** 等）"""
            if text:
                text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
                text = re.sub(r'\*(.+?)\*', r'\1', text)
                text = text.strip()
            return text
        
        # 解析各个字段（支持列表格式：- **Name:** xxx）
        name_match = re.search(r'\*{0,2}(?:Name|名字)\*{0,2}[:：]\s*(.+?)(?:\n|$)', identity_section, re.IGNORECASE)
        if name_match:
            identity["name"] = clean_markdown(name_match.group(1).strip())
        
        creature_match = re.search(r'\*{0,2}(?:Creature|物种 | 生物)\*{0,2}[:：]\s*(.+?)(?:\n|$)', identity_section, re.IGNORECASE)
        if creature_match:
            identity["creature"] = clean_markdown(creature_match.group(1).strip())
        
        vibe_match = re.search(r'\*{0,2}(?:Vibe|氛围 | 气质)\*{0,2}[:：]\s*(.+?)(?:\n|$)', identity_section, re.IGNORECASE)
        if vibe_match:
            identity["vibe"] = clean_markdown(vibe_match.group(1).strip())
        
        emoji_match = re.search(r'\*{0,2}(?:Emoji|表情 | 符号)\*{0,2}[:：]\s*(.+?)(?:\n|$)', identity_section, re.IGNORECASE)
        if emoji_match:
            identity["emoji"] = clean_markdown(emoji_match.group(1).strip())
        
        return identity
    
    def _parse_list_section(self, content: str, section_name: str) -> List[str]:
        """解析列表型章节（如 Core Truths、Boundaries）"""
        section_content = self._parse_section(content, section_name)
        if not section_content:
            return []
        
        items = []
        # 匹配以 - 或 * 开头的行
        for line in section_content.split('\n'):
            line = line.strip()
            if line.startswith('-') or line.startswith('*'):
                item = line[1:].strip()
                if item:
                    items.append(item)
        
        return items
