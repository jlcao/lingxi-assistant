"""WebSocket 消息协议模块"""

import asyncio
from typing import Dict, Any, Optional


class WebSocketMessage:
    """WebSocket 消息协议"""

    @staticmethod
    def create_response(message_type: str, data: Dict[str, Any], success: bool = True) -> Dict[str, Any]:
        """创建响应消息

        Args:
            message_type: 消息类型
            data: 消息数据
            success: 是否成功

        Returns:
            响应消息
        """
        return {
            "type": message_type,
            "payload": data,
            "timestamp": asyncio.get_event_loop().time()
        }

    @staticmethod
    def create_stream_chunk(message_type: str, content: str, chunk_index: int,
                           is_last: bool = False, metadata: Dict = None, stream_id: str = None) -> Dict[str, Any]:
        """创建流式消息块

        Args:
            message_type: 消息类型
            content: 内容
            chunk_index: 块索引
            is_last: 是否最后一块
            metadata: 元数据
            stream_id: 流 ID

        Returns:
            流式消息块
        """
        result = {
            "type": message_type,
            "stream": True,
            "chunk_index": chunk_index,
            "is_last": is_last,
            "content": content,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        if metadata:
            result["metadata"] = metadata
        
        if stream_id:
            result["streamId"] = stream_id
            
        return result

    @staticmethod
    def create_error(message_type: str, error: str, details: str = None) -> Dict[str, Any]:
        """创建错误消息

        Args:
            message_type: 消息类型
            error: 错误信息
            details: 详细信息

        Returns:
            错误消息
        """
        return {
            "type": message_type,
            "success": False,
            "error": error,
            "details": details,
            "timestamp": asyncio.get_event_loop().time()
        }
