"""异步改造测试脚本

测试 WebSocket 在高并发下是否阻塞
"""

import asyncio
import aiohttp
import time
import json
from typing import List


class AsyncWebSocketTester:
    """异步 WebSocket 测试器"""

    def __init__(self, base_url: str = "ws://localhost:5000"):
        self.base_url = base_url
        self.results: List[dict] = []

    async def test_single_connection(self, connection_id: int, message: str) -> dict:
        """测试单个连接
        
        Args:
            connection_id: 连接 ID
            message: 测试消息
            
        Returns:
            测试结果
        """
        result = {
            "connection_id": connection_id,
            "message": message,
            "start_time": time.time(),
            "end_time": 0,
            "latency": 0,
            "chunks_received": 0,
            "success": False,
            "error": None
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(f"{self.base_url}/ws") as ws:
                    # 发送消息
                    await ws.send_json({
                        "type": "stream_chat",
                        "content": message,
                        "session_id": f"test_session_{connection_id}"
                    })
                    
                    # 接收响应
                    chunks = []
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            data = json.loads(msg.data)
                            chunks.append(data)
                            result["chunks_received"] += 1
                            
                            if data.get("type") in ["task_end", "stream_end", "error"]:
                                break
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            break
                    
                    result["end_time"] = time.time()
                    result["latency"] = result["end_time"] - result["start_time"]
                    result["success"] = True
                    result["chunks"] = chunks
                    
        except Exception as e:
            result["error"] = str(e)
            result["end_time"] = time.time()
            result["latency"] = result["end_time"] - result["start_time"]
        
        return result

    async def test_concurrent_connections(self, num_connections: int = 10) -> dict:
        """测试并发连接
        
        Args:
            num_connections: 并发连接数
            
        Returns:
            测试统计
        """
        print(f"\n开始测试 {num_connections} 个并发连接...")
        
        tasks = []
        for i in range(num_connections):
            task = self.test_single_connection(
                i,
                f"测试消息 {i} - {time.strftime('%H:%M:%S')}"
            )
            tasks.append(task)
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # 统计结果
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        failed = len(results) - successful
        avg_latency = sum(r["latency"] for r in results if isinstance(r, dict)) / len(results) if results else 0
        max_latency = max(r["latency"] for r in results if isinstance(r, dict)) if results else 0
        min_latency = min(r["latency"] for r in results if isinstance(r, dict)) if results else 0
        total_chunks = sum(r.get("chunks_received", 0) for r in results if isinstance(r, dict))
        
        stats = {
            "total_connections": num_connections,
            "successful": successful,
            "failed": failed,
            "total_time": end_time - start_time,
            "avg_latency": avg_latency,
            "max_latency": max_latency,
            "min_latency": min_latency,
            "total_chunks": total_chunks,
            "throughput": num_connections / (end_time - start_time) if (end_time - start_time) > 0 else 0
        }
        
        print(f"\n测试完成！")
        print(f"总连接数：{num_connections}")
        print(f"成功：{successful}, 失败：{failed}")
        print(f"总耗时：{end_time - start_time:.2f}秒")
        print(f"平均延迟：{avg_latency:.2f}秒")
        print(f"最大延迟：{max_latency:.2f}秒")
        print(f"最小延迟：{min_latency:.2f}秒")
        print(f"吞吐量：{stats['throughput']:.2f} 连接/秒")
        print(f"总消息块数：{total_chunks}")
        
        return stats

    async def test_blocking(self, num_requests: int = 5) -> bool:
        """测试是否阻塞
        
        如果 WebSocket 不阻塞，多个请求应该并行处理
        如果阻塞，请求会串行处理，总时间会显著增加
        
        Args:
            num_requests: 请求数
            
        Returns:
            是否阻塞（True=阻塞，False=不阻塞）
        """
        print(f"\n开始阻塞测试（{num_requests} 个请求）...")
        
        # 发送多个请求，测量总时间
        start_time = time.time()
        
        tasks = []
        for i in range(num_requests):
            task = self.test_single_connection(
                i,
                f"阻塞测试消息 {i}"
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        total_time = end_time - start_time
        avg_latency = sum(r["latency"] for r in results) / len(results)
        
        # 如果总时间接近平均延迟 * 请求数，说明是串行处理（阻塞）
        # 如果总时间接近平均延迟，说明是并行处理（不阻塞）
        expected_serial_time = avg_latency * num_requests
        expected_parallel_time = avg_latency
        
        is_blocking = total_time > (expected_serial_time * 0.8)
        
        print(f"\n阻塞测试结果：")
        print(f"总耗时：{total_time:.2f}秒")
        print(f"平均延迟：{avg_latency:.2f}秒")
        print(f"预期串行时间：{expected_serial_time:.2f}秒")
        print(f"预期并行时间：{expected_parallel_time:.2f}秒")
        print(f"结论：{'阻塞 ❌' if is_blocking else '不阻塞 ✅'}")
        
        return is_blocking


async def main():
    """主函数"""
    print("=" * 60)
    print("灵犀异步改造测试")
    print("=" * 60)
    
    tester = AsyncWebSocketTester()
    
    # 测试 1：少量并发连接
    print("\n[测试 1] 少量并发连接测试")
    await tester.test_concurrent_connections(5)
    
    # 测试 2：阻塞测试
    print("\n[测试 2] 阻塞测试")
    is_blocking = await tester.test_blocking(5)
    
    # 测试 3：大量并发连接（可选）
    print("\n[测试 3] 大量并发连接测试")
    await tester.test_concurrent_connections(20)
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    
    if not is_blocking:
        print("\n✅ 异步改造成功！WebSocket 不阻塞！")
    else:
        print("\n❌ 检测到阻塞，需要进一步优化！")


if __name__ == "__main__":
    asyncio.run(main())
