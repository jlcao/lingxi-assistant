#!/usr/bin/env python3
"""安全拦截器 - 渐进式披露 + 确认 + 审计"""

import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime

from .execution_context import ExecutionContext
from .skill_response import SkillResponse


class SecurityInterceptor:
    """安全拦截器（渐进式披露 + 确认 + 审计）"""

    def __init__(self, config: Dict[str, Any]):
        """初始化安全拦截器

        Args:
            config: 系统配置
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.audit_log_path = config.get("audit_log_path", ".lingxi/data/audit.log")
        
        # 确保审计日志目录存在
        import os
        os.makedirs(os.path.dirname(self.audit_log_path), exist_ok=True)

    def disclose_stage1(self, skill_id: str, skill_info: Dict[str, Any]) -> Dict[str, Any]:
        """第一阶段披露：基础信息

        Args:
            skill_id: 技能ID
            skill_info: 技能信息

        Returns:
            披露信息
        """
        disclosure = {
            "skill_id": skill_id,
            "name": skill_info.get("name", skill_id),
            "version": skill_info.get("version", "1.0.0"),
            "description": skill_info.get("description", ""),
            "author": skill_info.get("author", ""),
            "trust_level": skill_info.get("trust_level", "L1"),
            "isolated_env": skill_info.get("isolated_env", False)
        }
        
        self.logger.debug(f"第一阶段披露: {disclosure}")
        return disclosure

    def disclose_stage2(self, skill_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """第二阶段披露：能力参数

        Args:
            skill_id: 技能ID
            params: 技能参数

        Returns:
            披露信息
        """
        # 脱敏处理参数
        sanitized_params = self._sanitize_params(params)
        
        disclosure = {
            "skill_id": skill_id,
            "parameters": sanitized_params,
            "parameter_count": len(params)
        }
        
        self.logger.debug(f"第二阶段披露: {disclosure}")
        return disclosure

    def disclose_stage3(self, skill_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """第三阶段披露：风险披露

        Args:
            skill_id: 技能ID
            params: 技能参数

        Returns:
            披露信息
        """
        # 分析风险
        risks = self._analyze_risks(skill_id, params)
        
        disclosure = {
            "skill_id": skill_id,
            "risks": risks,
            "risk_level": "HIGH" if risks else "LOW",
            "warning": "此操作可能存在安全风险，请谨慎执行"
        }
        
        self.logger.warning(f"第三阶段披露: {disclosure}")
        return disclosure

    def require_confirm(self) -> bool:
        """要求用户确认

        Returns:
            是否确认执行
        """
        # 这里是模拟实现，实际应该弹出确认对话框
        # 暂时默认返回 True，允许执行
        return True

    def audit_log(self, skill_id: str, params: Dict[str, Any], response: SkillResponse, context: ExecutionContext):
        """安全审计日志

        Args:
            skill_id: 技能ID
            params: 技能参数
            response: 执行结果
            context: 执行上下文
        """
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "trace_id": context.trace_id,
            "skill_id": skill_id,
            "user_id": context.user_id,
            "workspace": context.workspace,
            "trust_level": context.trust_level.value if hasattr(context.trust_level, "value") else context.trust_level,
            "parameters": self._sanitize_params(params),
            "success": response.success,
            "code": response.code,
            "message": response.message,
            "cost_ms": response.meta.get("cost_ms", 0),
            "permissions": context.permissions
        }
        
        # 写入审计日志
        try:
            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                json.dump(audit_entry, f, ensure_ascii=False)
                f.write("\n")
            
            self.logger.debug(f"审计日志已记录: {skill_id}")
        except Exception as e:
            self.logger.error(f"写入审计日志失败: {e}")

    def _sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """脱敏处理参数

        Args:
            params: 原始参数

        Returns:
            脱敏后的参数
        """
        sanitized = {}
        sensitive_keys = ["password", "token", "secret", "key", "api_key"]
        
        for key, value in params.items():
            if key.lower() in sensitive_keys:
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_params(value)
            else:
                sanitized[key] = value
        
        return sanitized

    def _analyze_risks(self, skill_id: str, params: Dict[str, Any]) -> list:
        """分析风险

        Args:
            skill_id: 技能ID
            params: 技能参数

        Returns:
            风险列表
        """
        risks = []
        
        # 检查危险技能
        dangerous_skills = ["execute", "shell", "system"]
        if skill_id in dangerous_skills:
            risks.append("执行系统命令可能导致安全风险")
        
        # 检查危险参数
        if skill_id == "execute" and isinstance(params.get("command"), str):
            command = params["command"]
            dangerous_commands = ["rm -rf", "format", "del", "erase"]
            for dangerous in dangerous_commands:
                if dangerous in command.lower():
                    risks.append(f"命令包含危险操作: {dangerous}")
        
        # 检查文件操作
        if "file" in skill_id.lower() or "path" in skill_id.lower():
            risks.append("文件操作可能导致数据泄露或损坏")
        
        return risks

    def check_permission(self, skill_id: str, action: str) -> bool:
        """检查权限

        Args:
            skill_id: 技能ID
            action: 操作类型

        Returns:
            是否有权限
        """
        # 简单的权限检查实现
        # 实际应该从权限系统获取
        allowed_actions = {
            "read": ["file", "pdf", "docx", "xlsx"],
            "write": ["file", "pdf", "docx", "xlsx"],
            "execute": ["execute", "shell"]
        }
        
        allowed_skills = allowed_actions.get(action, [])
        return any(skill in skill_id for skill in allowed_skills)

    def intercept(self):
        """拦截危险操作"""
        # 这里可以实现具体的拦截逻辑
        # 例如钩子函数、系统调用拦截等
        pass

    def release(self):
        """释放拦截"""
        # 释放拦截资源
        pass