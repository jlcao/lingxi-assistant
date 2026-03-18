"""Confirmation 管理器模块 - 高危操作确认和技能检查"""

import asyncio
import logging
import re
from datetime import datetime
from typing import Dict, Optional, Callable

from .confirmation_models import RiskLevel, ConfirmationRequest, ConfirmationResponse


class ConfirmationManager:
    """确认管理器（单例模式）"""
    
    _instance = None  # 单例实例
    
    def __new__(cls, timeout: int = 60, auto_reject_timeout: bool = True):
        """单例模式：确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, timeout: int = 60, auto_reject_timeout: bool = True):
        # 防止重复初始化
        if hasattr(self, '_initialized'):
            return
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
        
        self.logger.debug(f"确认管理器初始化：timeout={timeout}s, auto_reject={auto_reject_timeout}")
        self._initialized = True
    
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
            timeout: 超时时间（秒），使用默认值则为 None
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
        
        self.logger.debug(
            f"创建确认请求：id={request_id}, operation={operation}, "
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
            request_id: 请求 ID
            timeout: 超时时间（秒），使用请求默认值则为 None

        Returns:
            是否确认

        Raises:
            KeyError: 请求不存在
            asyncio.TimeoutError: 等待超时
        """
        if request_id not in self._responses:
            raise KeyError(f"确认请求不存在：{request_id}")
        
        request = self._pending_requests.get(request_id)
        wait_timeout = timeout or (request.timeout if request else self.timeout)
        
        self.logger.debug(f"等待确认：id={request_id}, timeout={wait_timeout}s")
        
        try:
            confirmed = await asyncio.wait_for(
                self._responses[request_id],
                timeout=wait_timeout
            )
            self.logger.debug(f"确认结果：id={request_id}, confirmed={confirmed}")
            return confirmed
        except asyncio.TimeoutError:
            if self.auto_reject_timeout:
                self.logger.warning(f"确认超时，自动拒绝：id={request_id}")
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
            request_id: 请求 ID
            confirmed: 是否确认
            reason: 拒绝原因（可选）

        Returns:
            是否成功响应

        Raises:
            KeyError: 请求不存在
        """
        if request_id not in self._pending_requests:
            self.logger.warning(f"确认请求不存在或已过期：{request_id}")
            return False
        
        if request_id not in self._responses:
            self.logger.warning(f"确认请求已完成：{request_id}")
            return False
        
        if self._responses[request_id].done():
            self.logger.warning(f"确认请求已响应：{request_id}")
            return False
        
        response = ConfirmationResponse(
            request_id=request_id,
            confirmed=confirmed,
            responded_at=datetime.now(),
            reason=reason
        )
        
        self._responses[request_id].set_result(confirmed)
        
        self.logger.debug(
            f"确认响应：id={request_id}, confirmed={confirmed}, "
            f"reason={reason}"
        )
        
        self._cleanup_request(request_id)
        return True
    
    def cancel_request(self, request_id: str) -> bool:
        """取消确认请求

        Args:
            request_id: 请求 ID

        Returns:
            是否成功取消
        """
        if request_id not in self._pending_requests:
            return False
        
        self._cleanup_request(request_id)
        self.logger.debug(f"取消确认请求：{request_id}")
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
            request_id: 请求 ID

        Returns:
            确认请求对象，不存在则返回 None
        """
        return self._pending_requests.get(request_id)
    
    def cleanup_expired_requests(self, max_age: int = 300):
        """清理过期的确认请求

        Args:
            max_age: 最大存活时间（秒），默认 5 分钟
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
            self.logger.debug(f"清理过期请求：{len(expired_ids)}个")
    
    def _cleanup_request(self, request_id: str):
        """清理确认请求

        Args:
            request_id: 请求 ID
        """
        self._pending_requests.pop(request_id, None)
        self._responses.pop(request_id, None)
    
    def register_callback(self, request_id: str, callback: Callable[[bool], None]):
        """注册确认回调函数

        Args:
            request_id: 请求 ID
            callback: 回调函数，接收确认结果
        """
        self._response_callbacks[request_id] = callback
    
    def trigger_callback(self, request_id: str, confirmed: bool):
        """触发确认回调

        Args:
            request_id: 请求 ID
            confirmed: 确认结果
        """
        if request_id in self._response_callbacks:
            callback = self._response_callbacks.pop(request_id)
            try:
                callback(confirmed)
            except Exception as e:
                self.logger.error(f"确认回调执行失败：{e}")


class DangerousSkillChecker:
    """高危技能检查器"""

    logger = logging.getLogger(__name__)
    
    DANGEROUS_SKILLS = {
        'system.exec': RiskLevel.HIGH,
        'file.write': RiskLevel.MEDIUM,
        'file.delete': RiskLevel.HIGH,
        'file.create': RiskLevel.LOW,
        'shell.exec': RiskLevel.CRITICAL,
        'network.request': RiskLevel.MEDIUM
    }
    
    DANGEROUS_PATTERNS = [
        r'(?<!-)\brm\b(?![a-z-])', r'(?<!-)\bdel\b(?![a-z-])', r'(?<!-)\bformat\b(?![a-z-])', r'(?<!-)\bshutdown\b(?![a-z-])', r'(?<!-)\breboot\b(?![a-z-])',
        r'(?<!-)\bdrop\b(?![a-z-])', r'(?<!-)\btruncate\b(?![a-z-])', r'(?<!-)\bdelete from\b', r'(?<!-)\btruncate table\b'
    ]
    
    @classmethod
    def check_skill_risk(cls, skill_id: str) -> RiskLevel:
        """检查技能风险级别

        Args:
            skill_id: 技能 ID

        Returns:
            风险级别
        """
        return cls.DANGEROUS_SKILLS.get(skill_id, RiskLevel.LOW)
    
    @classmethod
    def check_command_risk(cls, command: str) -> RiskLevel:
        """检查命令风险级别

        Args:
            command: 命令内容

        Returns:
            风险级别
        """
        command_lower = command.lower()
        
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, command_lower):
                cls.logger.warning(f"检测到高危命令模式：{pattern} 在命令中 ：{command}")
                return RiskLevel.HIGH
        
        return RiskLevel.LOW
    
    @classmethod
    def is_dangerous(cls, skill_id: str = None, command: str = None) -> bool:
        """检查是否为高危操作

        Args:
            skill_id: 技能 ID
            command: 命令内容

        Returns:
            是否高危
        """
        if skill_id:
            risk = cls.check_skill_risk(skill_id)
            return risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        
        if command:
            risk = cls.check_command_risk(command)
            return risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        
        return False
