"""全局状态管理模块，避免循环导入"""
from typing import Optional, Union
from lingxi.__main__ import LingxiAssistant
from lingxi.core.async_main import AsyncLingxiAssistant
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
