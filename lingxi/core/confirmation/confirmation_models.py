"""Confirmation 数据模型模块"""

import asyncio
from typing import Dict, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class RiskLevel(str, Enum):
    """风险级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ConfirmationRequest:
    """确认请求"""
    request_id: str
    operation: str
    description: str
    risk_level: RiskLevel
    created_at: datetime
    timeout: int = 60
    metadata: Optional[Dict] = None


@dataclass
class ConfirmationResponse:
    """确认响应"""
    request_id: str
    confirmed: bool
    responded_at: datetime
    reason: Optional[str] = None
