import logging
import json
import asyncio
from typing import Dict, List, Optional, Any, Callable
from concurrent.futures import ThreadPoolExecutor
from lingxi.skills.skill_system import SkillSystem
from lingxi.core.utils.security import SecuritySandbox, SecurityError
from lingxi.core.utils.Tool import Tool, ToolBase
from lingxi.core.skill_executor import SkillExecutor

# 创建线程池用于执行同步技能
_skill_executor = ThreadPoolExecutor(max_workers=20, thread_name_prefix="skill-executor")

from lingxi.core.soul import SoulInjector

class SkillCaller:
    """能力调用层，标准化 MCP/Skill 调用"""
    
    _instance = None  # 单例实例
    
    def __init__(self, config: Dict[str, Any]):
        """单例模式：确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config: Dict[str, Any]):
        """初始化能力调用层

        Args:
            config: 系统配置
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        skill_call_config = config.get("skill_call", {})
        self.default_timeout = skill_call_config.get("default_timeout", 30)
        self.retry_count = skill_call_config.get("retry_count", 1)
        self.verify_ssl = skill_call_config.get("verify_ssl", True)
        
        # 初始化技能管理器（包含技能注册表）
        # 使用统一的 SkillSystem
        self.skill_system = SkillSystem(config)
        self.skill_registry = self.skill_system.registry
        self.sandbox = self.skill_system.sandbox
        self.tool = Tool(self.skill_system)
        
        # 初始化技能执行器
        self.skill_executor = SkillExecutor(self.skill_system, self.sandbox)
        self.logger.debug("技能执行器已初始化")
        
        # 工作空间管理器（V4.0 新增）
        self.workspace_manager = None
        
        # 初始化 SOUL 注入器
        workspace_path = config.get("workspace", {}).get("default_path", "./workspace")
        self.soul_injector = SoulInjector()
        self.soul_injector.load()
        self.logger.debug("SOUL 注入器已初始化")
        
        # 子代理调度器
        from lingxi.core.subagent import SubAgentScheduler
        self.subagent_scheduler = SubAgentScheduler(
            session_manager=None,  # 由外部设置
            skill_caller=self,
            config=config
        )
        self.logger.debug("子代理调度器已初始化")
        
        self.logger.debug("初始化能力调用层（使用 SkillSystem）")
    
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
                skill_caller=self,
                session_store=None,  # 由外部设置
                event_publisher=None  # 由外部设置
            )
        
        self.logger.debug("工作空间管理器已设置")

    def call(self, skill_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """调用技能

        Args:
            skill_name: 技能名称
            parameters: 技能参数

        Returns:
            调用结果
        """
        if parameters is None:
            parameters = {}

        self.logger.debug(f"调用技能: {skill_name} - {parameters}")

        skill_info = self.skill_registry.get_skill(skill_name)

        if not skill_info:
            self.logger.warning(f"技能不存在: {skill_name}")
            return {"success": False, "error": f"技能不存在: {skill_name}"}

        if not skill_info.get("enabled", True):
            self.logger.warning(f"技能未启用: {skill_name}")
            return {"success": False, "error": f"技能未启用: {skill_name}"}

        try:
            result = self._execute_with_retry(skill_name, parameters)
            return {"success": True, "result": result}
        except Exception as e:
            self.logger.error(f"技能调用失败: {e}")
            return {"success": False, "error": str(e)}

    def _execute_with_retry(self, skill_name: str, parameters: Dict[str, Any]) -> str:
        """执行技能（使用 SkillSystem）

        Args:
            skill_name: 技能名称
            parameters: 技能参数

        Returns:
            执行结果
        """
        # 处理文件操作类技能，将相对路径转换为绝对路径
        if skill_name in ["create_file", "delete_file", "read_file", "modify_file"]:
            if "file_path" in parameters:
                parameters = parameters.copy()  # 避免修改原始参数
                parameters["file_path"] = self._normalize_file_path(parameters["file_path"])
        
        last_error = None

        for attempt in range(self.retry_count + 1):
            try:
                # 使用 SkillSystem 执行
                result = self.skill_system.execute_skill(skill_name, parameters)
                result_debug = result.replace('\n', '\\n')
                self.logger.debug(f"执行技能返回：{skill_name} - {result_debug}")
                return result
            except Exception as e:
                last_error = e
                self.logger.warning(f"技能调用尝试 {attempt + 1}/{self.retry_count + 1} 失败：{e}")

                if attempt < self.retry_count:
                    continue

        raise last_error if last_error else Exception("技能调用失败")

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
        parameters = self._normalize_paths_in_parameters(parameters)

        try:
            self.sandbox.check_security_parameters(skill_name, action_type, parameters)
        except SecurityError as e:
            self.logger.error(f"安全检查失败: {e}")
            return {"success": False, "error": f"该任务无法完成，只能操作工作空间内的文件或目录: {str(e)}"}

        if action_type not in ["tool", "skill"]:
            error_msg = f"无效的行动类型: {action_type}"
            self.logger.warning(error_msg)
            return {"success": False, "error": error_msg}
        if action_type == "tool" :
            tool_res = self.tool.execute_tool(skill_name, **parameters)
            tool_status = tool_res.get('status')
            if tool_status == 'F':
                error_msg = f"工具执行失败: {skill_name} : {tool_res.get('error')}"
                self.logger.warning(error_msg)
                return {"success": False, "error": error_msg, "result_description": tool_res.get('result_description')}
            elif tool_status == 'S':
                return {"success": True, "result": str(tool_res), "result_description": tool_res.get('result_description')}
        else :
            return self.skill_executor.execute_skill(skill_name, parameters)

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

    def _execute_with_security_check(
        self,
        skill_name: str,
        parameters: Dict[str, Any],
        require_confirmation: bool
    ) -> str:
        """执行技能（带安全检查）

        Args:
            skill_name: 技能名称
            parameters: 技能参数
            require_confirmation: 是否需要确认

        Returns:
            执行结果

        Raises:
            SecurityError: 安全检查失败
        """
        from lingxi.core.confirmation import DangerousSkillChecker, RiskLevel

        skill_risk = DangerousSkillChecker.check_skill_risk(skill_name)

        if skill_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            if not require_confirmation:
                error_msg = (
                    f"高危操作需要用户确认：{skill_name}\n"
                    f"风险级别：{DangerousSkillChecker.get_risk_description(skill_risk)}"
                )
                raise SecurityError(error_msg, "DANGEROUS_OPERATION")

        # 处理文件操作类技能，将相对路径转换为绝对路径
        if skill_name in ["create_file", "delete_file", "read_file", "modify_file"]:
            if "file_path" in parameters:
                parameters = parameters.copy()  # 避免修改原始参数
                parameters["file_path"] = self._normalize_file_path(parameters["file_path"])
        # 判断当前操作是不是

        if skill_name == "file.read":
            file_path = parameters.get("file_path")
            if file_path:
                return self.sandbox.safe_read(file_path)

        elif skill_name == "file.write":
            file_path = parameters.get("file_path")
            content = parameters.get("content", "")
            overwrite = parameters.get("overwrite", False)
            if file_path:
                return self.sandbox.safe_write(file_path, content, overwrite)

        elif skill_name == "file.delete":
            file_path = parameters.get("file_path")
            if file_path:
                return self.sandbox.safe_delete(file_path)

        elif skill_name == "system.exec":
            command = parameters.get("command")
            timeout = parameters.get("timeout", 30)
            cwd = parameters.get("cwd")
            if command:
                return self.sandbox.safe_exec(command, timeout, cwd)

        return self._execute_with_retry(skill_name, parameters)

    def get_skill_info(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """获取技能信息

        Args:
            skill_name: 技能名称

        Returns:
            技能信息
        """
        return self.skill_registry.get_skill(skill_name)

    def register_skill(self, name: str, description: str = "", author: str = "",
                      version: str = "1.0.0", parameters: List[Dict[str, Any]] = None) -> bool:
        """注册技能

        Args:
            name: 技能名称
            description: 技能描述
            author: 作者
            version: 版本
            parameters: 技能参数

        Returns:
            是否注册成功
        """
        # 兼容两种注册表接口
        skill_config = {
            "skill_id": name,
            "skill_name": name,
            "description": description,
            "author": author,
            "version": version,
            "parameters": parameters
        }
        return self.skill_registry.register_skill(skill_config)

    def unregister_skill(self, name: str) -> bool:
        """注销技能

        Args:
            name: 技能名称

        Returns:
            是否注销成功
        """
        return self.skill_registry.unregister_skill(name)

    def enable_skill(self, name: str, enabled: bool = True) -> bool:
        """启用或禁用技能

        Args:
            name: 技能名称
            enabled: 是否启用

        Returns:
            是否操作成功
        """
        return self.skill_registry.enable_skill(name, enabled)

    def validate_parameters(self, skill_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """验证技能参数

        Args:
            skill_name: 技能名称
            parameters: 参数字典

        Returns:
            验证结果
        """
        skill_info = self.skill_registry.get_skill(skill_name)

        if not skill_info:
            return {"valid": False, "error": f"技能不存在: {skill_name}"}

        skill_params = skill_info.get("parameters", [])

        missing_params = []
        for param in skill_params:
            if param.get("required", False) and param.get("name") not in parameters:
                missing_params.append(param.get("name"))

        if missing_params:
            return {
                "valid": False,
                "error": f"缺少必需参数: {', '.join(missing_params)}"
            }

        return {"valid": True}

    def parse_skill_call(self, call_text: str) -> Optional[Dict[str, Any]]:
        """解析技能调用文本

        Args:
            call_text: 技能调用文本，如 "search(query='北京天气')"

        Returns:
            解析后的调用信息
        """
        import re

        pattern = r'(\w+)\((.*?)\)'
        match = re.match(pattern, call_text.strip())

        if not match:
            return None

        skill_name = match.group(1)
        params_str = match.group(2)

        parameters = {}

        if params_str:
            try:
                if '=' in params_str:
                    for param in params_str.split(','):
                        param = param.strip()
                        if '=' in param:
                            key, value = param.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('\'"')
                            parameters[key] = value
                else:
                    parameters["query"] = params_str.strip().strip('\'"')
            except Exception as e:
                self.logger.error(f"解析参数失败: {e}")
                return None

        return {
            "skill_name": skill_name,
            "parameters": parameters
        }

    async def call_async(self, skill_name: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """异步调用技能

        Args:
            skill_name: 技能名称
            parameters: 技能参数

        Returns:
            调用结果
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _skill_executor,
            lambda: self.call(skill_name, parameters)
        )

    async def call_with_security_check_async(
        self,
        skill_name: str,
        parameters: Dict[str, Any] = None,
        require_confirmation: bool = False
    ) -> Dict[str, Any]:
        """异步调用技能（带安全检查）

        Args:
            skill_name: 技能名称
            parameters: 技能参数
            require_confirmation: 是否需要确认

        Returns:
            调用结果
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _skill_executor,
            lambda: self.call_with_security_check(skill_name, parameters, require_confirmation)
        )

    # ========== 子代理便捷方法 ==========
    
    async def spawn_subagent(
        self,
        task: str,
        workspace_path: str = None,
        timeout: int = None,
        context: Dict[str, Any] = None,
        callback: Callable = None
    ) -> str:
        """Spawn 子代理执行任务
        
        Args:
            task: 任务描述
            workspace_path: 工作目录（可选）
            timeout: 超时时间（秒）
            context: 额外上下文
            callback: 完成回调函数
        
        Returns:
            任务 ID
        """
        return await self.subagent_scheduler.spawn(
            task=task,
            workspace_path=workspace_path,
            timeout=timeout,
            context=context,
            callback=callback
        )
    
    def get_subagent_status(self, task_id: str) -> Optional[str]:
        """获取子代理任务状态
        
        Args:
            task_id: 任务 ID
        
        Returns:
            任务状态（pending/running/completed/failed/timeout）
        """
        return self.subagent_scheduler.get_task_status(task_id)
    
    def list_subagents(self, status: str = None):
        """列出所有子代理任务
        
        Args:
            status: 按状态过滤（可选）
        
        Returns:
            任务列表
        """
        return self.subagent_scheduler.list_tasks(status)
    
    def set_session_manager_for_subagents(self, session_manager):
        """为子代理调度器设置 SessionManager
        
        Args:
            session_manager: SessionManager 实例
        """
        if self.subagent_scheduler:
            self.subagent_scheduler.session_manager = session_manager
            self.logger.debug("子代理调度器的 SessionManager 已设置")
