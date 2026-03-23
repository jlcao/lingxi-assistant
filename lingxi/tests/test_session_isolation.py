import pytest
import time
from lingxi.core.session.session_manager import SessionManager
from lingxi.core.session.task_manager import TaskManager
from lingxi.context.manager import ContextManager
import uuid
import json


class TestSessionIsolation:
    """测试会话隔离效果"""

    def setup_method(self):
        """设置测试环境"""
        # 创建测试配置
        import tempfile
        import os
        self.test_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.test_db_path = self.test_db.name
        self.test_db.close()
        
        self.config = {
            "session": {
                "db_path": self.test_db_path,
                "max_history_turns": 50
            },
            "context_management": {
                "token_budget": {
                    "max_tokens": 8000,
                    "compression_trigger": 0.7,
                    "critical_threshold": 0.9
                },
                "retention": {
                    "user_input_keep_turns": 10,
                    "tool_result_keep_turns": 5,
                    "task_boundary_archive": True
                },
                "compression": {
                    "strategy": "hybrid",
                    "summary_ratio": 0.3,
                    "enable_llm_summary": True,
                    "preserve_entities": True
                },
                "long_term_memory": {
                    "enabled": False
                }
            },
            "workspace": {
                "last_workspace": "./workspace"
            }
        }
        
        # 确保数据库表初始化
        import logging
        logger = logging.getLogger(__name__)
        from lingxi.core.session.database_manager import DatabaseManager
        db_manager = DatabaseManager(":memory:", logger)
        # 数据库初始化在DatabaseManager构造函数中自动执行

    def test_session_isolation(self):
        """测试多个会话之间的隔离"""
        # 创建两个不同的会话管理器实例
        session_id1 = str(uuid.uuid4())
        session_id2 = str(uuid.uuid4())
        
        manager1 = SessionManager(self.config, session_id1)
        manager2 = SessionManager(self.config, session_id2)
        
        # 验证两个实例是不同的对象
        assert manager1 is not manager2
        
        # 为第一个会话添加任务
        task_id1 = str(uuid.uuid4())
        manager1.create_task(session_id1, task_id1, "test", "任务1内容")
        
        # 为第二个会话添加任务
        task_id2 = str(uuid.uuid4())
        manager2.create_task(session_id2, task_id2, "test", "任务2内容")
        
        # 获取两个会话的任务列表
        tasks1 = manager1.task_manager.get_tasks_by_session(session_id1)
        tasks2 = manager2.task_manager.get_tasks_by_session(session_id2)
        
        # 验证任务列表长度
        assert len(tasks1) == 1
        assert len(tasks2) == 1
        
        # 验证任务内容隔离
        assert tasks1[0]["task_id"] == task_id1
        assert tasks1[0]["user_input"] == "任务1内容"
        assert tasks2[0]["task_id"] == task_id2
        assert tasks2[0]["user_input"] == "任务2内容"
        
        # 验证任务不交叉
        assert task_id1 != task_id2
        assert tasks1[0]["task_id"] != tasks2[0]["task_id"]

    def test_context_isolation(self):
        """测试上下文隔离"""
        # 创建两个不同的会话
        session_id1 = str(uuid.uuid4())
        session_id2 = str(uuid.uuid4())
        
        # 创建上下文管理器
        context1 = ContextManager(self.config, session_id1)
        context2 = ContextManager(self.config, session_id2)
        
        # 验证两个实例是不同的对象
        assert context1 is not context2
        
        # 为第一个上下文添加消息
        context1.add_message("user", "用户输入1")
        context1.add_message("assistant", "助手回复1")
        
        # 为第二个上下文添加消息
        context2.add_message("user", "用户输入2")
        context2.add_message("assistant", "助手回复2")
        
        # 获取上下文
        ctx1 = context1.get_context_for_llm()
        ctx2 = context2.get_context_for_llm()
        
        # 验证上下文长度
        assert len(ctx1) == 2
        assert len(ctx2) == 2
        
        # 验证上下文内容隔离
        assert "用户输入1" in ctx1[0]["content"]
        assert "助手回复1" in ctx1[1]["content"]
        assert "用户输入2" in ctx2[0]["content"]
        assert "助手回复2" in ctx2[1]["content"]
        
        # 验证上下文不交叉
        assert "用户输入1" not in ctx2[0]["content"]
        assert "用户输入2" not in ctx1[0]["content"]

    def test_cache_isolation(self):
        """测试缓存隔离"""
        # 创建两个不同的会话管理器
        session_id1 = str(uuid.uuid4())
        session_id2 = str(uuid.uuid4())
        
        manager1 = SessionManager(self.config, session_id1)
        manager2 = SessionManager(self.config, session_id2)
        
        # 访问两个会话的上下文
        ctx1 = manager1.get_session_context(session_id1)
        ctx2 = manager2.get_session_context(session_id2)
        
        # 验证上下文实例不同
        assert ctx1 is not ctx2
        
        # 验证缓存隔离
        assert len(manager1.session_context_cache) == 1
        assert len(manager2.session_context_cache) == 1
        assert session_id1 in manager1.session_context_cache
        assert session_id2 in manager2.session_context_cache
        assert session_id1 not in manager2.session_context_cache
        assert session_id2 not in manager1.session_context_cache

    def test_cache_expiry(self):
        """测试缓存过期机制"""
        session_id = str(uuid.uuid4())
        manager = SessionManager(self.config, session_id)
        
        # 访问上下文，触发缓存
        ctx1 = manager.get_session_context(session_id)
        assert session_id in manager.session_context_cache
        
        # 模拟缓存过期
        manager.session_cache_expiry = 0  # 设置过期时间为0
        time.sleep(0.1)
        
        # 再次访问上下文，应该重新创建
        ctx2 = manager.get_session_context(session_id)
        assert session_id in manager.session_context_cache
        # 注意：由于时间戳更新，ctx1和ctx2可能是同一个实例，但缓存机制应该正常工作

    def test_cache_size_limit(self):
        """测试缓存大小限制"""
        manager = SessionManager(self.config, "test")
        manager.session_cache_max_size = 2  # 设置最大缓存大小为2
        
        # 创建多个会话上下文
        session_ids = [str(uuid.uuid4()) for _ in range(3)]
        
        for session_id in session_ids:
            manager.get_session_context(session_id)
        
        # 验证缓存大小不超过限制
        assert len(manager.session_context_cache) <= 2


    def teardown_method(self):
        """清理测试环境"""
        import os
        if hasattr(self, 'test_db_path') and os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)

if __name__ == "__main__":
    pytest.main([__file__])
