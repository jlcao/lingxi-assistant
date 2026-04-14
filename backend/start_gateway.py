#!/usr/bin/env python3
"""
启动 Gateway API 服务器（不依赖 uv）

这个脚本在没有 uv 的生产环境中也能使用，
直接使用 Python 和已安装的依赖来启动 Gateway API。
"""

import os
import sys


def start_gateway():
    """启动 Gateway API 服务器"""
    # 获取当前目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 设置 PYTHONPATH 为当前目录
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    print(f"启动 Gateway API 服务器...")
    print(f"当前目录: {current_dir}")
    print(f"PYTHONPATH: {sys.path[:3]}")
    
    try:
        # 尝试直接导入并启动 uvicorn
        import uvicorn
        
        print("使用 uvicorn 启动 Gateway API...")
        uvicorn.run(
            "app.gateway.app:app",
            host="0.0.0.0",
            port=8001,
            log_level="info"
        )
        
    except ImportError as e:
        print(f"错误: 无法导入 uvicorn - {e}")
        print("\n请确保已安装所有必要的依赖:")
        print("  pip install fastapi uvicorn httpx python-multipart sse-starlette")
        sys.exit(1)
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n服务器已停止")
        sys.exit(0)


if __name__ == "__main__":
    start_gateway()
