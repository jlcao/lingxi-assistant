#!/usr/bin/env python3
"""全链路执行上下文"""

import time
import uuid
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class TrustLevel(str, Enum):
    """信任等级"""
    L1 = "L1"
    L2 = "L2"


@dataclass
class ExecutionContext:
    """全链路执行上下文

    Attributes:
        trace_id: 追踪ID
        user_id: 用户ID
        skill_id: 技能ID
        trust_level: 信任等级（L1/L2）
        permissions: 权限列表
        timestamp: 时间戳
        workspace: 工作目录
        extra: 扩展字段
    """
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    skill_id: Optional[str] = None
    trust_level: TrustLevel = TrustLevel.L1
    permissions: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    workspace: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典

        Returns:
            字典表示
        """
        return {
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "skill_id": self.skill_id,
            "trust_level": self.trust_level.value if isinstance(self.trust_level, TrustLevel) else self.trust_level,
            "permissions": self.permissions,
            "timestamp": self.timestamp,
            "workspace": self.workspace,
            "extra": self.extra
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionContext":
        """从字典创建

        Args:
            data: 字典数据

        Returns:
            ExecutionContext 实例
        """
        trust_level = data.get("trust_level", TrustLevel.L1)
        if isinstance(trust_level, str):
            trust_level = TrustLevel(trust_level)

        return cls(
            trace_id=data.get("trace_id", str(uuid.uuid4())),
            user_id=data.get("user_id"),
            skill_id=data.get("skill_id"),
            trust_level=trust_level,
            permissions=data.get("permissions", []),
            timestamp=data.get("timestamp", time.time()),
            workspace=data.get("workspace"),
            extra=data.get("extra", {})
        )

    def clone(self) -> "ExecutionContext":
        """克隆上下文（保留 trace_id）

        Returns:
            新的 ExecutionContext 实例
        """
        data = self.to_dict()
        ctx = ExecutionContext.from_dict(data)
        ctx.trace_id = self.trace_id
        return ctx

    def with_skill(self, skill_id: str, trust_level: Optional[TrustLevel] = None) -> "ExecutionContext":
        """设置技能信息

        Args:
            skill_id: 技能ID
            trust_level: 信任等级

        Returns:
            新的 ExecutionContext 实例
        """
        ctx = self.clone()
        ctx.skill_id = skill_id
        if trust_level:
            ctx.trust_level = trust_level
        return ctx

    def with_workspace(self, workspace: str) -> "ExecutionContext":
        """设置工作目录

        Args:
            workspace: 工作目录

        Returns:
            新的 ExecutionContext 实例
        """
        ctx = self.clone()
        ctx.workspace = workspace
        return ctx

    def add_permission(self, permission: str) -> "ExecutionContext":
        """添加权限

        Args:
            permission: 权限

        Returns:
            新的 ExecutionContext 实例
        """
        ctx = self.clone()
        if permission not in ctx.permissions:
            ctx.permissions.append(permission)
        return ctx

    def has_permission(self, permission: str) -> bool:
        """检查是否有权限

        Args:
            permission: 权限

        Returns:
            是否有权限
        """
        return permission in self.permissions

    def set_extra(self, key: str, value: Any) -> "ExecutionContext":
        """设置扩展字段

        Args:
            key: 键
            value: 值

        Returns:
            新的 ExecutionContext 实例
        """
        ctx = self.clone()
        ctx.extra[key] = value
        return ctx

    def get_extra(self, key: str, default: Any = None) -> Any:
        """获取扩展字段

        Args:
            key: 键
            default: 默认值

        Returns:
            值
        """
        return self.extra.get(key, default)

