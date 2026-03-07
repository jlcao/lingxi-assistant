#!/usr/bin/env python3
"""
测试 ReAct 引擎的 LLM 响应解析

验证 LLM 是否返回正确的 JSON 格式
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from lingxi.utils.config import load_config
from lingxi.core.async_llm_client import AsyncLLMClient
from lingxi.core.engine.async_react_core import AsyncReActCore
from lingxi.core.skill_caller import SkillCaller
from lingxi.core.session import SessionManager


async def test_react_response():
    """测试 ReAct 引擎的 LLM 响应"""
    print("="*60)
    print("测试 ReAct 引擎的 LLM 响应解析")
    print("="*60)
    
    config = load_config()
    
    # 创建 ReAct 引擎
    skill_caller = SkillCaller(config)
    session_manager = SessionManager(config)
    engine = AsyncReActCore(config, skill_caller, session_manager)
    
    # 测试解析函数
    test_responses = [
        '{"thought": "用户在打招呼", "action": "finish", "action_input": "你好！有什么可以帮你的吗？"}',
        '{"thought": "需要查询天气", "action": "search", "action_input": {"query": "北京天气"}}',
        '你好！有什么可以帮你的吗？',  # 非 JSON 格式
        '',  # 空响应
        '{"thought": "思考中"}',  # 缺少 action 字段
    ]
    
    for i, response in enumerate(test_responses, 1):
        print(f"\n测试 {i}: {repr(response[:50]) if len(response) > 50 else repr(response)}")
        parsed = engine._parse_response(response)
        if parsed:
            print(f"  ✅ 解析成功：{parsed}")
        else:
            print(f"  ❌ 解析失败")
    
    # 实际调用 LLM
    print("\n" + "="*60)
    print("实际调用 LLM（使用 ReAct 提示词）")
    print("="*60)
    
    messages = [
        {
            "role": "system",
            "content": """你是一个智能助手，可以使用工具来帮助用户。
请以 JSON 格式返回响应，包含以下字段：
- thought: 你的思考过程
- action: 要执行的动作（search, calculate, finish 等）
- action_input: 动作的输入参数

示例：
{"thought": "用户想查询天气", "action": "search", "action_input": {"query": "北京天气"}}
{"thought": "已完成任务", "action": "finish", "action_input": "北京今天晴朗，温度 25 度"}
"""
        },
        {"role": "user", "content": "你好，请介绍一下你自己。"}
    ]
    
    print(f"\n发送消息到 LLM...\n")
    
    try:
        full_response = ""
        async for chunk in engine.async_llm_client.stream_chat(messages, task_level="simple"):
            choices = chunk.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                if "content" in delta:
                    content = delta["content"]
                    full_response += content
                    print(content, end="", flush=True)
        
        print(f"\n\n完整响应：{repr(full_response)}")
        
        print(f"\n尝试解析响应...")
        parsed = engine._parse_response(full_response)
        
        if parsed:
            print(f"✅ 解析成功：{parsed}")
        else:
            print(f"❌ 解析失败")
            print(f"   这可能导致引擎无法继续执行")
        
        return parsed
        
    except Exception as e:
        print(f"\n❌ LLM 调用失败：{e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        await engine.async_llm_client.close()


async def main():
    """主函数"""
    parsed = await test_react_response()
    
    print("\n" + "="*60)
    if parsed:
        print("✅ 测试成功！LLM 返回了正确的 JSON 格式")
    else:
        print("❌ 测试失败！LLM 没有返回正确的 JSON 格式")
        print("\n建议：")
        print("  1. 检查系统提示词是否正确")
        print("  2. 确认模型支持 JSON 格式输出")
        print("  3. 尝试更换模型（某些模型可能不支持 JSON）")
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
