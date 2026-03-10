"""Confirmation 模块 - 兼容性封装

为保持向后兼容，将数据模型和管理器重新导出到同一命名空间
"""

from lingxi.core.confirmation.confirmation_models import RiskLevel, ConfirmationRequest, ConfirmationResponse
from lingxi.core.confirmation.confirmation_manager import ConfirmationManager, DangerousSkillChecker

__all__ = [
    "RiskLevel",
    "ConfirmationRequest",
    "ConfirmationResponse",
    "ConfirmationManager",
    "DangerousSkillChecker",
]
