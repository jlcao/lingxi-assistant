#!/usr/bin/env python3
"""记忆功能 Phase 2 测试"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lingxi.core.memory import MemoryManager, MemoryExtractor


class TestMemoryExtractor:
    """记忆提取器测试"""
    
    @pytest.fixture
    def extractor(self):
        manager = MemoryManager()
        return MemoryExtractor(manager)
    
    def test_extract_preference(self, extractor):
        """测试提取偏好"""
        message = "我喜欢使用 TypeScript 编程"
        memories = extractor.extract_from_message(message, "user")
        
        assert len(memories) > 0
        pref_memories = [m for m in memories if m.category == "preference"]
        assert len(pref_memories) > 0
    
    def test_extract_fact(self, extractor):
        """测试提取事实"""
        message = "记住，当前项目是灵犀助手"
        memories = extractor.extract_from_message(message, "user")
        
        fact_memories = [m for m in memories if m.category == "fact"]
        assert len(fact_memories) > 0
    
    def test_extract_todo(self, extractor):
        """测试提取待办"""
        message = "我要记得实现向量搜索功能"
        memories = extractor.extract_from_message(message, "user")
        
        todo_memories = [m for m in memories if m.category == "todo"]
        assert len(todo_memories) > 0
    
    def test_extract_from_session(self, extractor):
        """测试从会话提取"""
        session_history = [
            {"role": "user", "content": "我喜欢简洁的代码风格"},
            {"role": "assistant", "content": "好的，我记住了"},
            {"role": "user", "content": "当前项目是灵犀助手 v2.0"},
        ]
        
        memories = extractor.extract_from_session(
            session_history,
            auto_save=True,
            min_importance=3
        )
        
        assert len(memories) > 0
        print(f"提取了 {len(memories)} 条记忆")
    
    def test_importance_calculation(self, extractor):
        """测试重要性计算"""
        message = "我一定要记住这个重要的事情"
        memories = extractor.extract_from_message(message, "user")
        
        if memories:
            assert memories[0].importance >= 4


class TestSessionManagerIntegration:
    """SessionManager 集成测试"""
    
    def test_memory_injection(self):
        """测试记忆注入 - 直接测试 MemoryManager"""
        from lingxi.core.memory import MemoryManager
        
        # 创建测试目录
        os.makedirs("/tmp/test_workspace", exist_ok=True)
        
        # 创建 MEMORY.md
        with open("/tmp/test_workspace/MEMORY.md", 'w') as f:
            f.write("# MEMORY.md\n\n## 用户偏好\n\n- 我喜欢 TypeScript\n")
        
        config = {
            "workspace": {"default_path": "/tmp/test_workspace"}
        }
        
        manager = MemoryManager(config)
        count = manager.load_memory("/tmp/test_workspace")
        
        # 验证记忆已加载
        assert count > 0
        assert len(manager.memories) > 0
        print(f"加载了 {len(manager.memories)} 条记忆")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
