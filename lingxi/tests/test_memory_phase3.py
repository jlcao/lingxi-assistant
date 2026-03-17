#!/usr/bin/env python3
"""记忆功能 Phase 3 测试（数据库支持）"""

import pytest
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lingxi.core.memory.database_migration import migrate, drop_all
from lingxi.core.memory.memory_database import MemoryDatabase


class TestMemoryDatabase:
    """记忆数据库测试"""
    
    @pytest.fixture
    def db(self):
        """创建临时数据库"""
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        # 初始化数据库
        migrate(db_path)
        database = MemoryDatabase(db_path)
        
        yield database
        
        # 清理
        drop_all(db_path)
        os.unlink(db_path)
    
    def test_save_memory(self, db):
        """测试保存记忆"""
        memory_data = {
            "id": "test123",
            "content": "测试记忆内容",
            "category": "note",
            "tags": ["test"],
            "importance": 3,
            "created_at": 1234567890.0,
            "updated_at": 1234567890.0,
            "access_count": 0,
            "workspace_path": "/tmp",
            "metadata": {}
        }
        
        result = db.save_memory(memory_data)
        assert result is True
        
        # 验证
        memory = db.get_memory("test123")
        assert memory is not None
        assert memory["content"] == "测试记忆内容"
    
    def test_search_memories(self, db):
        """测试搜索记忆"""
        # 保存测试数据
        for i in range(5):
            memory_data = {
                "id": f"test{i}",
                "content": f"测试记忆{i} Python",
                "category": "note",
                "tags": ["test"],
                "importance": 3 + i,
                "created_at": 1234567890.0 + i,
                "updated_at": 1234567890.0 + i,
                "access_count": i,
                "workspace_path": "/tmp",
                "metadata": {}
            }
            db.save_memory(memory_data)
        
        # 搜索
        results = db.search_memories("Python", limit=3)
        assert len(results) > 0
        assert "Python" in results[0]["content"]
    
    def test_update_access_count(self, db):
        """测试更新访问计数"""
        memory_data = {
            "id": "test_access",
            "content": "测试访问",
            "category": "note",
            "tags": [],
            "importance": 3,
            "created_at": 1234567890.0,
            "updated_at": 1234567890.0,
            "access_count": 0,
            "workspace_path": "/tmp",
            "metadata": {}
        }
        
        db.save_memory(memory_data)
        
        # 更新访问计数
        db.update_access_count("test_access", "测试查询")
        
        # 验证
        memory = db.get_memory("test_access")
        assert memory["access_count"] == 1
    
    def test_get_stats(self, db):
        """测试获取统计"""
        # 保存测试数据
        categories = ["preference", "fact", "decision"]
        for i, cat in enumerate(categories):
            memory_data = {
                "id": f"stat{i}",
                "content": f"测试{cat}",
                "category": cat,
                "tags": [],
                "importance": i + 1,
                "created_at": 1234567890.0,
                "updated_at": 1234567890.0,
                "access_count": 0,
                "workspace_path": "/tmp",
                "metadata": {}
            }
            db.save_memory(memory_data)
        
        # 获取统计
        stats = db.get_stats()
        assert stats["total"] == 3
        assert len(stats["by_category"]) == 3
        assert stats["by_importance"][1] == 1
        assert stats["by_importance"][2] == 1
        assert stats["by_importance"][3] == 1
    
    def test_delete_memory(self, db):
        """测试删除记忆"""
        memory_data = {
            "id": "to_delete",
            "content": "待删除",
            "category": "note",
            "tags": [],
            "importance": 3,
            "created_at": 1234567890.0,
            "updated_at": 1234567890.0,
            "access_count": 0,
            "workspace_path": "/tmp",
            "metadata": {}
        }
        
        db.save_memory(memory_data)
        
        # 删除
        result = db.delete_memory("to_delete")
        assert result is True
        
        # 验证
        memory = db.get_memory("to_delete")
        assert memory is None


class TestMemoryManagerWithDB:
    """MemoryManager 带数据库测试"""
    
    def test_memory_manager_db_integration(self):
        """测试 MemoryManager 数据库集成"""
        from lingxi.core.memory import MemoryManager
        
        # 创建临时目录
        fd, db_path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        
        config = {
            "workspace": {"default_path": "/tmp"},
            "memory": {
                "db_enabled": True,
                "db_path": db_path
            }
        }
        
        manager = MemoryManager(config)
        
        # 保存记忆
        memory = manager.save_memory(
            content="数据库测试",
            category="fact",
            importance=5
        )
        
        # 验证内存缓存
        assert memory.id in manager.memories
        
        # 验证数据库
        if manager.db:
            db_memory = manager.db.get_memory(memory.id)
            assert db_memory is not None
            assert db_memory["content"] == "数据库测试"
        
        # 清理
        os.unlink(db_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
