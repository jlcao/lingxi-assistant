#!/usr/bin/env python3
"""
异步改造验证脚本

检查所有异步组件是否正确创建和导入
"""

import sys
import asyncio
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def check_import(module_path: str, class_name: str) -> bool:
    """检查模块和类是否可以导入"""
    try:
        parts = module_path.split('.')
        module = __import__(module_path, fromlist=[class_name])
        cls = getattr(module, class_name)
        print(f"✅ {module_path}.{class_name} - 导入成功")
        return True
    except Exception as e:
        print(f"❌ {module_path}.{class_name} - 导入失败：{e}")
        return False


def check_file_exists(file_path: str) -> bool:
    """检查文件是否存在"""
    path = Path(file_path)
    if path.exists():
        print(f"✅ {file_path} - 文件存在")
        return True
    else:
        print(f"❌ {file_path} - 文件不存在")
        return False


async def test_async_llm_client():
    """测试异步 LLM 客户端"""
    try:
        from lingxi.core.async_llm_client import AsyncLLMClient
        from lingxi.utils.config import load_config
        
        config = load_config()
        client = AsyncLLMClient(config)
        
        # 检查是否是异步
        import inspect
        is_async = inspect.iscoroutinefunction(client.stream_chat)
        
        if is_async:
            print("✅ AsyncLLMClient.stream_chat - 异步方法 ✓")
            return True
        else:
            print("❌ AsyncLLMClient.stream_chat - 不是异步方法 ✗")
            return False
    except Exception as e:
        print(f"❌ AsyncLLMClient 测试失败：{e}")
        return False


async def test_async_engine():
    """测试异步引擎"""
    try:
        from lingxi.core.engine.async_plan_react import AsyncPlanReActEngine
        from lingxi.core.skill_caller import SkillCaller
        from lingxi.core.session import SessionManager
        from lingxi.utils.config import load_config
        import inspect
        
        config = load_config()
        skill_caller = SkillCaller(config)
        session_manager = SessionManager(config)
        
        engine = AsyncPlanReActEngine(config, skill_caller, session_manager)
        
        # 检查 process 方法是否是异步
        is_async = inspect.iscoroutinefunction(engine.process)
        
        if is_async:
            print("✅ AsyncPlanReActEngine.process - 异步方法 ✓")
            return True
        else:
            print("❌ AsyncPlanReActEngine.process - 不是异步方法 ✗")
            return False
    except Exception as e:
        print(f"❌ AsyncEngine 测试失败：{e}")
        return False


async def test_async_assistant():
    """测试异步助手"""
    try:
        from lingxi.core.async_main import AsyncLingxiAssistant
        from lingxi.utils.config import load_config
        import inspect
        
        config = load_config()
        assistant = AsyncLingxiAssistant(config)
        
        # 检查 process_input 方法是否是异步
        is_async = inspect.iscoroutinefunction(assistant.process_input)
        
        if is_async:
            print("✅ AsyncLingxiAssistant.process_input - 异步方法 ✓")
            return True
        else:
            print("❌ AsyncLingxiAssistant.process_input - 不是异步方法 ✗")
            return False
    except Exception as e:
        print(f"❌ AsyncAssistant 测试失败：{e}")
        return False


def test_skill_caller_async():
    """测试技能调用器异步方法"""
    try:
        from lingxi.core.skill_caller import SkillCaller
        from lingxi.utils.config import load_config
        import inspect
        
        config = load_config()
        caller = SkillCaller(config)
        
        # 检查 call_async 方法是否是异步
        is_async = inspect.iscoroutinefunction(caller.call_async)
        
        if is_async:
            print("✅ SkillCaller.call_async - 异步方法 ✓")
            return True
        else:
            print("❌ SkillCaller.call_async - 不是异步方法 ✗")
            return False
    except Exception as e:
        print(f"❌ SkillCaller 测试失败：{e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("灵犀智能助手 - 异步改造验证")
    print("=" * 60)
    print()
    
    results = []
    
    # 1. 检查文件是否存在
    print("[1] 检查新增文件...")
    files_to_check = [
        "lingxi/core/async_llm_client.py",
        "lingxi/core/async_main.py",
        "lingxi/core/engine/async_react_core.py",
        "lingxi/core/engine/async_plan_react.py",
        "test/test_async_websocket.py",
        "start_async_server.py",
        "docs/异步改造说明.md"
    ]
    
    for file_path in files_to_check:
        results.append(check_file_exists(file_path))
    
    print()
    
    # 2. 检查导入
    print("[2] 检查模块导入...")
    imports_to_check = [
        ("lingxi.core.async_llm_client", "AsyncLLMClient"),
        ("lingxi.core.async_main", "AsyncLingxiAssistant"),
        ("lingxi.core.engine.async_react_core", "AsyncReActCore"),
        ("lingxi.core.engine.async_plan_react", "AsyncPlanReActEngine"),
    ]
    
    for module_path, class_name in imports_to_check:
        results.append(check_import(module_path, class_name))
    
    print()
    
    # 3. 异步功能测试
    print("[3] 异步功能测试...")
    
    async def run_async_tests():
        results.append(await test_async_llm_client())
        results.append(await test_async_engine())
        results.append(await test_async_assistant())
        results.append(test_skill_caller_async())
    
    asyncio.run(run_async_tests())
    
    print()
    
    # 4. 统计结果
    print("=" * 60)
    total = len(results)
    passed = sum(results)
    failed = total - passed
    
    print(f"测试结果：{passed}/{total} 通过")
    print(f"通过率：{passed/total*100:.1f}%")
    
    if failed == 0:
        print("\n✅ 所有测试通过！异步改造成功！")
        print("\n🚀 可以启动服务器进行测试：")
        print("   python start_async_server.py --reload")
    else:
        print(f"\n❌ {failed} 个测试失败，请检查错误信息！")
    
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
