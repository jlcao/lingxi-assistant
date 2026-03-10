"""WebSocket 连接封装模块"""

import asyncio
import logging
from typing import Dict, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketConnection:
    """WebSocket 连接封装"""

    def __init__(self, websocket: WebSocket, connection_id: str):
        """初始化连接

        Args:
            websocket: WebSocket 对象
            connection_id: 连接 ID
        """
        self.websocket = websocket
        self.connection_id = connection_id
        self.session_id = "default"
        self.is_connected = True
        self.last_activity = asyncio.get_event_loop().time()

    async def send_json(self, data: Dict[str, Any]):
        """发送 JSON 消息

        Args:
            data: 消息数据

        Returns:
            是否发送成功
        """
        if not self.is_connected:
            return False
        try:
            await self.websocket.send_json(data)
            self.last_activity = asyncio.get_event_loop().time()
            return True
        except Exception as e:
            logger.debug(f"发送 JSON 消息失败：{e}")
            self.is_connected = False
            return False

    async def send_text(self, text: str):
        """发送文本消息

        Args:
            text: 文本内容

        Returns:
            是否发送成功
        """
        if not self.is_connected:
            return False
        try:
            await self.websocket.send_text(text)
            self.last_activity = asyncio.get_event_loop().time()
            return True
        except Exception as e:
            logger.debug(f"发送文本消息失败：{e}")
            self.is_connected = False
            return False

    def update_activity(self):
        """更新活动时间"""
        self.last_activity = asyncio.get_event_loop().time()

    def disconnect(self):
        """断开连接"""
        self.is_connected = False
