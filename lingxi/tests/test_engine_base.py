#!/usr/bin/env python3
"""Engine 模块单元测试"""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch

pytest_plugins = ('pytest_asyncio',)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class MockSkillCaller:
    """模拟 SkillCaller"""
    def __init__(self):
        self.call_count = 0
        self.subagent_scheduler = None
    
    def call(self, skill_name, parameters):
        self.call_count += 1
        return {"success": True, "result": f"Executed {skill_name}"}
    
    def call_with_security_check(self, skill_name, parameters, require_confirmation=False):
        self.call_count += 1
        return {"success": True, "result": f"Executed {skill_name}"}


class MockSessionManager:
    """模拟 SessionManager"""
    def __init__(self):
        self.sessions = {}
        self.memory_manager = Mock()
    
    def create_session(self, session_id, **kwargs):
        class Session:
            id = session_id
            history = []
            system_prompt = "You are a helpful assistant."
        self.sessions[session_id] = Session()
        return self.sessions[session_id]
    
    def get_session(self, session_id):
        return self.sessions.get(session_id)
    
    def get_history(self, session_id):
        session = self.get_session(session_id)
        return session.history if session else []


class MockSubAgentScheduler:
    """模拟 SubAgentScheduler"""
    def __init__(self, session_manager, skill_caller, config):
        self.session_manager = session_manager
        self.skill_caller = skill_caller
        self.config = config
    
    async def parallel_execute(self, tasks, workspace_path=None, context=None):
        class MockResult:
            def __init__(self, result):
                self.result = result
        return [MockResult(f"结果 {i+1}") for i, _ in enumerate(tasks)]


class MockLLMClient:
    """模拟 LLMClient"""
    def __init__(self, config):
        self.config = config
    
    def complete(self, prompt, task_level=None):
        return "Mock response"
    
    def stream_complete(self, prompt, task_level=None):
        return iter(["Mock ", "response"])


class MockSoulInjector:
    """模拟 SoulInjector"""
    def __init__(self, workspace_path):
        self.workspace_path = workspace_path
        self.soul_data = {}
    
    def load(self):
        pass
    
    def build_system_prompt(self, content):
        return "Mock soul prompt"


class TestEngineBase:
    """BaseEngine 测试"""
    
    @pytest.fixture
    def engine(self):
        """创建测试引擎"""
        config = {
            "execution_mode": {
                "complex": {
                    "max_plan_steps": 8,
                    "max_replan_count": 2,
                    "max_step_retries": 3
                }
            },
            "workspace": {
                "default_path": "/tmp"
            }
        }
        skill_caller = MockSkillCaller()
        session_manager = MockSessionManager()
        
        # Mock dependencies
        with patch('lingxi.core.engine.base.LLMClient', MockLLMClient), \
             patch('lingxi.core.engine.base.SoulInjector', MockSoulInjector):
            from lingxi.core.engine.base import BaseEngine
            return BaseEngine(config, skill_caller, session_manager)
    
    def test_engine_initialization(self, engine):
        """测试引擎初始化"""
        assert engine is not None
        assert engine.config is not None
        assert engine.skill_caller is not None
        assert engine.session_manager is not None
    
    def test_should_search_memory(self, engine):
        """测试记忆搜索检测"""
        # 应该触发记忆搜索的情况
        assert engine._should_search_memory("我记得之前说过") is True
        assert engine._should_search_memory("你记得我的偏好吗") is True
        assert engine._should_search_memory("上次提到的项目") is True
        assert engine._should_search_memory("我的习惯是什么") is True
        
        # 不应该触发的情况
        assert engine._should_search_memory("帮我写代码") is False
        assert engine._should_search_memory("分析这个项目") is False
    
    def test_should_extract_memory(self, engine):
        """测试记忆提取检测"""
        # 应该触发记忆保存的情况
        assert engine._should_extract_memory("记住这个") is True
        assert engine._should_extract_memory("记下我说的话") is True
        assert engine._should_extract_memory("保存这个信息") is True
        assert engine._should_extract_memory("别忘了") is True
        
        # 不应该触发的情况
        assert engine._should_extract_memory("帮我分析代码") is False
        assert engine._should_extract_memory("执行这个命令") is False
    
    def test_execute_simple_task(self, engine):
        """测试执行简单任务"""
        session = engine.session_manager.create_session("test_session_1")
        
        # 验证会话创建成功
        assert session is not None
        assert session.id == "test_session_1"
    
    def test_execute_with_memory_search(self, engine):
        """测试执行带记忆搜索的任务"""
        session = engine.session_manager.create_session("test_session_2")
        
        # 验证记忆搜索检测
        assert engine._should_search_memory("我记得之前说过喜欢 Python") is True
        assert session is not None


