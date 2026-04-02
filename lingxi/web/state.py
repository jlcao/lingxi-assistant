"""全局状态管理模块，避免循环导入"""
from typing import Optional, Union
from lingxi.__main__ import LingxiAssistant
from lingxi.core.assistant.async_main import AsyncLingxiAssistant
from lingxi.web.websocket import WebSocketManager


# 支持同步和异步助手
assistant: Optional[Union[LingxiAssistant, AsyncLingxiAssistant]] = None
websocket_manager: Optional[WebSocketManager] = None


def set_assistant(asst: Union[LingxiAssistant, AsyncLingxiAssistant]):
    """设置助手实例

    Args:
        asst: 灵犀助手实例（同步或异步）
    """
    global assistant
    assistant = asst
    
    # 修复：将 session_manager 设置到 workspace_manager 中
    # 检查是否是异步助手
    if hasattr(asst, 'action_caller') and hasattr(asst.action_caller, 'workspace_manager'):
        workspace_manager = asst.action_caller.workspace_manager
        if workspace_manager and hasattr(asst, 'session_manager'):
            workspace_manager.set_resources(
                session_store=asst.session_manager
            )
            import logging
            logger = logging.getLogger(__name__)
            logger.debug("workspace_manager.session_store 已设置（通过 set_assistant）")


def get_assistant() -> Optional[Union[LingxiAssistant, AsyncLingxiAssistant]]:
    """获取助手实例

    Returns:
        灵犀助手实例
    """
    return assistant


def set_websocket_manager(wsm: WebSocketManager):
    """设置 WebSocket 管理器实例

    Args:
        wsm: WebSocket 管理器实例
    """
    global websocket_manager
    websocket_manager = wsm


def get_websocket_manager() -> Optional[WebSocketManager]:
    """获取 WebSocket 管理器实例

    Returns:
        WebSocket 管理器实例
    """
    return websocket_manager
