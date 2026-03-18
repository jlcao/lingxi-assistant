#!/usr/bin/env python3
"""读取技能使用说明工具

从 SkillSystem 缓存中读取技能的 SKILL.md 文件内容，
提供详细的技能使用说明、参数说明和示例代码。
"""

import logging
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from lingxi.core.utils.Tool import ToolBase


class ReadSkillTool(ToolBase):
    """读取技能使用说明工具类"""
    
    def __init__(self, skill_system=None):
        """初始化工具
        
        Args:
            skill_system: SkillSystem 实例（可选，如果为 None 则需要手动设置）
        """
        super().__init__("read_skill", "读取技能使用说明工具，从 SkillSystem 缓存中读取技能的 SKILL.md 文件内容")
        self.skill_system = skill_system
    
    def set_skill_system(self, skill_system):
        """设置 SkillSystem 实例
        
        Args:
            skill_system: SkillSystem 实例
        """
        self.skill_system = skill_system
        self.logger.debug("SkillSystem 已设置")
    
    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具 - 读取技能的 SKILL.md 文件内容
        
        Args:
            parameters: 工具参数，包含:
                - skill_name: 技能名称（必填）
            
        Returns:
            执行结果字典，格式：
            {
                "status": "S" | "F",  # 成功/失败
                "content": [],  # 返回内容列表
                "error": ""  # 错误信息（成功时为空）
            }
        """
        result = {
            "status": "F",
            "content": [],
            "error": ""
        }
        
        skill_name = parameters.get("skill_name")
        
        if not skill_name:
            result["error"] = "缺少必要参数: skill_name"
            return result
        
        if not self.skill_system:
            result["error"] = "SkillSystem 未设置，无法读取技能"
            return result
        
        # 从 SkillSystem 的缓存中读取 SKILL.md 内容
        skill_cache = self.skill_system.cache
        self.logger.debug(f"尝试读取 SKILL.md，skill_name={skill_name}, skill_system={self.skill_system}, cache={skill_cache}")
        if skill_cache:
            cached_content = skill_cache.get_md_content(skill_name)
            self.logger.debug(f"get_md_content 返回结果：{cached_content}")
            if cached_content:
                self.logger.info(f"从缓存读取 SKILL.md：{skill_name}")
                result["status"] = "S"
                result["content"] = cached_content
                return result
        
        # 如果缓存中没有，返回错误
        self.logger.warning(f"缓存中未找到 SKILL.md：{skill_name}")
        result["error"] = f"缓存中未找到 SKILL.md：{skill_name}"
        return result
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> Optional[str]:
        """验证参数
        
        Args:
            parameters: 工具参数
            
        Returns:
            错误信息（如果有），否则返回 None
        """
        skill_name = parameters.get("skill_name")
        if not skill_name:
            return "缺少必要参数: skill_name"
        return None
    

    
    
    
    