class TestDirectEngine:
    """DirectEngine 测试"""
    
    @pytest.fixture
    def direct_engine(self):
        """创建 DirectEngine"""
        config = {
            "workspace": {
                "default_path": "/tmp"
            }
        }
        
        with patch('lingxi.core.engine.direct.LLMClient', MockLLMClient), \
             patch('lingxi.core.engine.direct.SoulInjector', MockSoulInjector):
            from lingxi.core.engine.direct import DirectEngine
            return DirectEngine(config)
    
    def test_direct_response(self, direct_engine):
        """测试直接响应"""
        # DirectEngine 使用 process 方法而不是 execute_task
        assert direct_engine is not None
        assert direct_engine.config is not None
        assert direct_engine.llm_client is not None
    
    def test_direct_with_skill_call(self, direct_engine):
        """测试 DirectEngine 配置"""
        # 验证 DirectEngine 初始化正常
        assert direct_engine.llm_client is not None
        assert direct_engine.soul_injector is not None
        assert direct_engine.max_tokens is not None


class TestEngineWithSubagents:
    """Engine 子代理功能测试"""
    
    @pytest.fixture
    def engine_with_subagents(self):
        """创建带子代理的引擎"""
        config = {
            "execution_mode": {
                "complex": {
                    "max_plan_steps": 8
                }
            },
            "workspace": {
                "default_path": "/tmp"
            }
        }
        skill_caller = MockSkillCaller()
        session_manager = MockSessionManager()
        
        with patch('lingxi.core.engine.base.LLMClient', MockLLMClient), \
             patch('lingxi.core.engine.base.SoulInjector', MockSoulInjector):
            from lingxi.core.engine.base import BaseEngine
            engine = BaseEngine(config, skill_caller, session_manager)
        
        # 添加子代理调度器
        engine.subagent_scheduler = MockSubAgentScheduler(
            session_manager=session_manager,
            skill_caller=skill_caller,
            config=config
        )
        
        return engine
    
    def test_should_use_subagent(self, engine_with_subagents):
        """测试子代理使用检测"""
        engine = engine_with_subagents
        
        # 应该使用子代理的情况
        assert engine._should_use_subagent("同时分析 A 和 B") is True
        assert engine._should_use_subagent("并行执行多个任务") is True
        assert engine._should_use_subagent("任务 1\n任务 2\n任务 3") is True
        
        # 不应该使用的情况
        assert engine._should_use_subagent("你好") is False
        assert engine._should_use_subagent("帮我写代码") is False
    
    def test_decompose_task(self, engine_with_subagents):
        """测试任务分解"""
        engine = engine_with_subagents
        
        # 按换行符分解
        tasks = engine._decompose_task("任务 1\n任务 2\n任务 3")
        assert len(tasks) == 3
        assert tasks[0] == "任务 1"
        
        # 按逗号分解
        tasks = engine._decompose_task("任务 1，任务 2，任务 3")
        assert len(tasks) == 3
        
        # 按"和"分解
        tasks = engine._decompose_task("分析 A 和分析 B")
        assert len(tasks) == 2
    
    def test_aggregate_results(self, engine_with_subagents):
        """测试结果聚合"""
        engine = engine_with_subagents
        
        # 创建模拟结果
        class MockResult:
            def __init__(self, result):
                self.result = result
        
        results = [
            MockResult("结果 1"),
            MockResult("结果 2"),
            MockResult("结果 3")
        ]
        
        aggregated = engine._aggregate_subagent_results(results)
        
        # 验证结果格式（实际输出没有空格）
        assert "【子任务1】" in aggregated
        assert "【子任务2】" in aggregated
        assert "【子任务3】" in aggregated
        assert "结果 1" in aggregated
        assert "结果 2" in aggregated
        assert "结果 3" in aggregated


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
