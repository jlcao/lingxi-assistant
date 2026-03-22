#!/usr/bin/env python3
"""Session 模块单元测试"""

import pytest
import sys
import os
import tempfile
import shutil
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lingxi.core.session.session_manager import SessionManager, session_to_dict, dict_to_session
from lingxi.core.session.session_models import Session
from lingxi.core.session.database_manager import DatabaseManager
from lingxi.core.memory import MemoryManager


class TestSessionManager:
    """SessionManager 测试"""
    
    @pytest.fixture
    def session_manager(self):
        """创建 SessionManager"""
        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        
        # 确保 data 目录存在（ContextManager 需要）
        data_dir = os.path.join(temp_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        
        config = {
            "workspace": {"default_path": temp_dir},
            "session": {
                "db_path": os.path.join(temp_dir, "sessions.db")
            },
            "context_management": {
                "long_term_memory": {
                    "enabled": False
                }
            }
        }
        
        manager = SessionManager(config, session_id="test_session")
        
        yield manager
        
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_session_manager_initialization(self, session_manager):
        """测试 SessionManager 初始化"""
        assert session_manager is not None
        assert session_manager.config is not None
        assert hasattr(session_manager, 'memory_manager')
    
    def test_create_session(self, session_manager):
        """测试创建会话"""
        session_id = session_manager.create_session(
            user_name="test_user"
        )
        
        assert session_id is not None
        assert isinstance(session_id, str)
        assert len(session_id) > 0
    
    def test_get_session(self, session_manager):
        """测试获取会话"""
        # 创建会话
        created_session_id = session_manager.create_session("test_user")
        
        # 获取会话信息
        session_info = session_manager.get_session_info(created_session_id)
        
        assert session_info is not None
        assert session_info["session_id"] == created_session_id
    
    def test_get_nonexistent_session(self, session_manager):
        """测试获取不存在的会话"""
        session_info = session_manager.get_session_info("nonexistent_session")
        
        assert session_info is None
    
    def test_list_sessions(self, session_manager):
        """测试列出会话"""
        # 创建多个会话
        session_manager.create_session("user_1")
        session_manager.create_session("user_2")
        session_manager.create_session("user_3")
        
        # 列出会话
        sessions = session_manager.list_all_sessions()
        
        assert len(sessions) >= 3
    
    def test_end_session(self, session_manager):
        """测试结束会话"""
        # 创建会话
        session_id = session_manager.create_session("test_user")
        
        # 结束会话（会提取记忆）
        session_manager.end_session(session_id, auto_extract_memory=False)
        
        # 验证会话还在
        session_info = session_manager.get_session_info(session_id)
        assert session_info is not None
    
    def test_memory_injection(self, session_manager):
        """测试记忆注入"""
        # 创建 MEMORY.md
        memory_content = """# MEMORY.md - 长期记忆

**最后更新：** 2024-01-01 12:00

## 用户偏好

- 我喜欢 TypeScript
- 我习惯使用 VS Code

## 重要事实

- 当前项目是灵犀助手
"""
        
        with open(session_manager.memory_manager.memory_file, 'w') as f:
            f.write(memory_content)
        
        # 重新加载记忆
        session_manager.memory_manager.load_memory()
        
        # 创建会话（会自动注入记忆）
        session_id = session_manager.create_session("test_user")
        
        # 验证记忆已加载
        assert len(session_manager.memory_manager.memories) > 0
    
    def test_session_with_history(self, session_manager):
        """测试带历史记录的会话"""
        import uuid
        
        # 创建会话
        session_id = session_manager.create_session("test_user")
        
        # 创建任务（添加历史记录）
        task_id = str(uuid.uuid4())
        session_manager.task_manager.create_task(
            session_id=session_id,
            task_id=task_id,
            task_type="simple",
            user_input="你好"
        )
        
        # 设置任务结果
        session_manager.task_manager.set_task_result(
            session_id=session_id,
            task_id=task_id,
            result="你好！有什么可以帮助你的？"
        )
        
        # 获取会话信息（包含任务历史）
        session_info = session_manager.get_session_info(session_id)
        
        assert session_info is not None
        assert session_info["task_count"] >= 1


class TestSessionModels:
    """Session 数据模型测试"""
    
    def test_session_creation(self):
        """测试 Session 对象创建"""
        from datetime import datetime
        
        session = Session(
            session_id="test_session",
            user_name="test_user",
            title="测试会话",
            current_task_id="",
            total_tokens=0,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        assert session.session_id == "test_session"
        assert session.user_name == "test_user"
        assert session.title == "测试会话"
        assert session.total_tokens == 0
    
    def test_session_serialization(self):
        """测试 Session 序列化"""
        from datetime import datetime
        
        session = Session(
            session_id="test_session",
            user_name="test_user",
            title="测试会话"
        )
        
        # 序列化
        data = session_to_dict(session)
        
        assert data["session_id"] == "test_session"
        assert data["user_name"] == "test_user"
        
        # 反序列化
        session2 = dict_to_session(data)
        
        assert session2.session_id == session.session_id
        assert session2.user_name == session.user_name


class TestDatabaseManager:
    """数据库管理器测试"""
    
    @pytest.fixture
    def db_manager(self):
        """创建数据库管理器"""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test.db")
        
        logger = logging.getLogger("test_db_manager")
        logger.setLevel(logging.DEBUG)
        
        manager = DatabaseManager(db_path, logger)
        
        yield manager
        
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_database_initialization(self, db_manager):
        """测试数据库初始化"""
        assert db_manager is not None
        assert os.path.exists(db_manager.db_path)
    
    def test_save_and_load_session(self, db_manager):
        """测试保存和加载会话"""
        # 使用 execute_sql 直接插入会话
        db_manager.execute_sql("""
            INSERT INTO sessions (session_id, user_name, title, total_tokens)
            VALUES (?, ?, ?, ?)
        """, ("test_session", "test_user", "测试会话", 0))
        
        # 查询会话
        result = db_manager.execute_sql("""
            SELECT session_id, user_name, title FROM sessions WHERE session_id = ?
        """, ("test_session",), fetch=True)
        
        assert result is not None
        assert len(result) == 1
        assert result[0][0] == "test_session"
    
    def test_delete_session(self, db_manager):
        """测试删除会话"""
        # 插入会话
        db_manager.execute_sql("""
            INSERT INTO sessions (session_id, user_name, title, total_tokens)
            VALUES (?, ?, ?, ?)
        """, ("session_to_delete", "test_user", "测试会话", 0))
        
        # 删除会话
        db_manager.execute_sql("""
            DELETE FROM sessions WHERE session_id = ?
        """, ("session_to_delete",))
        
        # 验证已删除
        result = db_manager.execute_sql("""
            SELECT session_id FROM sessions WHERE session_id = ?
        """, ("session_to_delete",), fetch=True)
        
        assert result is None or len(result) == 0
    
    def test_list_sessions(self, db_manager):
        """测试列出会话"""
        # 创建多个会话
        for i in range(5):
            db_manager.execute_sql("""
                INSERT INTO sessions (session_id, user_name, title, total_tokens)
                VALUES (?, ?, ?, ?)
            """, (f"session_{i}", f"user_{i}", f"测试会话{i}", 0))
        
        # 列出会话
        result = db_manager.execute_sql("""
            SELECT session_id FROM sessions
        """, fetch=True)
        
        assert result is not None
        assert len(result) >= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
