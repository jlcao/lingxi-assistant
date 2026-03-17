#!/usr/bin/env python3
"""SOUL 注入系统手动测试脚本"""

import os
import sys
import tempfile
import shutil

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lingxi.core.soul import SoulInjector, SoulParser, SoulCache

# 测试用 SOUL.md 样例内容
SAMPLE_SOUL_CONTENT = """# SOUL.md - Who You Are

_You're not a chatbot. You're becoming someone._

## Core Identity

- Name: 灵犀
- Creature: AI Assistant
- Vibe: Warm, helpful, slightly witty
- Emoji: 🦄

## Core Truths

- Be genuinely helpful, not performatively helpful
- Have opinions and don't be afraid to share them
- Be resourceful before asking for help
- Earn trust through competence
- Remember you're a guest in the user's workspace

## Boundaries

- Private things stay private
- Ask before acting externally
- Never send half-baked replies
- You're not the user's voice

## Memory

- User prefers concise responses
- Working on Project X
- Favorite color is blue

## Context

This is the current context for the assistant.
It provides additional background information.
"""


def test_soul_parser():
    """测试 SoulParser"""
    print("=" * 60)
    print("测试 SoulParser")
    print("=" * 60)
    
    parser = SoulParser()
    result = parser.parse(SAMPLE_SOUL_CONTENT)
    
    # 测试身份解析
    assert result["identity"]["name"] == "灵犀", "身份名称解析失败"
    assert result["identity"]["creature"] == "AI Assistant", "生物类型解析失败"
    assert "Warm" in result["identity"]["vibe"], "氛围解析失败"
    assert result["identity"]["emoji"] == "🦄", "表情符号解析失败"
    print("✓ 身份解析测试通过")
    
    # 测试核心原则解析
    assert len(result["core_truths"]) == 5, f"核心原则数量错误：{len(result['core_truths'])}"
    assert "Be genuinely helpful, not performatively helpful" in result["core_truths"]
    print("✓ 核心原则解析测试通过")
    
    # 测试边界解析
    assert len(result["boundaries"]) == 4, f"边界数量错误：{len(result['boundaries'])}"
    assert "Private things stay private" in result["boundaries"]
    print("✓ 边界解析测试通过")
    
    # 测试记忆解析
    assert len(result["memory"]) == 3, f"记忆数量错误：{len(result['memory'])}"
    print("✓ 记忆解析测试通过")
    
    # 测试上下文解析
    assert "current context" in result["context"], "上下文解析失败"
    print("✓ 上下文解析测试通过")
    
    # 测试原始内容保留
    assert result["raw_content"] == SAMPLE_SOUL_CONTENT, "原始内容未保留"
    print("✓ 原始内容保留测试通过")
    
    print("\n✅ SoulParser 所有测试通过!\n")
    return True


def test_soul_cache():
    """测试 SoulCache"""
    print("=" * 60)
    print("测试 SoulCache")
    print("=" * 60)
    
    cache = SoulCache()
    test_path = "/tmp/test_workspace"
    test_content = "test content"
    test_data = {"key": "value"}
    
    # 测试设置和获取
    cache.set(test_path, test_content, test_data)
    result = cache.get(test_path)
    assert result == test_data, "缓存设置/获取失败"
    print("✓ 缓存设置/获取测试通过")
    
    # 测试获取不存在的缓存
    result = cache.get("/nonexistent/path")
    assert result is None, "获取不存在的缓存应返回 None"
    print("✓ 获取不存在缓存测试通过")
    
    # 测试缓存失效
    cache.invalidate(test_path)
    result = cache.get(test_path)
    assert result is None, "缓存失效失败"
    print("✓ 缓存失效测试通过")
    
    # 测试缓存有效性检查
    cache.set(test_path, test_content, test_data)
    assert cache.is_valid(test_path, test_content) is True, "有效性检查失败（相同内容）"
    assert cache.is_valid(test_path, "different") is False, "有效性检查失败（不同内容）"
    print("✓ 缓存有效性检查测试通过")
    
    # 测试哈希计算
    hash1 = cache._compute_hash("test")
    hash2 = cache._compute_hash("test")
    hash3 = cache._compute_hash("different")
    assert hash1 == hash2, "相同内容哈希应相同"
    assert hash1 != hash3, "不同内容哈希应不同"
    print("✓ 哈希计算测试通过")
    
    # 测试清空缓存
    cache.clear()
    assert cache.get(test_path) is None, "清空缓存失败"
    print("✓ 清空缓存测试通过")
    
    print("\n✅ SoulCache 所有测试通过!\n")
    return True


