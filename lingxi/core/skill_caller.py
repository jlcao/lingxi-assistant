import logging
import json
from typing import Dict, List, Optional, Any
from lingxi.skills.registry import SkillRegistry
from lingxi.skills.builtin import BuiltinSkills
from lingxi.core.security import SecuritySandbox, SecurityError


class SkillCaller:
    """能力调用层，标准化MCP/Skill调用"""

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
        self.builtin_skills = BuiltinSkills(config)
        # 使用技能管理器的注册表，避免创建两个独立的实例
        self.skill_registry = self.builtin_skills.registry

        # 初始化安全沙箱（V4.0新增）
        security_config = config.get("security", {})
        self.sandbox = SecuritySandbox(
            workspace_root=security_config.get("workspace_root", "./workspace"),
            max_file_size=security_config.get("max_file_size", 10 * 1024 * 1024),
            allowed_commands=security_config.get("allowed_commands"),
            safety_mode=security_config.get("safety_mode", True)
        )

        self.logger.debug("初始化能力调用层")

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
        """执行技能（支持重试）

        Args:
            skill_name: 技能名称
            parameters: 技能参数

        Returns:
            执行结果
        """
        last_error = None

        for attempt in range(self.retry_count + 1):
            try:
                result = self.builtin_skills.execute_skill(skill_name, parameters)
                self.logger.debug(f"执行技能返回: {skill_name} - {result.replace('\n', '\\n')}")
                return result
            except Exception as e:
                last_error = e
                self.logger.warning(f"技能调用尝试 {attempt + 1}/{self.retry_count + 1} 失败: {e}")

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
        parameters: Dict[str, Any] = None,
        require_confirmation: bool = False
    ) -> Dict[str, Any]:
        """调用技能（带安全检查）

        Args:
            skill_name: 技能名称
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

        skill_info = self.skill_registry.get_skill(skill_name)

        if not skill_info:
            error_msg = f"技能不存在: {skill_name}"
            self.logger.warning(error_msg)
            return {"success": False, "error": error_msg}

        if not skill_info.get("enabled", True):
            error_msg = f"技能未启用: {skill_name}"
            self.logger.warning(error_msg)
            return {"success": False, "error": error_msg}

        try:
            result = self._execute_with_security_check(
                skill_name,
                parameters,
                require_confirmation
            )
            return {"success": True, "result": result}
        except SecurityError as e:
            self.logger.error(f"安全检查失败: {e}")
            return {"success": False, "error": str(e), "error_code": e.error_code}
        except Exception as e:
            self.logger.error(f"技能调用失败: {e}")
            return {"success": False, "error": str(e)}

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
