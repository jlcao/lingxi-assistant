"""流式响应API测试脚本

测试 /api/tasks/stream 接口的流式响应功能
"""

import asyncio
import aiohttp
import json
from typing import AsyncGenerator


class StreamAPITester:
    """流式API测试器"""

    def __init__(self, base_url: str = "http://localhost:5000"):
        """初始化测试器

        Args:
            base_url: API基础URL
        """
        self.base_url = base_url

    async def test_stream_task(self, task: str, session_id: str = "test_session") -> dict:
        """测试流式任务执行

        Args:
            task: 任务内容
            session_id: 会话ID

        Returns:
            测试结果统计
        """
        url = f"{self.base_url}/api/tasks/stream"
        payload = {
            "task": task,
            "session_id": session_id,
            "enable_heartbeat": True,
            "heartbeat_interval": 30
        }

        result = {
            "task": task,
            "events": [],
            "event_counts": {},
            "errors": [],
            "success": False
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        result["errors"].append(f"HTTP错误: {response.status} - {error_text}")
                        return result

                    async for line in response.content:
                        line_text = line.decode('utf-8').strip()
                        
                        if not line_text:
                            continue
                        
                        if line_text.startswith(':'):
                            continue
                        
                        if line_text.startswith('data: '):
                            try:
                                event_data = json.loads(line_text[6:])
                                event_type = event_data.get('event_type', 'unknown')
                                
                                result["events"].append(event_data)
                                result["event_counts"][event_type] = result["event_counts"].get(event_type, 0) + 1
                                
                                print(f"[{event_type}] {json.dumps(event_data.get('data', {}), ensure_ascii=False)[:100]}")
                                
                            except json.JSONDecodeError as e:
                                result["errors"].append(f"JSON解析错误: {e} - {line_text}")

                    result["success"] = True
                    
        except aiohttp.ClientError as e:
            result["errors"].append(f"网络错误: {e}")
        except Exception as e:
            result["errors"].append(f"未知错误: {e}")

        return result

    async def test_abort_controller(self, task: str, session_id: str = "test_session") -> dict:
        """测试AbortController取消功能

        Args:
            task: 任务内容
            session_id: 会话ID

        Returns:
            测试结果
        """
        url = f"{self.base_url}/api/tasks/stream"
        payload = {
            "task": task,
            "session_id": session_id,
            "enable_heartbeat": True,
            "heartbeat_interval": 30
        }

        result = {
            "task": task,
            "events": [],
            "cancelled": False,
            "errors": []
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        result["errors"].append(f"HTTP错误: {response.status} - {error_text}")
                        return result

                    event_count = 0
                    async for line in response.content:
                        line_text = line.decode('utf-8').strip()
                        
                        if not line_text or line_text.startswith(':'):
                            continue
                        
                        if line_text.startswith('data: '):
                            try:
                                event_data = json.loads(line_text[6:])
                                event_type = event_data.get('event_type', 'unknown')
                                
                                result["events"].append(event_data)
                                event_count += 1
                                
                                print(f"[{event_type}] 事件 #{event_count}")
                                
                                if event_count >= 3:
                                    print("模拟客户端取消请求...")
                                    await response.close()
                                    result["cancelled"] = True
                                    break
                                
                            except json.JSONDecodeError as e:
                                result["errors"].append(f"JSON解析错误: {e}")

        except aiohttp.ClientError as e:
            if "CancelledError" in str(type(e).__name__):
                result["cancelled"] = True
            else:
                result["errors"].append(f"网络错误: {e}")
        except Exception as e:
            result["errors"].append(f"未知错误: {e}")

        return result

    def print_test_summary(self, result: dict):
        """打印测试摘要

        Args:
            result: 测试结果
        """
        print("\n" + "="*60)
        print(f"测试任务: {result['task']}")
        print(f"测试状态: {'✓ 成功' if result['success'] else '✗ 失败'}")
        print(f"事件总数: {len(result['events'])}")
        print(f"事件类型统计:")
        for event_type, count in result.get('event_counts', {}).items():
            print(f"  - {event_type}: {count}")
        
        if result['errors']:
            print(f"\n错误列表:")
            for error in result['errors']:
                print(f"  ✗ {error}")
        
        print("="*60 + "\n")


async def main():
    """主测试函数"""
    tester = StreamAPITester()
    
    print("开始流式响应API测试...\n")
    
    test_cases = [
        "你好",
        "查北京天气",
        "创建一个test.txt文件并写入hello world",
        "列出当前目录的文件"
    ]
    
    for task in test_cases:
        print(f"\n{'='*60}")
        print(f"测试任务: {task}")
        print('='*60)
        
        result = await tester.test_stream_task(task)
        tester.print_test_summary(result)
        
        if not result['success']:
            print("测试失败，跳过后续测试")
            break
    
    print("\n测试AbortController取消功能...")
    abort_result = await tester.test_abort_controller("创建一个test.txt文件并写入hello world")
    print(f"取消功能测试: {'✓ 成功' if abort_result['cancelled'] else '✗ 失败'}")
    
    print("\n所有测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
