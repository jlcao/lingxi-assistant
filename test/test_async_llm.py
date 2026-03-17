#!/usr/bin/env python3
"""
测试异步 LLM 调用

验证异步 LLM 客户端是否正常工作
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from lingxi.utils.config import load_config
from lingxi.core.llm import AsyncLLMClient


async def test_llm_chat():
    """测试 LLM 流式聊天"""
    print("="*60)
    print("测试异步 LLM 流式聊天")
    print("="*60)
    
    config = load_config()
    client = AsyncLLMClient(config)
    
    messages = [
        {"role": "system", "content": "你是一个有帮助的助手。"},
        {"role": "user", "content": "你好，请简单回复我。"}
    ]
    
    print(f"\n发送消息：{messages[-1]['content']}")
    print("等待 LLM 响应...\n")
    
    try:
        full_response = ""
        async for chunk in client.stream_chat(messages, task_level="simple"):
            print(f"收到块：{chunk.keys() if isinstance(chunk, dict) else type(chunk)}")
            
            choices = chunk.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                if "content" in delta:
                    content = delta["content"]
                    full_response += content
                    print(f"内容：{repr(content)}")
            
            if chunk.get("usage"):
                print(f"Token 使用：{chunk['usage']}")
        
        print(f"\n完整响应：{repr(full_response)}")
        
        if not full_response:
            print("\n❌ 警告：LLM 返回了空响应！")
            print("可能原因：")
            print("  1. API 密钥无效")
            print("  2. 模型配置错误")
            print("  3. 网络连接问题")
            print("  4. 服务提供商问题")
        else:
            print("\n✅ LLM 响应正常！")
        
        return full_response
        
    except Exception as e:
        print(f"\n❌ LLM 调用失败：{e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        await client.close()


async def main():
    """主函数"""
    response = await test_llm_chat()
    
    print("\n" + "="*60)
    if response:
        print("✅ 测试成功！")
    else:
        print("❌ 测试失败！")
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
