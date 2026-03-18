#!/usr/bin/env python3
"""技能执行器 - 统一的技能执行逻辑"""

import logging
from typing import Dict, Any, Optional
from lingxi.core.confirmation import DangerousSkillChecker, RiskLevel
from lingxi.core.utils.security import SecurityError


class SkillExecutor:
    """技能执行器 - 统一的技能执行逻辑"""
    
    def __init__(self, skill_system, sandbox):
        """
        初始化技能执行器
        
        Args:
            skill_system: SkillSystem 实例
            sandbox: SecuritySandbox 实例
        """
        self.skill_system = skill_system
        self.sandbox = sandbox
        self.logger = logging.getLogger(__name__)
    
    def execute_skill(
        self,
        skill_name: str,
        parameters: Dict[str, Any],
        require_confirmation: bool = False
    ) -> Dict[str, Any]:
        """
        执行技能（带安全检查）
        
        Args:
            skill_name: 技能名称
            parameters: 技能参数
            require_confirmation: 是否需要用户确认
            
        Returns:
            执行结果字典
        """
        # 1. 检查技能是否存在
        skill_info = self.skill_system.get_skill_info(skill_name)
        if not skill_info:
            error_msg = f"技能不存在: {skill_name}"
            self.logger.warning(error_msg)
            return {"success": False, "error": error_msg}
        
        # 2. 检查技能是否启用
        if not skill_info.get("enabled", True):
            error_msg = f"技能未启用: {skill_name}"
            self.logger.warning(error_msg)
            return {"success": False, "error": error_msg}
        
        # 3. 检查操作风险级别
        skill_risk = DangerousSkillChecker.check_skill_risk(skill_name)
        command_risk = RiskLevel.LOW
        
        # 检查命令风险（如果是 execute 操作）
        if skill_name == "execute" and isinstance(parameters.get("command"), str):
            command_risk = DangerousSkillChecker.check_command_risk(parameters["command"])
        
        # 4. 判断是否需要确认
        needs_confirmation = (
            skill_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL] or
            command_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        )
        
        if needs_confirmation and not require_confirmation:
            error_msg = (
                f"高危操作需要用户确认：{skill_name}\n"
                f"风险级别：{DangerousSkillChecker.get_risk_description(skill_risk)}\n"
                f"参数：{parameters}"
            )
            self.logger.warning(error_msg)
            raise SecurityError(error_msg, "DANGEROUS_OPERATION")
        
        # 5. 处理文件操作类技能，将相对路径转换为绝对路径
        if skill_name in ["create_file", "delete_file", "read_file", "modify_file"]:
            if "file_path" in parameters:
                parameters = parameters.copy()
                parameters["file_path"] = self._normalize_file_path(parameters["file_path"])
        
        # 6. 使用 SkillSystem 执行技能
        try:
            result = self.skill_system.execute_skill(skill_name, parameters)
            self.logger.debug(f"技能执行成功：{skill_name}")
            return {"success": True, "result": result}
        except Exception as e:
            error_msg = f"技能执行失败：{skill_name} - {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def _normalize_file_path(self, file_path: str) -> str:
        """
        将文件路径转换为绝对路径（如果是相对路径）
        
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
        workspace_root = self.sandbox.workspace_root
        normalized_path = workspace_root / file_path
        return str(normalized_path)