#!/usr/bin/env python3
"""统一技能响应标准类"""

import time
import uuid
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from enum import IntEnum


class ResponseCode(IntEnum):
    """响应码枚举"""
    SUCCESS = 200
    BAD_REQUEST = 400
    FORBIDDEN = 403
    NOT_FOUND = 404
    INTERNAL_ERROR = 500


@dataclass
class SkillResponse:
    """统一技能响应结构

    Attributes:
        success: 是否成功
        code: 响应码（200=成功 400=参数 403=安全 500=异常）
        data: 技能返回数据
        message: 提示/错误信息
        meta: 元数据（skill_id, version, trace_id, cost_ms）
    """
    success: bool = True
    code: int = ResponseCode.SUCCESS
    data: Any = None
    message: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if "timestamp" not in self.meta:
            self.meta["timestamp"] = time.time()

    @classmethod
    def success(
        cls,
        data: Any = None,
        message: str = "执行成功",
        skill_id: Optional[str] = None,
        version: Optional[str] = None,
        trace_id: Optional[str] = None,
        cost_ms: Optional[float] = None
    ) -> "SkillResponse":
        """创建成功响应

        Args:
            data: 返回数据
            message: 成功消息
            skill_id: 技能ID
            version: 技能版本
            trace_id: 追踪ID
            cost_ms: 耗时（毫秒）

        Returns:
            SkillResponse 实例
        """
        meta = {}
        if skill_id:
            meta["skill_id"] = skill_id
        if version:
            meta["version"] = version
        if trace_id:
            meta["trace_id"] = trace_id
        if cost_ms is not None:
            meta["cost_ms"] = cost_ms

        return cls(
            success=True,
            code=ResponseCode.SUCCESS,
            data=data,
            message=message,
            meta=meta
        )

    @classmethod
    def error(
        cls,
        message: str = "执行失败",
        code: int = ResponseCode.INTERNAL_ERROR,
        skill_id: Optional[str] = None,
        version: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> "SkillResponse":
        """创建错误响应

        Args:
            message: 错误消息
            code: 错误码
            skill_id: 技能ID
            version: 技能版本
            trace_id: 追踪ID

        Returns:
            SkillResponse 实例
        """
        meta = {}
        if skill_id:
            meta["skill_id"] = skill_id
        if version:
            meta["version"] = version
        if trace_id:
            meta["trace_id"] = trace_id

        return cls(
            success=False,
            code=code,
            data=None,
            message=message,
            meta=meta
        )

    @classmethod
    def forbidden(
        cls,
        message: str = "安全检查失败",
        skill_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> "SkillResponse":
        """创建权限禁止响应

        Args:
            message: 禁止消息
            skill_id: 技能ID
            trace_id: 追踪ID

        Returns:
            SkillResponse 实例
        """
        return cls.error(
            message=message,
            code=ResponseCode.FORBIDDEN,
            skill_id=skill_id,
            trace_id=trace_id
        )

    @classmethod
    def bad_request(
        cls,
        message: str = "参数错误",
        skill_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> "SkillResponse":
        """创建参数错误响应

        Args:
            message: 错误消息
            skill_id: 技能ID
            trace_id: 追踪ID

        Returns:
            SkillResponse 实例
        """
        return cls.error(
            message=message,
            code=ResponseCode.BAD_REQUEST,
            skill_id=skill_id,
            trace_id=trace_id
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典

        Returns:
            字典表示
        """
        return {
            "success": self.success,
            "code": self.code,
            "data": self.data,
            "message": self.message,
            "meta": self.meta
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillResponse":
        """从字典创建

        Args:
            data: 字典数据

        Returns:
            SkillResponse 实例
        """
        return cls(
            success=data.get("success", True),
            code=data.get("code", ResponseCode.SUCCESS),
            data=data.get("data"),
            message=data.get("message", ""),
            meta=data.get("meta", {})
        )

