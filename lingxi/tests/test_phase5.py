#!/usr/bin/env python3
"""Phase 5 单元测试 - 技能级 venv"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import unittest

from lingxi.skills import SkillLoader


class TestSkillVenv(unittest.TestCase):
    """测试技能级 venv 功能"""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        
        self.config = {
            "skills": {
                "builtin_skills_dir": str(self.temp_path),
                "user_skills_dir": str(self.temp_path)
            }
        }
        
        self.loader = SkillLoader(self.config)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_venv_in_directory(self):
        """测试在指定目录创建 venv"""
        skill_dir = self.temp_path / "test_skill"
        skill_dir.mkdir()
        
        venv_dir = skill_dir / ".venv"
        
        result = self.loader.create_venv(str(skill_dir), upgrade_pip=False)
        self.assertTrue(result)
        self.assertTrue(venv_dir.exists())
        self.assertTrue(venv_dir.is_dir())

    def test_get_pip_path(self):
        """测试获取 pip 路径"""
        skill_dir = self.temp_path / "test_skill_pip"
        skill_dir.mkdir()
        
        self.loader.create_venv(str(skill_dir), upgrade_pip=False)
        
        venv_dir = os.path.join(str(skill_dir), ".venv")
        pip_path = self.loader._get_pip_path(venv_dir)
        self.assertIsNotNone(pip_path)

    def test_get_python_path(self):
        """测试获取 Python 路径"""
        skill_dir = self.temp_path / "test_skill_python"
        skill_dir.mkdir()
        
        self.loader.create_venv(str(skill_dir), upgrade_pip=False)
        
        venv_dir = os.path.join(str(skill_dir), ".venv")
        python_path = self.loader._get_python_path(venv_dir)
        self.assertIsNotNone(python_path)
        self.assertTrue(os.path.exists(python_path))

    def test_has_virtual_env(self):
        """测试检测 venv"""
        skill_dir = self.temp_path / "test_skill_check"
        skill_dir.mkdir()
        
        has_venv = self.loader.has_virtual_env(str(skill_dir))
        self.assertFalse(has_venv)
        
        self.loader.create_venv(str(skill_dir), upgrade_pip=False)
        
        has_venv = self.loader.has_virtual_env(str(skill_dir))
        self.assertTrue(has_venv)


if __name__ == "__main__":
    unittest.main()
