#!/usr/bin/env python3
"""
灵犀智能助手 - WebSocket服务器启动脚本
"""
import sys
import os
import argparse
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from lingxi.web.fastapi_server import run_server
from lingxi.utils.config import get_config
from lingxi.web.websocket import WebSocketManager
from lingxi.web.state import set_websocket_manager, set_assistant
from lingxi.core.assistant.async_main import AsyncLingxiAssistant
from lingxi.core.event.websocket_subscriber import WebSocketSubscriber


def main():
    """启动WebSocket服务器"""
    parser = argparse.ArgumentParser(description="灵犀智能助手 - WebSocket服务器")
    parser.add_argument("--reload", action="store_true", help="启用自动重载（开发模式）")
    args = parser.parse_args()

    print("=" * 60)
    print("灵犀智能助手 - WebSocket服务器")
    print("=" * 60)
    print()

    config = get_config()
    web_config = config.get('web', {})
    host = web_config.get('host', 'localhost')
    port = web_config.get('port', 5000)

    # 如果命令行参数指定了reload，覆盖配置文件中的设置
    if args.reload:
        web_config['debug'] = True
        print("开发模式已启用：文件修改后会自动重载")
        print()

    print(f"服务器地址: http://{host}:{port}")
    print(f"WebSocket 端点：ws://{host}:{port}/ws")
    print(f"Web 界面：http://{host}:{port}/static/index.html")
    print(f"API 文档：http://{host}:{port}/docs")
    print()
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)
    print()

    # 初始化助手和 WebSocket 管理器
    try:
        assistant = AsyncLingxiAssistant(config)
        set_assistant(assistant)
        
        # 初始化 WebSocket 管理器和订阅者
        websocket_manager = WebSocketManager(assistant)
        set_websocket_manager(websocket_manager)
        
        # 初始化 WebSocket 事件订阅者
        websocket_subscriber = WebSocketSubscriber(websocket_manager)
        
        print("异步助手已初始化")
        print("WebSocket 事件推送：已启用（全异步）")
        print()
    except Exception as e:
        print(f"初始化失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    try:
        run_server(config)
    except KeyboardInterrupt:
        print("\n\n服务器已停止")
    except Exception as e:
        print(f"\n\n服务器启动失败：{e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
