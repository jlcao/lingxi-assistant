"""Web 服务模块"""
try:
    from lingxi.web.fastapi_server import app, init_app, run_server
except ImportError:
    app, init_app, run_server = None, None, None

try:
    from lingxi.web.websocket import WebSocketManager, WebSocketConnection, WebSocketMessage
except ImportError:
    WebSocketManager, WebSocketConnection, WebSocketMessage = None, None, None

try:
    from lingxi.web.state import get_assistant, set_assistant, get_websocket_manager, set_websocket_manager
except ImportError:
    get_assistant, set_assistant, get_websocket_manager, set_websocket_manager = None, None, None, None

# WebSocket 管理器将在运行时通过 set_websocket_manager 初始化
# 避免循环依赖问题

__all__ = [
    "app",
    "init_app",
    "run_server",
    "WebSocketManager",
    "WebSocketConnection",
    "WebSocketMessage",
    "get_assistant",
    "set_assistant",
    "get_websocket_manager",
    "set_websocket_manager"
]
