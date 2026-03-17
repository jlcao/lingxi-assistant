#!/usr/bin/env python3
"""记忆功能 Phase 4 测试（向量搜索）"""

import pytest
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestVectorStore:
    """向量存储测试"""
    
    @pytest.fixture
    def vector_store(self):
        """创建临时向量存储"""
        from lingxi.core.memory.vector_store import VectorStore
        
        fd, persist_dir = tempfile.mkdtemp()
        os.rmdir(persist_dir)  # 删除空目录
        
        store = VectorStore(persist_dir)
        
        yield store
        
        # 清理
        import shutil
        if os.path.exists(persist_dir):
            shutil.rmtree(persist_dir)
    
    def test_add_memory(self, vector_store):
        """测试添加记忆"""
        if not vector_store.is_available():
            pytest.skip("向量搜索不可用")
        
        memory_data = {
            "content": "我喜欢使用 Python 编程",
            "category": "preference",
            "importance": 4,
            "tags": ["coding", "python"],
            "workspace_path": "/tmp"
        }
        
        result = vector_store.add_memory(memory_data)
        assert result is True
    
    def test_vector_search(self, vector_store):
        """测试向量搜索"""
        if not vector_store.is_available():
            pytest.skip("向量搜索不可用")
        
        # 添加测试数据
        test_memories = [
            {"content": "我喜欢 Python", "category": "preference", "importance": 4, "tags": [], "workspace_path": "/tmp"},
            {"content": "JavaScript 也不错", "category": "preference", "importance": 3, "tags": [], "workspace_path": "/tmp"},
            {"content": "今天天气很好", "category": "fact", "importance": 2, "tags": [], "workspace_path": "/tmp"},
        ]
        
        for memory in test_memories:
            vector_store.add_memory(memory)
        
        # 搜索
        results = vector_store.search("编程语言", n_results=2)
        assert len(results) > 0
        
        # 验证结果相关性
        assert "Python" in results[0]['content'] or "JavaScript" in results[0]['content']
    
    def test_delete_memory(self, vector_store):
        """测试删除记忆"""
        if not vector_store.is_available():
            pytest.skip("向量搜索不可用")
        
        memory_data = {
            "content": "待删除的记忆",
            "category": "note",
            "importance": 3,
            "tags": [],
            "workspace_path": "/tmp"
        }
        
        vector_store.add_memory(memory_data)
        result = vector_store.delete_memory("待删除的记忆", "note")
        assert result is True


class TestHybridSearch:
    """混合搜索测试"""
    
    def test_hybrid_search(self):
        """测试混合搜索"""
        from lingxi.core.memory import MemoryManager
        from lingxi.core.memory.vector_store import VectorStore
        from lingxi.core.memory.hybrid_search import HybridSearch
        
        # 创建临时目录
        fd, temp_dir = tempfile.mkdtemp()
        os.rmdir(temp_dir)
        
        config = {
            "workspace": {"default_path": temp_dir},
            "memory": {
                "db_enabled": False,
                "vector_enabled": False  # 先测试纯关键词
            }
        }
        
        manager = MemoryManager(config)
        
        # 保存测试记忆
        manager.save_memory("我喜欢 Python", "preference", ["coding"], 4)
        manager.save_memory("JavaScript 也不错", "preference", ["coding"], 3)
        
        # 创建混合搜索
        hybrid_search = HybridSearch(manager)
        
        # 测试搜索
        results = hybrid_search.search("编程语言", top_k=2)
        assert len(results) > 0
        
        # 清理
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
