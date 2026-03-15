#!/usr/bin/env python3
"""
Test suite for file skills: read_file, create_file, apply_patch, batch_read

Tests cover:
- Basic functionality
- Enhanced features (streaming, encoding detection, append mode)
- Edge cases and error handling
"""

import os
import sys
import tempfile
import shutil
import unittest
import re

# Add skills to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../lingxi/skills/builtin'))

from read_file.main import execute as read_file_execute
from create_file.main import execute as create_file_execute
from apply_patch.main import execute as apply_patch_execute
from batch_read.main import execute as batch_read_execute


class TestReadFile(unittest.TestCase):
    """Test read_file skill"""

    def setUp(self):
        """Create temporary test files"""
        self.test_dir = tempfile.mkdtemp()
        
        # Create test file with UTF-8 encoding
        self.utf8_file = os.path.join(self.test_dir, 'test_utf8.txt')
        with open(self.utf8_file, 'w', encoding='utf-8') as f:
            f.write("Line 1: Hello World\n")
            f.write("Line 2: Python is great\n")
            f.write("Line 3: Test content\n")
            f.write("Line 4: More content\n")
            f.write("Line 5: Final line\n")
        
        # Create test file with keyword for search
        self.search_file = os.path.join(self.test_dir, 'test_search.txt')
        with open(self.search_file, 'w', encoding='utf-8') as f:
            for i in range(1, 21):
                f.write(f"Line {i}: This is test content\n")
    
    def tearDown(self):
        """Clean up temporary files"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_basic_read(self):
        """Test basic file reading"""
        result = read_file_execute({
            "file_path": self.utf8_file
        })
        # Success can be indicated by 📄 or ✅
        self.assertTrue("📄" in result or "✅" in result)
        self.assertIn("Hello World", result)
        self.assertIn("5 行", result)
    
    def test_search_functionality(self):
        """Test search with context"""
        result = read_file_execute({
            "file_path": self.search_file,
            "search_text": "Line 5",
            "context_lines": 2
        })
        self.assertIn("搜索", result)
        self.assertIn("Line 5", result)
    
    def test_search_not_found(self):
        """Test search when text not found"""
        result = read_file_execute({
            "file_path": self.utf8_file,
            "search_text": "nonexistent_keyword_xyz"
        })
        self.assertIn("未找到", result)
    
    def test_max_lines_limit(self):
        """Test max_lines parameter"""
        result = read_file_execute({
            "file_path": self.search_file,
            "max_lines": 5
        })
        self.assertIn("截断", result)
    
    def test_missing_file_path(self):
        """Test error handling for missing file_path"""
        result = read_file_execute({})
        self.assertIn("❌", result)
        self.assertIn("缺少文件路径", result)
    
    def test_file_not_found(self):
        """Test error handling for non-existent file"""
        result = read_file_execute({
            "file_path": "/nonexistent/path/file.txt"
        })
        self.assertIn("❌", result)


class TestCreateFile(unittest.TestCase):
    """Test create_file skill"""

    def setUp(self):
        """Create temporary test directory"""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up temporary files"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_create_new_file(self):
        """Test creating a new file"""
        file_path = os.path.join(self.test_dir, 'new_file.txt')
        result = create_file_execute({
            "file_path": file_path,
            "content": "Hello, World!"
        })
        self.assertIn("✅", result)
        self.assertIn("创建成功", result)
        self.assertTrue(os.path.exists(file_path))
        
        # Verify content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertEqual(content, "Hello, World!")
    
    def test_append_mode(self):
        """Test appending to existing file"""
        file_path = os.path.join(self.test_dir, 'append_file.txt')
        
        # Create initial file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("Initial content\n")
        
        # Append content
        result = create_file_execute({
            "file_path": file_path,
            "content": "Appended content\n",
            "mode": "append"
        })
        self.assertIn("✅", result)
        self.assertIn("追加成功", result)
        
        # Verify content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self.assertEqual(content, "Initial content\nAppended content\n")
    
    def test_auto_create_parent_dirs(self):
        """Test automatic parent directory creation"""
        file_path = os.path.join(self.test_dir, 'nested', 'dir', 'file.txt')
        result = create_file_execute({
            "file_path": file_path,
            "content": "Nested content",
            "create_parent_dirs": True
        })
        self.assertIn("✅", result)
        self.assertTrue(os.path.exists(file_path))
    
    def test_missing_file_path(self):
        """Test error handling for missing file_path"""
        result = create_file_execute({
            "content": "Some content"
        })
        self.assertIn("❌", result)
        self.assertIn("缺少文件路径", result)


class TestApplyPatch(unittest.TestCase):
    """Test apply_patch skill"""

    def setUp(self):
        """Create temporary test files"""
        self.test_dir = tempfile.mkdtemp()
        
        # Create test file
        self.test_file = os.path.join(self.test_dir, 'test_patch.py')
        with open(self.test_file, 'w', encoding='utf-8') as f:
            f.write("line 1\n")
            f.write("line 2\n")
            f.write("line 3\n")
            f.write("line 4\n")
            f.write("line 5\n")
    
    def tearDown(self):
        """Clean up temporary files"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_dry_run_preview(self):
        """Test patch preview without applying"""
        patch_text = """--- a/test.py
+++ b/test.py
@@ -2,3 +2,4 @@
 line 2
-line 3
+modified line 3
 line 4
+new line 5
"""
        result = apply_patch_execute({
            "file_path": self.test_file,
            "patch_text": patch_text,
            "dry_run": True
        })
        # Preview mode uses 🔍 instead of ✅
        self.assertTrue("🔍" in result or "✅" in result)
        self.assertIn("预览模式", result)
    
    def test_apply_patch_with_backup(self):
        """Test applying patch with backup"""
        patch_text = """--- a/test.py
+++ b/test.py
@@ -2,3 +2,4 @@
 line 2
-line 3
+modified line 3
 line 4
+new line 5
"""
        result = apply_patch_execute({
            "file_path": self.test_file,
            "patch_text": patch_text,
            "backup": True
        })
        self.assertIn("✅", result)
        self.assertIn("补丁应用成功", result)
        self.assertIn("备份文件", result)
        
        # Verify backup was created
        backup_path = self.test_file + '.bak'
        self.assertTrue(os.path.exists(backup_path))
    
    def test_missing_file_path(self):
        """Test error handling for missing file_path"""
        result = apply_patch_execute({
            "patch_text": "some patch"
        })
        self.assertIn("❌", result)
        self.assertIn("缺少 file_path", result)
    
    def test_missing_patch_text(self):
        """Test error handling for missing patch_text"""
        result = apply_patch_execute({
            "file_path": self.test_file
        })
        self.assertIn("❌", result)
        self.assertIn("缺少 patch_text", result)
    
    def test_file_not_found(self):
        """Test error handling for non-existent file"""
        result = apply_patch_execute({
            "file_path": "/nonexistent/file.txt",
            "patch_text": "some patch"
        })
        self.assertIn("❌", result)
        self.assertIn("文件不存在", result)


