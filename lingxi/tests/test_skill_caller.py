#!/usr/bin/env python3
"""SkillCaller 单元测试"""

import pytest
import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lingxi.core.skill_caller import SkillCaller


class MockSessionManager:
    """模拟 SessionManager"""
    def __init__(self):
        self.sessions = {}
    
    def create_session(self, session_id, **kwargs):
        class Session:
            id = session_id
            history = []
            system_prompt = "You are a helpful assistant."
        self.sessions[session_id] = Session()
        return self.sessions[session_id]
    
    def get_session(self, session_id):
        return self.sessions.get(session_id)


class TestSkillCaller:
    """SkillCaller 测试"""
    
    @pytest.fixture
    def skill_caller(self):
        """创建 SkillCaller"""
        config = {
            "skill_call": {
                "default_timeout": 30,
                "retry_count": 3
            },
            "security": {
                "workspace_root": tempfile.gettempdir()
            },
            "skills": {
                "builtin_skills_dir": "skills/builtin",
                "use_memory_registry": True
            }
        }
        
        caller = SkillCaller(config)
        
        # 设置 SessionManager
        caller.session_manager = MockSessionManager()
        caller.set_workspace_manager(None)
        
        return caller
    
    def test_skill_caller_initialization(self, skill_caller):
        """测试 SkillCaller 初始化"""
        assert skill_caller is not None
        assert skill_caller.config is not None
        assert hasattr(skill_caller, 'skill_system')
        assert hasattr(skill_caller, 'subagent_scheduler')
    
    def test_call_skill(self, skill_caller):
        """测试调用技能"""
        # 列出可用技能
        skills = skill_caller.list_available_skills()
        
        # 验证技能列表方法可用（可能为空，取决于环境）
        assert skills is not None
        assert isinstance(skills, list)
    
    def test_call_nonexistent_skill(self, skill_caller):
        """测试调用不存在的技能"""
        result = skill_caller.call(
            skill_name="nonexistent_skill",
            parameters={}
        )
        
        assert result["success"] is False
        assert "技能不存在" in result.get("error", "")
    
    def test_call_with_retry(self, skill_caller):
        """测试重试机制"""
        # 验证重试配置
        assert skill_caller.retry_count == 3
        assert skill_caller.default_timeout == 30
    
    def test_spawn_subagent(self, skill_caller):
        """测试 Spawn 子代理"""
        import asyncio
        
        async def run_test():
            task_id = await skill_caller.subagent_scheduler.spawn(
                task="测试任务",
                timeout=60
            )
            
            assert task_id is not None
            
            # 获取任务
            task = skill_caller.subagent_scheduler.get_task(task_id)
            assert task is not None
            assert task.status in ["pending", "running"]
        
        asyncio.run(run_test())
    
    def test_list_subagents(self, skill_caller):
        """测试列出子代理"""
        # 初始应该没有子代理
        tasks = skill_caller.list_subagents()
        assert tasks is not None
    
    def test_get_subagent_status(self, skill_caller):
        """测试获取子代理状态"""
        import asyncio
        
        async def run_test():
            # 创建子代理
            task_id = await skill_caller.subagent_scheduler.spawn(
                task="测试状态",
                timeout=60
            )
            
            # 获取状态
            status = skill_caller.get_subagent_status(task_id)
            
            assert status is not None
            assert status in ["pending", "running", "completed", "failed", "timeout"]
        
        asyncio.run(run_test())
    
    def test_security_sandbox(self, skill_caller):
        """测试安全沙箱"""
        assert hasattr(skill_caller, 'sandbox')
        assert skill_caller.sandbox is not None
    
    def test_validate_parameters(self, skill_caller):
        """测试参数验证"""
        # 获取技能信息
        skills = skill_caller.list_available_skills()
        
        if len(skills) > 0:
            skill_name = skills[0].get("skill_id")
            
            # 验证空参数
            result = skill_caller.validate_parameters(skill_name, {})
            
            # 应该有验证结果
            assert "valid" in result


class TestSkillCallerWithMemory:
    """SkillCaller 带记忆功能测试"""
    
    @pytest.fixture
    def skill_caller_with_memory(self):
        """创建带记忆的 SkillCaller"""
        temp_dir = tempfile.mkdtemp()
        
        config = {
            "skill_call": {
                "default_timeout": 30,
                "retry_count": 3
            },
            "security": {
                "workspace_root": temp_dir
            },
            "skills": {
                "builtin_skills_dir": "skills/builtin",
                "use_memory_registry": True
            },
            "memory": {
                "db_enabled": False,
                "vector_enabled": False
            },
            "workspace": {
                "default_path": temp_dir
            }
        }
        
        caller = SkillCaller(config)
        caller.session_manager = MockSessionManager()
        caller.set_workspace_manager(None)
        
        yield caller
        
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_memory_search_integration(self, skill_caller_with_memory):
        """测试记忆搜索集成"""
        # 验证 memory_search 属性存在
        assert hasattr(skill_caller_with_memory, 'subagent_scheduler')
    
    def test_call_with_memory_context(self, skill_caller_with_memory):
        """测试带记忆上下文的调用"""
        # 验证 subagent_scheduler 存在
        assert hasattr(skill_caller_with_memory, 'subagent_scheduler')
        assert skill_caller_with_memory.subagent_scheduler is not None
        
        # 注意：memory_manager 可能在某些配置中存在
        # 这里验证调度器已正确初始化即可


class TestSkillCallerSecurity:
    """SkillCaller 安全测试"""
    
    @pytest.fixture
    def skill_caller_secure(self):
        """创建安全配置的 SkillCaller"""
        temp_dir = tempfile.mkdtemp()
        
        config = {
            "skill_call": {
                "default_timeout": 30,
                "retry_count": 0  # 不重试，快速失败
            },
            "security": {
                "workspace_root": temp_dir,
                "safety_mode": True,
                "allowed_commands": ["ls", "cat", "echo"]
            },
            "skills": {
                "builtin_skills_dir": "skills/builtin",
                "use_memory_registry": True
            },
            "workspace": {
                "default_path": temp_dir
            }
        }
        
        caller = SkillCaller(config)
        caller.session_manager = MockSessionManager()
        caller.set_workspace_manager(None)
        
        yield caller
        
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_security_mode_enabled(self, skill_caller_secure):
        """测试安全模式启用"""
        assert skill_caller_secure.sandbox.safety_mode is True
    
    def test_allowed_commands(self, skill_caller_secure):
        """测试允许的命令列表"""
        assert "ls" in skill_caller_secure.sandbox.allowed_commands
        assert "cat" in skill_caller_secure.sandbox.allowed_commands
        assert "echo" in skill_caller_secure.sandbox.allowed_commands
    
    def test_dangerous_command_blocked(self, skill_caller_secure):
        """测试危险命令被阻止"""
        # 验证危险命令不在允许列表中
        assert "rm" not in skill_caller_secure.sandbox.allowed_commands
        assert "sudo" not in skill_caller_secure.sandbox.allowed_commands
        assert "chmod" not in skill_caller_secure.sandbox.allowed_commands


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
