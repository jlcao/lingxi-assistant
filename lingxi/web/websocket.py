"""WebSocket 模块 - 兼容性封装

为保持向后兼容，将三个独立类重新导出到同一命名空间
"""

from lingxi.web.websocket_message import WebSocketMessage
from lingxi.web.websocket_connection import WebSocketConnection
from lingxi.web.websocket_manager import WebSocketManager

__all__ = [
    "WebSocketMessage",
    "WebSocketConnection",
    "WebSocketManager",
]
