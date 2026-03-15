#!/usr/bin/env python3
"""Test file skills enhancements"""

import os
import sys
import tempfile
import unittest
import importlib.util

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_skill_module(skill_name, base_path=None):
    """Load skill module by name"""
    if base_path is None:
        base_path = os.path.join(os.path.dirname(__file__), '..', 'skills', 'builtin')
    
    module_path = os.path.join(base_path, skill_name, 'main.py')
    spec = importlib.util.spec_from_file_location(f"{skill_name}_skill", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestReadFileSkill(unittest.TestCase):
    """Test read_file skill enhancements"""

    def setUp(self):
        """Create temporary test files"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test.txt")
        
        # Create test file with content
        with open(self.test_file, 'w', encoding='utf-8') as f:
            for i in range(1, 101):
                f.write(f"Line {i}: This is test content\n")

    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_read_file_basic(self):
        """Test basic file reading"""
        module = load_skill_module('read_file')
        result = module.execute({
            "file_path": self.test_file,
            "max_lines": 200
        })
        self.assertIn("文件内容", result)
        self.assertIn("100 行", result)

    def test_read_file_search(self):
        """Test file search functionality"""
        module = load_skill_module('read_file')
        result = module.execute({
            "file_path": self.test_file,
            "search_text": "Line 50",
            "context_lines": 2
        })
        self.assertIn("搜索结果", result)
        self.assertIn("第 50 行", result)

    def test_read_file_not_found(self):
        """Test search text not found"""
        module = load_skill_module('read_file')
        result = module.execute({
            "file_path": self.test_file,
            "search_text": "NONEXISTENT",
        })
        self.assertIn("未找到", result)

    def test_read_file_max_lines(self):
        """Test max lines truncation"""
        module = load_skill_module('read_file')
        result = module.execute({
            "file_path": self.test_file,
            "max_lines": 50
        })
        self.assertIn("已截断", result)
        self.assertIn("前 50 行", result)

    def test_read_file_stream(self):
        """Test streaming read"""
        module = load_skill_module('read_file')
        result = module.execute({
            "file_path": self.test_file,
            "stream": True,
            "max_lines": 200
        })
        self.assertIn("读取成功", result)

    def test_read_file_missing(self):
        """Test missing file"""
        module = load_skill_module('read_file')
        result = module.execute({
            "file_path": "/nonexistent/file.txt"
        })
        self.assertIn("错误", result)


class TestCreateFileSkill(unittest.TestCase):
    """Test create_file skill enhancements"""

    def setUp(self):
        """Create temporary test directory"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_create_file_basic(self):
        """Test basic file creation"""
        module = load_skill_module('create_file')
        file_path = os.path.join(self.temp_dir, "new.txt")
        result = module.execute({
            "file_path": file_path,
            "content": "Hello, World!"
        })
        self.assertIn("创建成功", result)
        self.assertTrue(os.path.exists(file_path))

    def test_create_file_append(self):
        """Test append mode"""
        module = load_skill_module('create_file')
        file_path = os.path.join(self.temp_dir, "append.txt")
        
        # Create initial file
        module.execute({
            "file_path": file_path,
            "content": "Line 1\n"
        })
        
        # Append content
        result = module.execute({
            "file_path": file_path,
            "content": "Line 2\n",
            "mode": "append"
        })
        
        self.assertIn("追加成功", result)
        
        # Verify content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertIn("Line 1", content)
        self.assertIn("Line 2", content)

    def test_create_file_auto_dirs(self):
        """Test auto-create parent directories"""
        module = load_skill_module('create_file')
        file_path = os.path.join(self.temp_dir, "nested/deep/dir/file.txt")
        result = module.execute({
            "file_path": file_path,
            "content": "Content",
            "create_parent_dirs": True
        })
        self.assertIn("创建成功", result)
        self.assertTrue(os.path.exists(file_path))


class TestApplyPatchSkill(unittest.TestCase):
    """Test apply_patch skill"""

    def setUp(self):
        """Create temporary test files"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "patch_test.txt")
        
        # Create test file
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write("Line 1\n")
            f.write("Line 2\n")
            f.write("Line 3\n")

    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_apply_patch_dry_run(self):
        """Test patch preview (dry run)"""
        module = load_skill_module('apply_patch')
        patch_text = """--- a/test.txt
+++ b/test.txt
@@ -1,3 +1,4 @@
 Line 1
+New Line 2
 Line 2
 Line 3
"""
        result = module.execute({
            "file_path": self.test_file,
            "patch_text": patch_text,
            "dry_run": True
        })
        self.assertIn("预览模式", result)

    def test_apply_patch_with_backup(self):
        """Test patch application with backup"""
        module = load_skill_module('apply_patch')
        patch_text = """--- a/test.txt
+++ b/test.txt
@@ -1,3 +1,4 @@
 Line 1
+New Line 2
 Line 2
 Line 3
"""
        result = module.execute({
            "file_path": self.test_file,
            "patch_text": patch_text,
            "backup": True
        })
        self.assertIn("应用成功", result)
        self.assertIn("备份文件", result)
        
        # Verify backup exists
        backup_path = self.test_file + '.bak'
        self.assertTrue(os.path.exists(backup_path))


class TestBatchReadSkill(unittest.TestCase):
    """Test batch_read skill"""

    def setUp(self):
        """Create temporary test files"""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create multiple test files
        for i in range(1, 6):
            file_path = os.path.join(self.temp_dir, f"file{i}.txt")
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"File {i} content\n" * 10)

    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_batch_read_list(self):
        """Test batch read with file list"""
        module = load_skill_module('batch_read')
        file_paths = [
            os.path.join(self.temp_dir, f"file{i}.txt")
            for i in range(1, 4)
        ]
        result = module.execute({
            "file_paths": file_paths
        })
        self.assertIn("批量读取完成", result)
        self.assertIn("✅ 成功", result)

    def test_batch_read_pattern(self):
        """Test batch read with pattern"""
        module = load_skill_module('batch_read')
        result = module.execute({
            "pattern": "*.txt",
            "directory": self.temp_dir,
            "max_files": 10
        })
        self.assertIn("批量读取完成", result)
        self.assertIn("成功", result)


if __name__ == '__main__':
    unittest.main()
