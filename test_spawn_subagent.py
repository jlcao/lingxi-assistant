#!/usr/bin/env python3
"""
测试 spawn_subagent 技能
"""
import asyncio
import json
import websockets

async def test_spawn_subagent():
    """测试 spawn_subagent 技能"""
    url = "ws://localhost:8001/ws"
    
    async with websockets.connect(url) as websocket:
        print("连接已打开")
        
        # 接收欢迎消息
        welcome_msg = await websocket.recv()
        print(f"收到欢迎消息: {welcome_msg}")
        
        # 发送测试消息 - 测试 spawn_subagent 技能
        test_message = {
            "type": "stream_chat",
            "content": "使用子代理执行一个简单任务：计算 123 + 456",
            "session_id": "test_session_1"
        }
        
        print("发送测试消息...")
        await websocket.send(json.dumps(test_message))
        
        # 接收响应
        try:
            while True:
                response = await websocket.recv()
                print(f"收到消息: {response}")
        except websockets.exceptions.ConnectionClosed:
            print("连接已关闭")

if __name__ == "__main__":
    asyncio.run(test_spawn_subagent())
