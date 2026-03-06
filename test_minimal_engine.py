#!/usr/bin/env python3
"""
最小化测试：直接测试异步引擎

排除所有其他因素，只测试核心的异步引擎
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from lingxi.utils.config import load_config
from lingxi.core.engine.async_react_core import AsyncReActCore
from lingxi.core.skill_caller import SkillCaller
from lingxi.core.session import SessionManager
from lingxi.core.context import TaskContext


async def test_minimal_engine():
    """最小化引擎测试"""
    print("="*60)
    print("最小化异步引擎测试")
    print("="*60)
    
    config = load_config()
    skill_caller = SkillCaller(config)
    session_manager = SessionManager(config)
    engine = AsyncReActCore(config, skill_caller, session_manager)
    
    # 创建任务上下文
    context = TaskContext(
        user_input="你好",
        task_info={"level": "simple"},
        session_id="test_minimal",
        session_history=[],
        stream=True
    )
    
    print(f"\n用户输入：{context.user_input}")
    print(f"任务级别：{context.task_info['level']}")
    print(f"流式：{context.stream}")
    print()
    
    try:
        # 直接调用引擎的 process 方法
        print("开始处理...\n")
        result = await engine.process(context)
        
        # 如果是异步生成器，遍历它
        if hasattr(result, '__aiter__'):
            async for chunk in result:
                chunk_type = chunk.get("type", "unknown")
                payload = chunk.get("payload", chunk)
                
                if chunk_type == "task_start":
                    print(f"[任务开始]")
                elif chunk_type == "step_start":
                    print(f"[步骤 {payload.get('step')}] 开始")
                elif chunk_type == "think_stream":
                    thought = payload.get('thought', '')
                    print(f"  [思考] {thought[:50]}..." if len(thought) > 50 else f"  [思考] {thought}")
                elif chunk_type == "step_end":
                    print(f"[步骤 {payload.get('step')}] 结束 - status: {payload.get('status')}")
                    if payload.get('observation'):
                        obs = payload['observation']
                        print(f"  观察：{obs[:50]}..." if len(obs) > 50 else f"  观察：{obs}")
                elif chunk_type == "stream_end":
                    print(f"[流式结束]")
                elif chunk_type == "stream_error":
                    print(f"[流式错误] {payload.get('error', 'Unknown error')}")
                else:
                    print(f"[{chunk_type}] {str(payload)[:100]}")
        else:
            # 如果是字符串，直接打印
            print(f"响应：{result}")
        
        print("\n✅ 处理完成！")
        
    except Exception as e:
        print(f"\n❌ 处理失败：{e}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.async_llm_client.close()


async def main():
    """主函数"""
    await test_minimal_engine()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试异常：{e}")
        import traceback
        traceback.print_exc()
