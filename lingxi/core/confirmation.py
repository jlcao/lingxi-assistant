"""高危操作确认管理器

提供高危操作的二次确认机制
"""

import asyncio
import logging
from typing import Dict, Optional, Callable
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta


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


class ConfirmationManager:
    """确认管理器"""
    
    def __init__(self, timeout: int = 60, auto_reject_timeout: bool = True):
        """初始化确认管理器

        Args:
            timeout: 默认超时时间（秒）
            auto_reject_timeout: 超时是否自动拒绝
        """
        self.timeout = timeout
        self.auto_reject_timeout = auto_reject_timeout
        self._pending_requests: Dict[str, ConfirmationRequest] = {}
        self._responses: Dict[str, asyncio.Future] = {}
        self._response_callbacks: Dict[str, Callable] = {}
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"确认管理器初始化: timeout={timeout}s, auto_reject={auto_reject_timeout}")
    
    def create_request(
        self,
        operation: str,
        description: str,
        risk_level: RiskLevel = RiskLevel.MEDIUM,
        timeout: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> ConfirmationRequest:
        """创建确认请求

        Args:
            operation: 操作名称
            description: 操作描述
            risk_level: 风险级别
            timeout: 超时时间（秒），使用默认值则为None
            metadata: 附加元数据

        Returns:
            确认请求对象
        """
        import uuid
        request_id = str(uuid.uuid4())
        
        request = ConfirmationRequest(
            request_id=request_id,
            operation=operation,
            description=description,
            risk_level=risk_level,
            created_at=datetime.now(),
            timeout=timeout or self.timeout,
            metadata=metadata
        )
        
        self._pending_requests[request_id] = request
        self._responses[request_id] = asyncio.Future()
        
        self.logger.info(
            f"创建确认请求: id={request_id}, operation={operation}, "
            f"risk={risk_level}, timeout={request.timeout}s"
        )
        
        return request
    
    async def wait_for_confirmation(
        self,
        request_id: str,
        timeout: Optional[int] = None
    ) -> bool:
        """等待用户确认

        Args:
            request_id: 请求ID
            timeout: 超时时间（秒），使用请求默认值则为None

        Returns:
            是否确认

        Raises:
            KeyError: 请求不存在
            asyncio.TimeoutError: 等待超时
        """
        if request_id not in self._responses:
            raise KeyError(f"确认请求不存在: {request_id}")
        
        request = self._pending_requests.get(request_id)
        wait_timeout = timeout or (request.timeout if request else self.timeout)
        
        self.logger.debug(f"等待确认: id={request_id}, timeout={wait_timeout}s")
        
        try:
            confirmed = await asyncio.wait_for(
                self._responses[request_id],
                timeout=wait_timeout
            )
            self.logger.info(f"确认结果: id={request_id}, confirmed={confirmed}")
            return confirmed
        except asyncio.TimeoutError:
            if self.auto_reject_timeout:
                self.logger.warning(f"确认超时，自动拒绝: id={request_id}")
                self._cleanup_request(request_id)
                return False
            else:
                raise
    
    def respond_confirmation(
        self,
        request_id: str,
        confirmed: bool,
        reason: Optional[str] = None
    ) -> bool:
        """响应对确认请求

        Args:
            request_id: 请求ID
            confirmed: 是否确认
            reason: 拒绝原因（可选）

        Returns:
            是否成功响应

        Raises:
            KeyError: 请求不存在
        """
        if request_id not in self._pending_requests:
            self.logger.warning(f"确认请求不存在或已过期: {request_id}")
            return False
        
        if request_id not in self._responses:
            self.logger.warning(f"确认请求已完成: {request_id}")
            return False
        
        if self._responses[request_id].done():
            self.logger.warning(f"确认请求已响应: {request_id}")
            return False
        
        response = ConfirmationResponse(
            request_id=request_id,
            confirmed=confirmed,
            responded_at=datetime.now(),
            reason=reason
        )
        
        self._responses[request_id].set_result(confirmed)
        
        self.logger.info(
            f"确认响应: id={request_id}, confirmed={confirmed}, "
            f"reason={reason}"
        )
        
        self._cleanup_request(request_id)
        return True
    
    def cancel_request(self, request_id: str) -> bool:
        """取消确认请求

        Args:
            request_id: 请求ID

        Returns:
            是否成功取消
        """
        if request_id not in self._pending_requests:
            return False
        
        self._cleanup_request(request_id)
        self.logger.info(f"取消确认请求: {request_id}")
        return True
    
    def get_pending_requests(self) -> Dict[str, ConfirmationRequest]:
        """获取所有待确认的请求

        Returns:
            待确认请求字典
        """
        return self._pending_requests.copy()
    
    def get_request(self, request_id: str) -> Optional[ConfirmationRequest]:
        """获取确认请求

        Args:
            request_id: 请求ID

        Returns:
            确认请求对象，不存在则返回None
        """
        return self._pending_requests.get(request_id)
    
    def cleanup_expired_requests(self, max_age: int = 300):
        """清理过期的确认请求

        Args:
            max_age: 最大存活时间（秒），默认5分钟
        """
        now = datetime.now()
        expired_ids = []
        
        for request_id, request in self._pending_requests.items():
            age = (now - request.created_at).total_seconds()
            if age > max_age:
                expired_ids.append(request_id)
        
        for request_id in expired_ids:
            self.cancel_request(request_id)
        
        if expired_ids:
            self.logger.info(f"清理过期请求: {len(expired_ids)}个")
    
    def _cleanup_request(self, request_id: str):
        """清理确认请求

        Args:
            request_id: 请求ID
        """
        self._pending_requests.pop(request_id, None)
        self._responses.pop(request_id, None)
    
    def register_callback(self, request_id: str, callback: Callable[[bool], None]):
        """注册确认回调函数

        Args:
            request_id: 请求ID
            callback: 回调函数，接收确认结果
        """
        self._response_callbacks[request_id] = callback
    
    def trigger_callback(self, request_id: str, confirmed: bool):
        """触发确认回调

        Args:
            request_id: 请求ID
            confirmed: 确认结果
        """
        if request_id in self._response_callbacks:
            callback = self._response_callbacks.pop(request_id)
            try:
                callback(confirmed)
            except Exception as e:
                self.logger.error(f"确认回调执行失败: {e}")


class DangerousSkillChecker:
    """高危技能检查器"""
    
    DANGEROUS_SKILLS = {
        'system.exec': RiskLevel.HIGH,
        'file.write': RiskLevel.MEDIUM,
        'file.delete': RiskLevel.HIGH,
        'file.create': RiskLevel.LOW,
        'shell.exec': RiskLevel.CRITICAL,
        'network.request': RiskLevel.MEDIUM
    }
    
    DANGEROUS_PATTERNS = [
        'rm', 'del', 'format', 'shutdown', 'reboot',
        'drop', 'truncate', 'delete from', 'truncate table'
    ]
    
    @classmethod
    def check_skill_risk(cls, skill_id: str) -> RiskLevel:
        """检查技能风险级别

        Args:
            skill_id: 技能ID

        Returns:
            风险级别
        """
        return cls.DANGEROUS_SKILLS.get(skill_id, RiskLevel.LOW)
    
    @classmethod
    def check_command_risk(cls, command: str) -> RiskLevel:
        """检查命令风险级别

        Args:
            command: 命令字符串

        Returns:
            风险级别
        """
        command_lower = command.lower()
        
        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern in command_lower:
                if pattern in ['rm', 'del', 'format']:
                    return RiskLevel.HIGH
                elif pattern in ['shutdown', 'reboot']:
                    return RiskLevel.CRITICAL
                else:
                    return RiskLevel.MEDIUM
        
        return RiskLevel.LOW
    
    @classmethod
    def is_dangerous(cls, skill_id: str, command: Optional[str] = None) -> bool:
        """检查是否为高危操作

        Args:
            skill_id: 技能ID
            command: 命令（可选）

        Returns:
            是否高危
        """
        skill_risk = cls.check_skill_risk(skill_id)
        if skill_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            return True
        
        if command:
            command_risk = cls.check_command_risk(command)
            if command_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                return True
        
        return False
    
    @classmethod
    def get_risk_description(cls, risk_level: RiskLevel) -> str:
        """获取风险级别描述

        Args:
            risk_level: 风险级别

        Returns:
            风险描述
        """
        descriptions = {
            RiskLevel.LOW: "低风险",
            RiskLevel.MEDIUM: "中等风险",
            RiskLevel.HIGH: "高风险",
            RiskLevel.CRITICAL: "严重风险"
        }
        return descriptions.get(risk_level, "未知风险")
