#!/usr/bin/env python3
"""
测试完整的异步引擎流程

模拟 WebSocket 调用异步引擎的完整流程
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from lingxi.utils.config import load_config
from lingxi.core.assistant import AsyncLingxiAssistant


async def test_full_engine():
    """测试完整的引擎流程"""
    print("="*60)
    print("测试完整的异步引擎流程")
    print("="*60)
    
    config = load_config()
    assistant = AsyncLingxiAssistant(config)
    
    test_messages = [
        "你好",
        "1+1 等于几？",
        "请帮我写一首关于春天的短诗"
    ]
    
    for message in test_messages:
        print(f"\n{'='*60}")
        print(f"测试消息：{message}")
        print(f"{'='*60}")
        
        try:
            # 使用流式处理
            response_generator = assistant.stream_process_input(message, session_id="test_session")
            
            print("\n接收响应流:\n")
            async for chunk in response_generator:
                chunk_type = chunk.get("type", "unknown")
                
                if chunk_type == "task_start":
                    print(f"[任务开始] executionId: {chunk['payload'].get('executionId')}")
                
                elif chunk_type == "step_start":
                    print(f"[步骤开始] step: {chunk['payload'].get('step')}")
                
                elif chunk_type == "thought_stream":
                    thought = chunk['payload'].get('thought', '')
                    print(f"[思考] {thought[:50]}..." if len(thought) > 50 else f"[思考] {thought}")
                
                elif chunk_type == "step_end":
                    payload = chunk['payload']
                    print(f"[步骤结束] status: {payload.get('status')}")
                    if payload.get('observation'):
                        print(f"  观察：{payload['observation'][:50]}..." if len(payload['observation']) > 50 else f"  观察：{payload['observation']}")
                
                elif chunk_type == "stream_end":
                    print(f"[流式结束]")
                
                elif chunk_type == "stream_error":
                    print(f"[流式错误] {chunk.get('error')}")
                
                else:
                    print(f"[{chunk_type}] {chunk.get('payload', chunk)}")
            
            print(f"\n✅ 消息处理完成")
            
        except Exception as e:
            print(f"\n❌ 处理失败：{e}")
            import traceback
            traceback.print_exc()
            break
    
    print(f"\n{'='*60}")
    print("测试完成")
    print(f"{'='*60}")


async def main():
    """主函数"""
    await test_full_engine()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试异常：{e}")
        import traceback
        traceback.print_exc()
