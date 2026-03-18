#!/usr/bin/env python3
"""工具基类 - 所有工具的父类"""

import logging
from typing import Dict, Any, Optional


class ToolBase:
    """工具基类，所有工具必须继承此类"""
    
    def __init__(self, name: str, description: str):
        """
        初始化工具
        
        Args:
            name: 工具名称
            description: 工具描述
        """
        self.name = name
        self.description = description
        self.logger = logging.getLogger(__name__)
    
    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行工具（子类必须实现）
        
        Args:
            parameters: 工具参数
            
        Returns:
            执行结果字典，格式：
            {
                "status": "S" | "F",  # 成功/失败
                "content": [],  # 返回内容列表
                "error": ""  # 错误信息（成功时为空）
            }
        """
        raise NotImplementedError("子类必须实现 execute 方法")
    
    def get_info(self) -> Dict[str, Any]:
        """
        获取工具信息
        
        Returns:
            工具信息字典
        """
        return {
            "name": self.name,
            "description": self.description
        }
    
    def validate_parameters(self, parameters: Dict[str, Any]) -> Optional[str]:
        """
        验证参数（子类可以重写）
        
        Args:
            parameters: 工具参数
            
        Returns:
            错误信息（如果有），否则返回 None
        """
        return None  # 默认不验证，子类可以重写


class Tool:
    """工具管理器（单例模式）"""
    
    _instance = None
    
    def __new__(cls,skill_system):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self,skill_system):
        """初始化工具管理器"""
        self.logger = logging.getLogger(__name__)
        self.tools: Dict[str, ToolBase] = {}
        
        # 延迟导入以避免循环依赖
        from lingxi.core.utils.FileTool import FileTool
        from lingxi.core.utils.CommandTool import CommandTool
        from lingxi.core.utils.ReadSkillTool import ReadSkillTool
        
        self.register_tool(FileTool())
        self.register_tool(CommandTool())
        self.register_tool(ReadSkillTool(skill_system))
    
    def register_tool(self, tool: ToolBase):
        """注册工具"""
        self.tools[tool.name] = tool
        self.logger.info(f"工具已注册：{tool.name}")
    
    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """执行工具
        
        Args:
            tool_name: 工具名称
            **kwargs: 工具参数
            
        Returns:
            工具执行结果
        """
        if tool_name not in self.tools:
            return {
                "status": "F",
                "content": [],
                "error": f"工具 {tool_name} 未注册"
            }
        
        tool = self.tools[tool_name]
        
        # 验证参数
        validation_error = tool.validate_parameters(kwargs)
        if validation_error:
            return {
                "status": "F",
                "content": [],
                "error": validation_error
            }
        
        # 执行工具
        return tool.execute(kwargs)
    
    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        """列出所有工具"""
        return {
            name: tool.get_info()
            for tool in self.tools.values()
        }