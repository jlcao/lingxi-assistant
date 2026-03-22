#!/usr/bin/env python3
"""WebSocket 客户端测试脚本"""

import websocket
import json
import time


def on_message(ws, message):
    """处理接收到的消息"""
    print(f"收到消息: {message}")


def on_error(ws, error):
    """处理错误"""
    print(f"错误: {error}")


def on_close(ws, close_status_code, close_msg):
    """处理连接关闭"""
    print("连接已关闭")


def on_open(ws):
    """处理连接打开"""
    print("连接已打开")
    # 发送订阅事件的请求
    ws.send(json.dumps({
        "type": "subscribe",
        "event_types": ["task_start", "task_end", "task_failed", "task_timeout"]
    }))


if __name__ == "__main__":
    # 连接到 WebSocket 服务器
    ws = websocket.WebSocketApp(
        "ws://localhost:8000/ws",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    # 启动 WebSocket 客户端
    ws.run_forever()
