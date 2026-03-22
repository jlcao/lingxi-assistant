import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, '.')

from lingxi.utils.config import load_config

print("测试配置加载...")
try:
    config = load_config()
    print("✓ 配置加载成功")
    print(f"系统名称: {config.get('system', {}).get('name')}")
    print(f"LLM 提供商: {config.get('llm', {}).get('provider')}")
    print(f"默认引擎: {config.get('engine', {}).get('default')}")
except Exception as e:
    print(f"✗ 配置加载失败: {e}")
    import traceback
    traceback.print_exc()