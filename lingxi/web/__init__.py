"""Web服务模块"""
from lingxi.web.fastapi_server import app, init_app, run_server
from lingxi.web.websocket import WebSocketManager, WebSocketConnection, WebSocketMessage
from lingxi.web.state import get_assistant, set_assistant, get_websocket_manager, set_websocket_manager

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
