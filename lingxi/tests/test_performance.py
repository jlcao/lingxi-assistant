import time
import uuid
from lingxi.core.session.session_manager import SessionManager
from lingxi.context.manager import ContextManager


class TestPerformance:
    """测试性能优化效果"""

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

    def teardown_method(self):
        """清理测试环境"""
        import os
        if hasattr(self, 'test_db_path') and os.path.exists(self.test_db_path):
            os.unlink(self.test_db_path)

    def test_session_creation_performance(self):
        """测试会话创建性能"""
        start_time = time.time()
        
        # 创建10个会话管理器实例
        managers = []
        for i in range(10):
            session_id = str(uuid.uuid4())
            manager = SessionManager(self.config, session_id)
            managers.append(manager)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"创建10个会话管理器实例耗时: {total_time:.4f}秒")
        print(f"平均每个实例耗时: {total_time/10:.4f}秒")
        
        # 验证所有实例都是不同的
        assert len(set(managers)) == 10
        
        # 性能要求：创建10个实例耗时不超过1秒
        assert total_time < 1.0

    def test_cache_performance(self):
        """测试缓存性能"""
        session_id = str(uuid.uuid4())
        manager = SessionManager(self.config, session_id)
        
        # 第一次访问上下文（创建缓存）
        start_time = time.time()
        ctx1 = manager.get_session_context(session_id)
        first_time = time.time() - start_time
        
        # 第二次访问上下文（缓存命中）
        start_time = time.time()
        ctx2 = manager.get_session_context(session_id)
        second_time = time.time() - start_time
        
        print(f"第一次访问上下文耗时: {first_time:.4f}秒")
        print(f"第二次访问上下文耗时: {second_time:.4f}秒")
        
        # 验证缓存命中（时间应该显著减少）
        assert second_time < first_time * 0.5

    def test_llm_compression_cache(self):
        """测试LLM压缩缓存性能"""
        session_id = str(uuid.uuid4())
        context = ContextManager(self.config, session_id)
        
        # 测试文本
        test_content = """这是一段很长的测试文本，用于测试LLM压缩的缓存性能。"""
        
        # 第一次压缩（缓存未命中）
        start_time = time.time()
        summary1 = context._summarize_with_llm(test_content)
        first_time = time.time() - start_time
        
        # 第二次压缩（缓存命中）
        start_time = time.time()
        summary2 = context._summarize_with_llm(test_content)
        second_time = time.time() - start_time
        
        print(f"第一次LLM压缩耗时: {first_time:.4f}秒")
        print(f"第二次LLM压缩耗时: {second_time:.4f}秒")
        
        # 验证缓存命中（时间应该显著减少）
        assert second_time < first_time * 0.1
        # 验证摘要内容相同
        assert summary1 == summary2

    def test_context_compression_performance(self):
        """测试上下文压缩性能"""
        session_id = str(uuid.uuid4())
        context = ContextManager(self.config, session_id)
        
        # 添加多条消息
        for i in range(20):
            context.add_message("user", f"用户输入{i}")
            context.add_message("assistant", f"助手回复{i}")
            context.add_message("tool", f"工具结果{i}" * 10)  # 长工具结果
        
        # 执行压缩
        start_time = time.time()
        stats = context.compress()
        compression_time = time.time() - start_time
        
        print(f"上下文压缩耗时: {compression_time:.4f}秒")
        print(f"压缩前token数: {stats['before_tokens']}")
        print(f"压缩后token数: {stats['after_tokens']}")
        print(f"压缩率: {stats['compression_ratio']:.1%}")
        
        # 性能要求：压缩耗时不超过0.5秒
        assert compression_time < 0.5
        # 压缩率要求：至少30%
        assert stats['compression_ratio'] > 0.3

    def test_multiple_sessions_performance(self):
        """测试多会话性能"""
        start_time = time.time()
        
        # 创建5个会话并添加消息
        sessions = []
        for i in range(5):
            session_id = str(uuid.uuid4())
            manager = SessionManager(self.config, session_id)
            
            # 为每个会话添加10条消息
            for j in range(10):
                manager.get_session_context(session_id).add_message("user", f"用户输入{i}-{j}")
                manager.get_session_context(session_id).add_message("assistant", f"助手回复{i}-{j}")
            
            sessions.append(manager)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"创建5个会话并添加消息耗时: {total_time:.4f}秒")
        print(f"平均每个会话耗时: {total_time/5:.4f}秒")
        
        # 性能要求：5个会话操作耗时不超过2秒
        assert total_time < 2.0


if __name__ == "__main__":
    test = TestPerformance()
    test.setup_method()
    
    print("测试会话创建性能...")
    test.test_session_creation_performance()
    
    print("\n测试缓存性能...")
    test.test_cache_performance()
    
    print("\n测试LLM压缩缓存...")
    test.test_llm_compression_cache()
    
    print("\n测试上下文压缩性能...")
    test.test_context_compression_performance()
    
    print("\n测试多会话性能...")
    test.test_multiple_sessions_performance()
    
    test.teardown_method()
    print("\n所有性能测试完成！")
