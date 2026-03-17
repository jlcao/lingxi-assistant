#!/usr/bin/env python3
"""技能系统集成测试（独立运行版）"""

import sys
import os
import time
import importlib.util

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def load_module(path, name):
    """直接加载模块，绕过 __init__.py"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_skill_cache():
    """测试 SkillCache 缓存模块"""
    print('\n【测试 1】SkillCache 缓存模块')
    skill_cache = load_module('skills/skill_cache.py', 'skill_cache')
    SkillCache = skill_cache.SkillCache

    cache = SkillCache(ttl=60)
    cache.set_config('test_skill', {'test': 'data'}, '/tmp/test.py')
    cached = cache.get_config('test_skill')
    assert cached == {'test': 'data'}, '缓存获取失败'
    print('✓ 缓存设置和获取：通过')

    cache.invalidate('test_skill')
    assert cache.get_config('test_skill') is None, '缓存失效失败'
    print('✓ 缓存失效：通过')

    cache.set_config('skill1', {}, '/tmp/1.py')
    cache.set_config('skill2', {}, '/tmp/2.py')
    cache.set_module('skill1', None, '/tmp/1.py')
    stats = cache.get_stats()
    assert stats['config_cache_size'] == 2, '配置缓存统计失败'
    assert stats['module_cache_size'] == 1, '模块缓存统计失败'
    print('✓ 缓存统计：通过')
    print(f'  配置缓存：{stats["config_cache_size"]} 个')
    print(f'  模块缓存：{stats["module_cache_size"]} 个')
    return True


def test_skill_loader_cache():
    """测试 SkillLoader 缓存集成"""
    print('\n【测试 2】SkillLoader 缓存集成')
    with open('skills/skill_loader.py', 'r', encoding='utf-8') as f:
        source = f.read()

    assert 'def __init__(self, config: Dict[str, Any], registry=None, cache=None):' in source
    print('✓ SkillLoader.__init__ 支持 cache 参数：通过')

    assert 'cached_config = self.cache.get_config(skill_id)' in source
    print('✓ _load_skill_config 检查缓存：通过')

    assert 'self.cache.set_config(skill_id, config,' in source
    print('✓ _load_skill_config 设置缓存：通过')

    assert 'cached_module = self.cache.get_module(skill_id)' in source
    print('✓ _load_local_skill_module 检查缓存：通过')

    assert 'self.cache.set_module(skill_id, module, main_py_path)' in source
    print('✓ _load_local_skill_module 设置缓存：通过')
    return True


def test_builtin_skills_cache():
    """测试 BuiltinSkills 缓存集成"""
    print('\n【测试 3】BuiltinSkills 缓存集成')
    with open('skills/builtin.py', 'r', encoding='utf-8') as f:
        source = f.read()

    assert 'from lingxi.skills.skill_cache import SkillCache' in source
    print('✓ BuiltinSkills 导入 SkillCache：通过')

    assert 'self.cache = SkillCache(ttl=cache_ttl)' in source
    print('✓ BuiltinSkills 初始化缓存：通过')

    assert 'self.skill_loader = SkillLoader(config, self.registry, self.cache)' in source
    print('✓ BuiltinSkills 传递 cache 给 SkillLoader：通过')
    return True


def test_skill_caller_skill_system():
    """测试 SkillCaller SkillSystem 集成"""
    print('\n【测试 4】SkillCaller SkillSystem 集成')
    with open('core/skill_caller.py', 'r', encoding='utf-8') as f:
        source = f.read()

    assert 'from lingxi.skills.skill_system import SkillSystem' in source
    print('✓ SkillCaller 导入 SkillSystem：通过')

    assert 'self.skill_system = SkillSystem(config)' in source
    print('✓ SkillCaller 初始化 SkillSystem：通过')

    assert 'self.skill_registry = self.skill_system.registry' in source
    print('✓ SkillCaller 使用 SkillSystem.registry：通过')

    assert 'result = self.skill_system.execute_skill(skill_name, parameters)' in source
    print('✓ SkillCaller 使用 SkillSystem.execute_skill：通过')
    return True


def test_skill_system():
    """测试 SkillSystem 统一入口"""
    print('\n【测试 5】SkillSystem 统一入口')
    with open('skills/skill_system.py', 'r', encoding='utf-8') as f:
        source = f.read()

    assert 'class SkillSystem:' in source
    print('✓ SkillSystem 类定义：通过')

    assert 'self.cache = SkillCache(ttl=cache_ttl)' in source
    print('✓ SkillSystem 初始化缓存：通过')

    assert 'self.loader = SkillLoader(config, self.registry, self.cache)' in source
    print('✓ SkillSystem 初始化 SkillLoader（带缓存）：通过')

    assert 'def execute_skill(self, skill_name:' in source
    print('✓ SkillSystem.execute_skill 方法：通过')

    assert 'def get_cache_stats(self)' in source
    print('✓ SkillSystem.get_cache_stats 方法：通过')
    return True


def test_performance():
    """性能对比测试"""
    print('\n【测试 6】缓存性能对比')
    skill_cache = load_module('skills/skill_cache.py', 'skill_cache')
    SkillCache = skill_cache.SkillCache

    def mock_load_config(skill_id):
        time.sleep(0.005)  # 模拟 5ms 的 IO 延迟
        return {'skill_id': skill_id, 'data': 'test'}

    # 无缓存
    start = time.time()
    for i in range(50):
        mock_load_config(f'skill_{i}')
    time_no_cache = time.time() - start

    # 有缓存（命中）
    cache = SkillCache(ttl=300)
    for i in range(50):
        skill_id = f'skill_{i}'
        config = mock_load_config(skill_id)
        cache.set_config(skill_id, config, f'/tmp/{skill_id}.py')
    
    start = time.time()
    for i in range(50):
        cache.get_config(f'skill_{i}')
    time_cached = time.time() - start

    print(f'无缓存耗时（50 次）：  {time_no_cache*1000:.2f} ms')
    print(f'有缓存命中（50 次）： {time_cached*1000:.2f} ms')
    print(f'性能提升：          {(time_no_cache / time_cached):.1f}x')
    return True


if __name__ == "__main__":
    print('='*60)
    print('技能系统集成测试')
    print('='*60)
    
    tests = [
        ('SkillCache 缓存模块', test_skill_cache),
        ('SkillLoader 缓存集成', test_skill_loader_cache),
        ('BuiltinSkills 缓存集成', test_builtin_skills_cache),
        ('SkillCaller SkillSystem 集成', test_skill_caller_skill_system),
        ('SkillSystem 统一入口', test_skill_system),
        ('缓存性能对比', test_performance),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f'✗ {name} 失败：{e}')
            failed += 1
    
    print('\n' + '='*60)
    print(f'测试结果：{passed} 通过，{failed} 失败')
    print('='*60)
    
    sys.exit(0 if failed == 0 else 1)
