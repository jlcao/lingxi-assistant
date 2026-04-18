import logging
import json
import asyncio
from typing import Dict, List, Optional, Any, Callable
from concurrent.futures import ThreadPoolExecutor
from lingxi.skills.skill_system import SkillSystem
from lingxi.skills.tool_sandbox_adapter import ToolSandboxAdapter, adapt_tool_manager
from lingxi.skills.execution_context import ExecutionContext
from lingxi.core.utils.security import SecuritySandbox, SecurityError
from lingxi.core.utils.Tool import Tool, ToolBase

# 创建线程池用于执行同步技能
_skill_executor = ThreadPoolExecutor(max_workers=20, thread_name_prefix="skill-executor")

from lingxi.core.soul import SoulInjector

class ActionCaller:
    """行动调用层，标准化 MCP/Skill 调用"""
    
    _instance = None  # 单例实例
    
    def __new__(cls, config: Dict[str, Any]):
        """单例模式：确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config: Dict[str, Any]):
        """初始化能力调用层

        Args:
            config: 系统配置
        """
        # 防止重复初始化
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self.config = config
        self.logger = logging.getLogger(__name__)
        skill_call_config = config.get("skill_call", {})
        self.default_timeout = skill_call_config.get("default_timeout", 30)
        self.retry_count = skill_call_config.get("retry_count", 1)
        self.verify_ssl = skill_call_config.get("verify_ssl", True)
        self._initialized = True
        
        # 初始化技能管理器（包含技能注册表）
        # 使用统一的 SkillSystem
        self.skill_system = SkillSystem(config)
        self.skill_registry = self.skill_system.registry
        self.sandbox = self.skill_system.sandbox
        self.sandbox_manager = self.skill_system.sandbox_manager
        self.tool = Tool(self.skill_system)
        
        # 初始化工具沙盒适配器
        self.tool_adapter = adapt_tool_manager(self.tool, self.sandbox_manager)
        self.logger.debug("工具沙盒适配器已初始化")
        

        
        # 工作空间管理器（V4.0 新增）
        self.workspace_manager = None
        
        # 初始化 SOUL 注入器
        self.soul_injector = SoulInjector()
        self.soul_injector.load()
        self.logger.debug("SOUL 注入器已初始化")
    
    def set_workspace_manager(self, workspace_manager):
        """设置工作空间管理器
        
        Args:
            workspace_manager: WorkspaceManager 实例
        """
        self.workspace_manager = workspace_manager
        
        # 设置资源引用
        if workspace_manager:
            workspace_manager.set_resources(
                sandbox=self.sandbox,
                action_caller=self,
                skill_system=self.skill_system,
                session_store=None,  # 由外部设置
                event_publisher=None  # 由外部设置
            )
        
        self.logger.debug("工作空间管理器已设置")

    def list_available_skills(self, enabled_only: bool = True) -> List[Dict[str, Any]]:
        """列出可用技能

        Args:
            enabled_only: 是否只列出启用的技能

        Returns:
            技能列表
        """
        return self.skill_registry.list_skills(enabled_only=enabled_only)

    def call_with_security_check(
        self,
        skill_name: str,
        action_type: str,
        parameters: Dict[str, Any] = None,
        require_confirmation: bool = False
    ) -> Dict[str, Any]:
        """调用技能（带安全检查）

        Args:
            skill_name: 技能名称
            action_type: 行动类型
            parameters: 技能参数
            require_confirmation: 是否需要确认

        Returns:
            调用结果

        Raises:
            SecurityError: 安全检查失败
        """
        if parameters is None:
            parameters = {}

        self.logger.debug(f"调用技能（安全检查）: {skill_name} - {parameters}")

        # 规范化 parameters 中所有包含 "path" 的参数为绝对路径
        if skill_name not in ['read_skill']:
            parameters = self._normalize_paths_in_parameters(parameters)
        try:
            self.sandbox.check_security_parameters(skill_name, action_type, parameters)
        except SecurityError as e:
            self.logger.error(f"安全检查失败: {e}")
            return {"success": False, "result": f"该任务无法完成，只能操作工作空间内的文件或目录: {str(e)}"}

        if action_type not in ["tool", "skill"]:
            error_msg = f"无效的行动类型: {action_type}"
            self.logger.warning(error_msg)
            return {"success": False, "result": error_msg}
        if action_type == "tool" :
            # 使用沙盒执行环境执行工具
            context = ExecutionContext(skill_id=skill_name)
            try:
                # 从工具管理器获取工具实例
                if skill_name in self.tool.tools:
                    
                    
                    # 为 file 工具的 list 操作添加 operation_type 参数
                    if skill_name == "file" and parameters.get("action") == "list":
                        parameters["operation_type"] = "list"
                    
                    # 在沙盒中执行工具
                    response = self.tool_adapter.execute_tool_in_sandbox(
                        self.tool,
                        parameters,
                        skill_name,
                        context=context
                    )
                    
                    # 处理响应 - 检查 response.success 而不是 response.data.get("success")
                    if response.success:
                        return {"success": True, "result": str(response.data), "result_description": response.message}
                    else:
                        error_msg = f"工具执行失败: {skill_name} : {response.message}"
                        self.logger.warning(error_msg)
                        return {"success": False, "result": response.message, "result_description": response.message}
                else:
                    error_msg = f"工具 {skill_name} 未注册"
                    self.logger.warning(error_msg)
                    return {"success": False, "result": error_msg}
            except Exception as e:
                error_msg = f"工具执行异常: {skill_name} : {str(e)}"
                self.logger.error(error_msg)
                return {"success": False, "result": error_msg}
        else :
            return self.skill_system.execute_skill(skill_name, parameters).get("data", {})

    def _normalize_file_path(self, file_path: str) -> str:
        """将文件路径转换为绝对路径（如果是相对路径）

        Args:
            file_path: 文件路径

        Returns:
            绝对路径
        """
        from pathlib import Path
        
        # 如果已经是绝对路径，直接返回
        if Path(file_path).is_absolute():
            return file_path
        
        # 如果是相对路径，转换为工作区绝对路径
        normalized_path = self.sandbox.workspace_root / file_path
        return str(normalized_path)
    
    def _normalize_paths_in_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """规范化 parameters 中所有包含 "path" 的参数为绝对路径
        
        Args:
            parameters: 原始参数字典
            
        Returns:
            处理后的参数字典
        """
        if not parameters:
            return parameters
        
        normalized_params = parameters.copy()
        
        for key, value in parameters.items():
            # 检查键名是否包含 "path"（不区分大小写）
            if "path" in key.lower() and isinstance(value, str):
                try:
                    normalized_params[key] = self._normalize_file_path(value)
                    self.logger.debug(f"规范化路径参数 {key}: {value} -> {normalized_params[key]}")
                except Exception as e:
                    self.logger.warning(f"规范化路径参数 {key} 失败: {e}")
            if "output_file" in key.lower() and isinstance(value, str):
                try:
                    normalized_params[key] = self._normalize_file_path(value)
                    self.logger.debug(f"规范化路径参数 {key}: {value} -> {normalized_params[key]}")
                except Exception as e:
                    self.logger.warning(f"规范化路径参数 {key} 失败: {e}")
        
        return normalized_params



