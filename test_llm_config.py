#!/usr/bin/env python3
"""测试 LLM 配置是否正确加载"""

import os
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("=" * 60)
print("测试 LLM 配置")
print("=" * 60)

# 检查环境变量
api_key = os.getenv('DASHSCOPE_API_KEY')
print(f"\n1. 环境变量 DASHSCOPE_API_KEY: {'✅ 已设置' if api_key else '❌ 未设置'}")
if api_key:
    print(f"   值：{api_key[:20]}...")

# 加载配置
from lingxi.utils.config import get_config
config = get_config()
print(f"\n2. 配置文件加载：✅ 成功")

llm_config = config.get('llm', {})
print(f"3. LLM 配置:")
print(f"   - provider: {llm_config.get('provider')}")
print(f"   - model: {llm_config.get('model')}")
print(f"   - api_key (from config): {'已设置' if llm_config.get('api_key') else '未设置'}")

# 初始化 LLM 客户端
try:
    from lingxi.core.llm.llm_client import LLMClient
    llm_client = LLMClient(llm_config)
    print(f"\n4. LLM 客户端初始化：✅ 成功")
    print(f"   - api_key (from env): {'已设置' if llm_client.api_key else '未设置'}")
    print(f"   - model: {llm_client.model}")
    print(f"   - base_url: {llm_client.base_url}")
except Exception as e:
    print(f"\n4. LLM 客户端初始化：❌ 失败")
    print(f"   错误：{e}")

# 初始化分类器
try:
    from lingxi.core.classification import TaskClassifier
    classifier = TaskClassifier(config)
    print(f"\n5. 任务分类器初始化：✅ 成功")
    
    # 注入 LLM 客户端
    classifier.set_llm_client(llm_client)
    print(f"6. LLM 客户端注入：✅ 成功")
    
    # 测试分类
    test_task = "1+1 等于几？"
    result = classifier.classify(test_task)
    print(f"\n7. 分类测试：✅ 成功")
    print(f"   任务：{test_task}")
    print(f"   级别：{result.get('level')}")
    print(f"   置信度：{result.get('confidence')}")
    
except Exception as e:
    print(f"\n5-7. 分类器测试：❌ 失败")
    print(f"   错误：{e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