def test_soul_injector():
    """测试 SoulInjector"""
    print("=" * 60)
    print("测试 SoulInjector")
    print("=" * 60)
    
    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    soul_path = os.path.join(temp_dir, "SOUL.md")
    
    try:
        # 创建 SOUL.md 文件
        with open(soul_path, 'w', encoding='utf-8') as f:
            f.write(SAMPLE_SOUL_CONTENT)
        
        injector = SoulInjector(temp_dir)
        
        # 测试加载
        result = injector.load()
        assert result is True, "加载 SOUL.md 失败"
        assert injector.soul_content is not None, "内容未加载"
        assert injector.soul_data is not None, "数据未解析"
        print("✓ 加载 SOUL.md 测试通过")
        
        # 测试解析
        data = injector.parse()
        assert data["identity"]["name"] == "灵犀", "解析失败"
        print("✓ 解析 SOUL.md 测试通过")
        
        # 测试构建系统提示词
        base_prompt = "你是灵犀智能助手。"
        system_prompt = injector.build_system_prompt(base_prompt)
        assert base_prompt in system_prompt, "基础提示词未包含"
        assert "---" in system_prompt, "分隔符未包含"
        assert "# 你的身份 (SOUL.md)" in system_prompt, "身份标题未包含"
        assert "## 核心身份" in system_prompt, "核心身份部分未包含"
        assert "## 核心原则" in system_prompt, "核心原则部分未包含"
        assert "## 边界" in system_prompt, "边界部分未包含"
        assert "Name: 灵犀" in system_prompt, "身份信息未包含"
        print("✓ 构建系统提示词测试通过")
        
        # 测试注入消息（有系统消息）
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        injected = injector.inject(messages)
        assert len(injected) == len(messages), "消息数量改变"
        assert injected[0]["role"] == "system", "第一条消息不是系统消息"
        assert "You are a helpful assistant." in injected[0]["content"], "原系统消息丢失"
        assert "# 你的身份 (SOUL.md)" in injected[0]["content"], "SOUL 内容未注入"
        print("✓ 注入消息（有系统消息）测试通过")
        
        # 测试注入消息（无系统消息）
        messages_no_system = [
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        injected_no_system = injector.inject(messages_no_system)
        assert len(injected_no_system) == len(messages_no_system) + 1, "应添加系统消息"
        assert injected_no_system[0]["role"] == "system", "第一条消息不是系统消息"
        print("✓ 注入消息（无系统消息）测试通过")
        
        # 测试获取身份摘要
        summary = injector.get_identity_summary()
        assert "Name: 灵犀" in summary, "身份摘要不包含名称"
        assert "Creature: AI Assistant" in summary, "身份摘要不包含生物类型"
        print("✓ 获取身份摘要测试通过")
        
        # 测试重新加载
        with open(soul_path, 'w', encoding='utf-8') as f:
            f.write("# Modified SOUL\n\n## Core Identity\n\n- Name: Modified")
        
        result = injector.reload()
        assert result is True, "重新加载失败"
        assert injector.soul_data["identity"]["name"] == "Modified", "重新加载后数据未更新"
        print("✓ 重新加载测试通过")
        
        # 测试检查 SOUL.md 是否存在
        assert injector.has_soul() is True, "has_soul() 应返回 True"
        injector2 = SoulInjector("/nonexistent/path")
        assert injector2.has_soul() is False, "has_soul() 对不存在路径应返回 False"
        print("✓ 检查 SOUL.md 存在性测试通过")
        
        # 测试获取缓存状态
        status = injector.get_cache_status()
        assert "cached" in status, "缓存状态不包含 cached 字段"
        print("✓ 获取缓存状态测试通过")
        
        print("\n✅ SoulInjector 所有测试通过!\n")
        return True
        
    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_integration():
    """集成测试"""
    print("=" * 60)
    print("集成测试 - 完整工作流程")
    print("=" * 60)
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 创建 SOUL.md
        soul_path = os.path.join(temp_dir, "SOUL.md")
        with open(soul_path, 'w', encoding='utf-8') as f:
            f.write(SAMPLE_SOUL_CONTENT)
        
        # 创建注入器
        injector = SoulInjector(temp_dir)
        
        # 完整工作流程
        assert injector.load() is True, "加载失败"
        data = injector.parse()
        assert data["identity"]["name"] == "灵犀", "解析失败"
        
        system_prompt = injector.build_system_prompt("Base prompt")
        assert "Base prompt" in system_prompt, "基础提示词未包含"
        assert "灵犀" in system_prompt, "SOUL 内容未包含"
        
        messages = [{"role": "user", "content": "Hello"}]
        injected = injector.inject(messages)
        assert len(injected) == 2, "消息数量错误"
        assert injected[0]["role"] == "system", "系统消息未添加"
        
        summary = injector.get_identity_summary()
        assert "灵犀" in summary, "身份摘要错误"
        
        # 修改并重新加载
        with open(soul_path, 'w', encoding='utf-8') as f:
            f.write("# New SOUL\n\n## Core Identity\n\n- Name: New")
        
        assert injector.reload() is True, "重新加载失败"
        assert injector.parse()["identity"]["name"] == "New", "重新加载后数据未更新"
        
        print("✓ 完整工作流程测试通过")
        print("\n✅ 集成测试通过!\n")
        return True
        
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_with_workspace_soul():
    """使用真实工作区的 SOUL.md 测试"""
    print("=" * 60)
    print("使用真实工作区 SOUL.md 测试")
    print("=" * 60)
    
    workspace_path = "/home/admin/.openclaw/workspace"
    soul_path = os.path.join(workspace_path, "SOUL.md")
    
    if not os.path.exists(soul_path):
        print(f"⚠️  工作区 SOUL.md 不存在：{soul_path}")
        print("跳过此测试\n")
        return True
    
    injector = SoulInjector(workspace_path)
    
    # 加载
    result = injector.load()
    if not result:
        print("⚠️  加载 SOUL.md 失败")
        print("跳过此测试\n")
        return True
    
    print(f"✓ 成功加载工作区 SOUL.md")
    
    # 解析
    data = injector.parse()
    print(f"✓ 解析成功，身份：{data.get('identity', {}).get('name', 'Unknown')}")
    
    # 构建系统提示词
    system_prompt = injector.build_system_prompt("你是灵犀智能助手。")
    print(f"✓ 系统提示词长度：{len(system_prompt)} 字符")
    
    # 获取身份摘要
    summary = injector.get_identity_summary()
    print(f"✓ 身份摘要：{summary}")
    
    # 获取缓存状态
    status = injector.get_cache_status()
    print(f"✓ 缓存状态：{'已缓存' if status.get('cached') else '未缓存'}")
    
    print("\n✅ 工作区 SOUL.md 测试通过!\n")
    return True


def main():
    """运行所有测试"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "SOUL 注入系统测试" + " " * 16 + "║")
    print("╚" + "=" * 58 + "╝")
    print("\n")
    
    results = []
    
    try:
        results.append(("SoulParser", test_soul_parser()))
    except Exception as e:
        print(f"\n❌ SoulParser 测试失败：{e}\n")
        results.append(("SoulParser", False))
    
    try:
        results.append(("SoulCache", test_soul_cache()))
    except Exception as e:
        print(f"\n❌ SoulCache 测试失败：{e}\n")
        results.append(("SoulCache", False))
    
    try:
        results.append(("SoulInjector", test_soul_injector()))
    except Exception as e:
        print(f"\n❌ SoulInjector 测试失败：{e}\n")
        results.append(("SoulInjector", False))
    
    try:
        results.append(("Integration", test_integration()))
    except Exception as e:
        print(f"\n❌ 集成测试失败：{e}\n")
        results.append(("Integration", False))
    
    try:
        results.append(("Workspace", test_with_workspace_soul()))
    except Exception as e:
        print(f"\n❌ 工作区测试失败：{e}\n")
        results.append(("Workspace", False))
    
    # 打印总结
    print("=" * 60)
    print("测试总结")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")
    
    print()
    print(f"总计：{passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过!\n")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
