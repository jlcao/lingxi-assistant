#!/usr/bin/env python3
"""读取技能使用说明工具

从 SkillSystem 缓存中读取技能的 SKILL.md 文件内容，
提供详细的技能使用说明、参数说明和示例代码。
"""

import logging
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from lingxi.core.tools import ToolValidationError
from lingxi.core.tools.Tool import ToolBase


class ReadSkillTool(ToolBase):
    """读取技能使用说明工具类"""

    _instance = None

    def __new__(cls, *args, **kwargs):
        """实现单例模式"""
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, skill_system=None):
        """初始化工具
        
        Args:
            skill_system: SkillSystem 实例（可选，如果为 None 则需要手动设置）
        """
        super().__init__("read_skill", "用于读取技能的详细使用说明，默认读取 SKILL.md 文件，可指定该技能下面的其它文件读取，传入file_path参数")
        self.skill_system = skill_system
    
    def set_skill_system(self, skill_system):
        """设置 SkillSystem 实例
        
        Args:
            skill_system: SkillSystem 实例
        """
        self.skill_system = skill_system
        self.logger.debug("SkillSystem 已设置")

    def get_parameters_description(self) -> str:
        """
        获取工具参数描述
        
        Returns:
            参数描述字符串  
        """
        str = """- execute 工具调用示例
            ```json
            {{"skill_name": "技能名称，字符串，必填","file_path": "文件相对路径，字符串，可填，默认 SKILL.md"}}
            ```"""
        return str
    
    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具 - 读取技能的 SKILL.md 文件内容
        
        Args:
            parameters: 工具参数，包含:
                - skill_name: 技能名称（必填）
                - file_path: 文件相对路径（可填，为 None 时默认读SKILL.md）
            
        Returns:
            执行结果字典，格式：
            {
                "status": "S" | "F",  # 成功/失败
                "content": [],  # 返回内容列表
                "error": ""  # 错误信息（成功时为空）
            }
        """
        skill_name = parameters.get("skill_name") #技能名称
        file_path = parameters.get("file_path") #文件相对路径
        
       
        if not skill_name:
            raise ToolValidationError("缺少必要参数: skill_name")
        
        if file_path is None:
            file_path = f"SKILL.md"
            
        
        # 从 SkillSystem 的缓存中读取 SKILL.md 内容
        skill_cache = self.skill_system.cache
        self.logger.debug(f"尝试读取 {file_path}，skill_name={skill_name}, skill_system={self.skill_system}, cache={skill_cache}")
        if skill_cache:
            cached_content = skill_cache.get_file_content(skill_name, file_path)
            self.logger.debug(f"get_file_content 返回结果：{cached_content}")
            if cached_content:
                return f"已读取文件:{file_path}\n{cached_content}"
        
        # 如果缓存中没有，尝试从文件系统重新加载
        self.logger.debug(f"缓存未命中，尝试从文件系统加载：{skill_name}")
        content = self._load_from_filesystem(skill_name,file_path)
        if content:
            self.logger.info(f"从文件系统加载 {file_path}：{skill_name}")
            # 重新缓存
            if skill_cache:
                skill_md_path = self._find_skill_file_path(skill_name, file_path)
                if skill_md_path:
                    skill_cache.set_file_content(skill_name, content, skill_md_path)
            return f"已读取文件:{file_path}\n{content}"
        
        # 如果文件系统中也没有，返回错误
        self.logger.warning(f"缓存和文件系统中均未找到 {file_path}：{skill_name}")
        return f"缓存中未找到 {file_path}：{skill_name}"
    
    def _find_skill_file_path(self, skill_name: str, file_path: str = "SKILL.md") -> Optional[str]:
        """查找技能的文件路径
        
        Args:
            skill_name: 技能名称
            file_path: 文件相对路径，默认为 SKILL.md
            
        Returns:
            文件路径，如果未找到返回 None
        """
        # 获取技能目录配置
        skills_config = self.skill_system.loader
        if not skills_config:
            return None
        
        # 在内置技能目录和用户技能目录中查找
        for skills_path in [skills_config.builtin_skills_dir, skills_config.user_skills_dir]:
            if not skills_path:
                continue
            try:
                skill_dir = Path(skills_path) / skill_name
                skill_file_path = skill_dir / file_path
                if skill_file_path.exists():
                    return str(skill_file_path)
            except Exception:
                continue
        
        return None
    
    def _load_from_filesystem(self, skill_name: str, file_path: str = "SKILL.md") -> Optional[str]:
        """从文件系统加载指定文件内容
        
        Args:
            skill_name: 技能名称
            file_path: 文件相对路径，默认为 SKILL.md
            
        Returns:
            文件内容，如果未找到返回 None
        """
        skill_file_path = self._find_skill_file_path(skill_name, file_path)
        if not skill_file_path:
            return None
        
        try:
            with open(skill_file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"读取文件失败：{e}")
            return None
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> Optional[str]:
        """验证参数
        
        Args:
            parameters: 工具参数
            
        Returns:
            错误信息（如果有），否则返回 None
        """
        skill_name = parameters.get("skill_name")
        if not skill_name:
            raise ToolValidationError("缺少必要参数: skill_name")    

    
    
    
    
