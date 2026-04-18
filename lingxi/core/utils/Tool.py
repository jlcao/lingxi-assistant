#!/usr/bin/env python3
"""工具基类 - 所有工具的父类"""

import logging
from typing import Dict, Any, List, Optional

from lingxi.skills.skill_response import ToolResponse


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
    def get_parameters_description(self) -> str:
        """
        获取工具参数描述
        
        Returns:
            参数描述字符串  
        """
        return self.get_parameters()
    
    def get_description(self) -> str:
        """
        获取工具描述
        
        Returns:
            工具描述字符串
        """
        return self.description
    
    
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
    
    def __new__(cls, skill_system=None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, skill_system=None):
        """初始化工具管理器"""
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self.logger = logging.getLogger(__name__)
        self.tools: Dict[str, ToolBase] = {}
        
        if skill_system is not None:
            self._initialize_tools(skill_system)
            self._initialized = True
    
    def _initialize_tools(self, skill_system):
        """初始化工具列表"""
        from lingxi.core.utils.FileTool import FileTool
        from lingxi.core.utils.CommandTool import CommandTool
        from lingxi.core.utils.ReadSkillTool import ReadSkillTool
        
        self.register_tool(FileTool())
        self.register_tool(CommandTool())
        self.register_tool(ReadSkillTool(skill_system))
    
    @classmethod
    def get_instance(cls):
        """获取单例实例"""
        if cls._instance is None:
            raise RuntimeError("Tool 实例尚未初始化，请先调用 Tool(skill_system)")
        return cls._instance
    
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
        try:
            if tool_name not in self.tools:
                raise ToolNotFoundError(f"工具 {tool_name} 未注册")
        
            tool = self.tools[tool_name]
            # 验证参数
            tool.validate_parameters(kwargs)
            content = tool.execute(kwargs)

            # 执行工具
            return ToolResponse.success(data=content)  
        except Exception as e:
            self.logger.error(f"工具执行错误：{e}", exc_info=True)
            return ToolResponse.error(message=str(e))
        
    
    def list_tools(self) -> Dict[str, Dict[str, Any]]:
        """列出所有工具"""
        return {
            name: tool.get_info()
            for tool in self.tools.values()
        }
    def list_tools_metadata(self) -> List[str]:
        """列出所有工具的元数据"""
        return [
            f"{tool.name}: {tool.get_description()}"
            for tool in self.tools.values()
        ]
    
    def list_tools_parameter_description(self) -> List[str]:
        """列出所有工具的参数描述"""
        return [
            f"{tool.name}:\n{tool.get_parameters_description()}"
            for tool in self.tools.values()
        ]
    