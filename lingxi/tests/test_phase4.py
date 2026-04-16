#!/usr/bin/env python3
"""Phase 4 单元测试 - 防内存泄漏"""

import sys
import os
import tempfile
import gc
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import unittest

from lingxi.skills import SkillCache, SkillLoader


def create_test_skill_module(skill_dir, skill_id):
    """创建一个测试技能模块"""
    main_py = skill_dir / "main.py"
    main_py.write_text("""
test_data = [1, 2, 3, 4, 5]

def execute(params):
    return {"success": True, "result": f"Hello {params.get('name', 'World')}"}

def init():
    pass
""", encoding="utf-8")
    
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(f"""---
name: {skill_id}
description: Test skill
author: Test
version: 1.0.0
---
# Test Skill
""", encoding="utf-8")


class TestSkillCacheMemoryLeak(unittest.TestCase):
    """测试 SkillCache 的防内存泄漏功能"""

    def setUp(self):
        self.cache = SkillCache(ttl=60, max_size=5)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_lru_eviction(self):
        """测试 LRU 淘汰机制"""
        for i in range(10):
            skill_id = f"test_skill_{i}"
            skill_dir = self.temp_path / skill_id
            skill_dir.mkdir()
            main_py = skill_dir / "main.py"
            main_py.write_text("def execute(params): pass", encoding="utf-8")
            
            import types
            module = types.ModuleType(f"skill_{skill_id}")
            self.cache.set_module(skill_id, module, str(main_py))
        
        self.assertLessEqual(len(self.cache._module_cache), 5)

    def test_module_cleanup(self):
        """测试模块清理功能"""
        skill_id = "test_cleanup"
        skill_dir = self.temp_path / skill_id
        skill_dir.mkdir()
        create_test_skill_module(skill_dir, skill_id)
        
        import importlib.util
        spec = importlib.util.spec_from_file_location(f"skill_{skill_id}", str(skill_dir / "main.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        self.cache.set_module(skill_id, module, str(skill_dir / "main.py"))
        
        self.assertIn(skill_id, self.cache._module_cache)
        
        self.cache._remove_module(skill_id)
        
        self.assertNotIn(skill_id, self.cache._module_cache)

    def test_force_gc(self):
        """测试强制 GC 功能"""
        gc.collect()
        count_before = gc.collect()
        
        for i in range(1000):
            obj = {"data": list(range(100))}
        
        count_after = self.cache.force_gc()
        self.assertIsInstance(count_after, int)

    def test_hot_reload(self):
        """测试热重载功能"""
        skill_id = "test_hot_reload"
        skill_dir = self.temp_path / skill_id
        skill_dir.mkdir()
        create_test_skill_module(skill_dir, skill_id)
        
        import importlib.util
        spec = importlib.util.spec_from_file_location(f"skill_{skill_id}", str(skill_dir / "main.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        self.cache.set_module(skill_id, module, str(skill_dir / "main.py"))
        
        self.assertIn(skill_id, self.cache._module_cache)
        
        self.cache.hot_reload(skill_id)
        
        self.assertNotIn(skill_id, self.cache._module_cache)


class TestSkillLoaderUnload(unittest.TestCase):
    """测试 SkillLoader 的卸载功能"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        self.config = {
            "skills": {
                "builtin_skills_dir": str(self.temp_path),
                "user_skills_dir": str(self.temp_path)
            }
        }
        
        self.cache = SkillCache()
        self.loader = SkillLoader(self.config, cache=self.cache)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_unload_nonexistent_module(self):
        """测试卸载不存在的模块"""
        result = self.loader.unload_module("nonexistent_skill")
        self.assertTrue(result)

    def test_unload_module(self):
        """测试卸载模块"""
        skill_id = "test_unload"
        skill_dir = self.temp_path / skill_id
        skill_dir.mkdir()
        create_test_skill_module(skill_dir, skill_id)
        
        self.loader._load_local_skill_module(str(skill_dir), skill_id)
        
        self.assertIn(skill_id, self.loader.loaded_modules)
        
        result = self.loader.unload_module(skill_id)
        
        self.assertTrue(result)
        self.assertNotIn(skill_id, self.loader.loaded_modules)

    def test_unload_all(self):
        """测试卸载所有模块"""
        for i in range(3):
            skill_id = f"test_unload_{i}"
            skill_dir = self.temp_path / skill_id
            skill_dir.mkdir()
            create_test_skill_module(skill_dir, skill_id)
            self.loader._load_local_skill_module(str(skill_dir), skill_id)
        
        self.assertEqual(len(self.loader.loaded_modules), 3)
        
        count = self.loader.unload_all()
        
        self.assertEqual(count, 3)
        self.assertEqual(len(self.loader.loaded_modules), 0)


if __name__ == "__main__":
    unittest.main()
