"""
测试流式 API 修复
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_stream_task():
    """测试流式任务执行"""
    print("=" * 60)
    print("测试流式任务执行")
    print("=" * 60)
    
    # 创建会话
    print("\n1. 创建会话...")
    session_response = requests.post(f"{BASE_URL}/api/sessions", json={
        "user_name": "test_user"
    })
    
    if session_response.status_code != 200:
        print(f"❌ 创建会话失败：{session_response.text}")
        return
    
    session_data = session_response.json()
    session_id = session_data.get("session_id")
    print(f"✅ 会话创建成功：{session_id}")
    
    # 测试流式任务
    print(f"\n2. 执行流式任务...")
    stream_url = f"{BASE_URL}/api/tasks/stream"
    
    start_time = time.time()
    
    try:
        response = requests.post(
            stream_url,
            json={
                "session_id": session_id,
                "task": "翻译：Hello, World! 到中文",
                "model_override": None
            },
            stream=True,
            headers={"Accept": "text/event-stream"}
        )
        
        print(f"✅ 流式请求已建立，状态码：{response.status_code}")
        print(f"⏳ 等待响应...")
        
        event_count = 0
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    event_count += 1
                    data = json.loads(line_str[6:])
                    event_type = data.get('type', 'unknown')
                    print(f"   [{event_count}] 事件类型：{event_type}")
                    
                    # 如果是错误事件，打印详细信息
                    if event_type == 'error':
                        print(f"   ❌ 错误：{data.get('message', 'Unknown error')}")
                    
                    # 如果是结束事件，停止
                    if event_type == 'stream_end':
                        print(f"   ✅ 流式传输完成")
                        break
        
        elapsed_time = time.time() - start_time
        print(f"\n✅ 测试完成！总耗时：{elapsed_time:.2f}秒，收到 {event_count} 个事件")
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"\n❌ 测试失败：{str(e)}")
        print(f"   耗时：{elapsed_time:.2f}秒")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        test_stream_task()
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试异常：{str(e)}")
        import traceback
        traceback.print_exc()