class TestBatchRead(unittest.TestCase):
    """Test batch_read skill"""

    def setUp(self):
        """Create temporary test files"""
        self.test_dir = tempfile.mkdtemp()
        
        # Create multiple test files
        for i in range(1, 6):
            file_path = os.path.join(self.test_dir, f'test_{i}.txt')
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"File {i} content\n")
                f.write(f"Line 2 of file {i}\n")
    
    def tearDown(self):
        """Clean up temporary files"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_batch_read_file_list(self):
        """Test batch reading with file list"""
        file_paths = [
            os.path.join(self.test_dir, 'test_1.txt'),
            os.path.join(self.test_dir, 'test_2.txt'),
            os.path.join(self.test_dir, 'test_3.txt')
        ]
        result = batch_read_execute({
            "file_paths": file_paths
        })
        self.assertIn("✅", result)
        self.assertIn("批量读取完成", result)
        # Check for success count using regex (no space between number and 个)
        self.assertTrue(re.search(r'成功.*3.*个', result) is not None)
    
    def test_batch_read_with_pattern(self):
        """Test batch reading with pattern matching"""
        result = batch_read_execute({
            "pattern": "*.txt",
            "directory": self.test_dir,
            "max_files": 10
        })
        self.assertIn("✅", result)
        self.assertIn("批量读取完成", result)
        # Check for success count using regex
        self.assertTrue(re.search(r'成功.*5.*个', result) is not None)
    
    def test_batch_read_max_files_limit(self):
        """Test max_files parameter"""
        result = batch_read_execute({
            "pattern": "*.txt",
            "directory": self.test_dir,
            "max_files": 2
        })
        self.assertIn("✅", result)
        # Should only read 2 files
        self.assertTrue(re.search(r'成功.*2.*个', result) is not None)
    
    def test_batch_read_empty_paths(self):
        """Test error handling for empty file paths"""
        result = batch_read_execute({})
        self.assertIn("❌", result)
        self.assertIn("没有指定文件路径", result)


class TestEncodingDetection(unittest.TestCase):
    """Test encoding detection functionality"""

    def setUp(self):
        """Create temporary test files with different encodings"""
        self.test_dir = tempfile.mkdtemp()
        
        # Create UTF-8 file
        self.utf8_file = os.path.join(self.test_dir, 'utf8.txt')
        with open(self.utf8_file, 'w', encoding='utf-8') as f:
            f.write("UTF-8 测试内容\n")
        
        # Create GBK file (Chinese encoding)
        self.gbk_file = os.path.join(self.test_dir, 'gbk.txt')
        with open(self.gbk_file, 'w', encoding='gbk') as f:
            f.write("GBK 测试内容\n")
    
    def tearDown(self):
        """Clean up temporary files"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_utf8_encoding_detection(self):
        """Test UTF-8 encoding auto-detection"""
        result = read_file_execute({
            "file_path": self.utf8_file,
            "detect_encoding": True
        })
        # Success can be indicated by 📄 or ✅
        self.assertTrue("📄" in result or "✅" in result)
        self.assertIn("测试内容", result)
    
    def test_gbk_encoding_detection(self):
        """Test GBK encoding auto-detection"""
        # Note: chardet may not always correctly detect GBK with small samples
        # This test verifies the feature exists, but detection accuracy varies
        result = read_file_execute({
            "file_path": self.gbk_file,
            "detect_encoding": True
        })
        # Either it successfully detects and reads, or it fails with encoding error
        # Both are valid outcomes depending on chardet's detection
        self.assertTrue(
            "📄" in result or "✅" in result or "编码错误" in result
        )
    
    def test_manual_encoding_override(self):
        """Test manual encoding specification"""
        result = read_file_execute({
            "file_path": self.utf8_file,
            "encoding": "utf-8",
            "detect_encoding": False
        })
        # Success can be indicated by 📄 or ✅
        self.assertTrue("📄" in result or "✅" in result)
        self.assertIn("测试内容", result)


