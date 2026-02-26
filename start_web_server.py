#!/usr/bin/env python3
"""
灵犀智能助手 - WebSocket服务器启动脚本
"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from lingxi.web.fastapi_server import run_server
from lingxi.utils.config import get_config


def main():
    """启动WebSocket服务器"""
    print("=" * 60)
    print("灵犀智能助手 - WebSocket服务器")
    print("=" * 60)
    print()

    config = get_config()
    web_config = config.get('web', {})
    host = web_config.get('host', 'localhost')
    port = web_config.get('port', 5000)

    print(f"服务器地址: http://{host}:{port}")
    print(f"WebSocket端点: ws://{host}:{port}/ws")
    print(f"Web界面: http://{host}:{port}/static/index.html")
    print(f"API文档: http://{host}:{port}/docs")
    print()
    print("按 Ctrl+C 停止服务器")
    print("=" * 60)
    print()

    try:
        run_server(config)
    except KeyboardInterrupt:
        print("\n\n服务器已停止")
    except Exception as e:
        print(f"\n\n服务器启动失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
