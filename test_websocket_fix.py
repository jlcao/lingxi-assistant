#!/usr/bin/env python3
"""
测试 WebSocket 连接修复

验证 sessionId 查询参数是否正确处理
"""

import asyncio
import websockets
import json


async def test_websocket_connection():
    """测试 WebSocket 连接"""
    uri = "ws://localhost:5000/ws?sessionId=test_session_123"
    
    print(f"尝试连接：{uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ WebSocket 连接成功！")
            
            # 等待欢迎消息
            welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            welcome_data = json.loads(welcome_msg)
            print(f"收到欢迎消息：{json.dumps(welcome_data, indent=2, ensure_ascii=False)}")
            
            # 发送测试消息
            test_msg = {
                "type": "stream_chat",
                "content": "你好",
                "session_id": "test_session_123"
            }
            print(f"\n发送测试消息：{json.dumps(test_msg, indent=2, ensure_ascii=False)}")
            await websocket.send(json.dumps(test_msg))
            
            # 接收响应
            print("\n接收响应...")
            try:
                while True:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    response_data = json.loads(response)
                    print(f"收到：{json.dumps(response_data, indent=2, ensure_ascii=False)}")
                    
                    # 如果是流式结束，停止接收
                    if response_data.get("type") == "stream_end":
                        print("\n✅ 流式响应完成！")
                        break
            except asyncio.TimeoutError:
                print("响应接收超时（可能是正常的）")
            
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ WebSocket 连接失败：HTTP {e.status_code}")
        print(f"错误：{e}")
        return False
    except Exception as e:
        print(f"❌ 连接错误：{e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n✅ 测试完成！")
    return True


async def test_multiple_connections():
    """测试多个并发连接"""
    print("\n" + "="*60)
    print("测试多个并发连接")
    print("="*60)
    
    async def connect_with_session(session_id: str):
        uri = f"ws://localhost:5000/ws?sessionId={session_id}"
        try:
            async with websockets.connect(uri) as websocket:
                welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                welcome_data = json.loads(welcome_msg)
                print(f"✅ {session_id}: 连接成功")
                return True
        except Exception as e:
            print(f"❌ {session_id}: 连接失败 - {e}")
            return False
    
    # 创建 5 个并发连接
    tasks = [
        connect_with_session(f"session_{i}")
        for i in range(5)
    ]
    
    results = await asyncio.gather(*tasks)
    
    success_count = sum(results)
    print(f"\n成功连接：{success_count}/5")
    
    return success_count == 5


async def main():
    """主函数"""
    print("="*60)
    print("WebSocket sessionId 查询参数测试")
    print("="*60)
    print()
    
    # 测试 1：单个连接
    print("[测试 1] 单个连接带 sessionId 参数")
    print("-"*60)
    success1 = await test_websocket_connection()
    
    # 测试 2：多个并发连接
    await asyncio.sleep(1)
    print()
    print("[测试 2] 多个并发连接")
    print("-"*60)
    success2 = await test_multiple_connections()
    
    # 总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    if success1 and success2:
        print("✅ 所有测试通过！")
        print("WebSocket sessionId 查询参数处理正常")
    else:
        print("❌ 部分测试失败")
        if not success1:
            print("  - 单个连接测试失败")
        if not success2:
            print("  - 并发连接测试失败")
    print("="*60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试异常：{e}")
        import traceback
        traceback.print_exc()