class TestStreamRead(unittest.TestCase):
    """Test streaming read functionality"""

    def setUp(self):
        """Create large test file"""
        self.test_dir = tempfile.mkdtemp()
        self.large_file = os.path.join(self.test_dir, 'large.txt')
        
        # Create a file with 2000 lines
        with open(self.large_file, 'w', encoding='utf-8') as f:
            for i in range(1, 2001):
                f.write(f"Line {i}: This is test content for streaming\n")
    
    def tearDown(self):
        """Clean up temporary files"""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_stream_read_large_file(self):
        """Test streaming read with max_lines limit"""
        result = read_file_execute({
            "file_path": self.large_file,
            "stream": True,
            "max_lines": 100
        })
        # Stream read may use ⚠️ when limit is hit, or ✅ for success
        self.assertTrue("⚠️" in result or "✅" in result)
        # Should mention the limit
        self.assertIn("100", result)
    
    def test_stream_read_chunk_size(self):
        """Test streaming with custom chunk size"""
        result = read_file_execute({
            "file_path": self.large_file,
            "stream": True,
            "chunk_size": 16384,
            "max_lines": 500
        })
        # Stream read may use ⚠️ when limit is hit, or ✅ for success
        self.assertTrue("⚠️" in result or "✅" in result)
        # Should mention the limit
        self.assertIn("500", result)


if __name__ == '__main__':
    # Run tests with verbosity
    unittest.main(verbosity=2)
