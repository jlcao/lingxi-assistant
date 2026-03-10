"""接口定义模块

定义核心接口，实现依赖倒置原则
"""

from typing import Protocol, runtime_checkable, Any, Dict, List, Optional
from abc import ABC, abstractmethod


@runtime_checkable
class ISessionManager(Protocol):
    """会话管理器接口"""
    
    def create_session(self, session_id: str, user_input: str, task_type: str) -> None:
        """创建会话"""
        ...
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话"""
        ...
    
    def update_session(self, session_id: str, **kwargs) -> None:
        """更新会话"""
        ...
    
    def add_step(self, session_id: str, step: Dict[str, Any]) -> None:
        """添加步骤"""
        ...
    
    def get_history(self, session_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """获取历史记录"""
        ...


@runtime_checkable
class ISkillCaller(Protocol):
    """技能调用器接口"""
    
    def call_skill(self, skill_name: str, parameters: Dict[str, Any]) -> str:
        """调用技能"""
        ...
    
    def list_skills(self) -> List[Dict[str, Any]]:
        """列出所有技能"""
        ...


@runtime_checkable
class ILLMClient(Protocol):
    """LLM客户端接口"""
    
    def generate(self, prompt: str, **kwargs) -> str:
        """生成响应"""
        ...
    
    def generate_stream(self, prompt: str, **kwargs):
        """流式生成响应"""
        ...


@runtime_checkable
class IEventPublisher(Protocol):
    """事件发布器接口"""
    
    def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        """发布事件"""
        ...
    
    def subscribe(self, event_type: str, callback) -> None:
        """订阅事件"""
        ...


@runtime_checkable
class IWorkspaceManager(Protocol):
    """工作区管理器接口"""
    
    def get_current_workspace(self) -> Optional[str]:
        """获取当前工作区"""
        ...
    
    def set_workspace(self, workspace_id: str) -> bool:
        """设置工作区"""
        ...
    
    def list_workspaces(self) -> List[Dict[str, Any]]:
        """列出所有工作区"""
        ...


__all__ = [
    "ISessionManager",
    "ISkillCaller",
    "ILLMClient",
    "IEventPublisher",
    "IWorkspaceManager",
]
