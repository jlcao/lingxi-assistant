#!/usr/bin/env python3
"""子代理调度器测试"""

import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lingxi.core.subagent import SubAgentScheduler, SubAgentTask


class MockSessionManager:
    """模拟 SessionManager"""
    def create_session(self, session_id=None, workspace_path=None):
        class Session:
            id = session_id
        return Session()


class MockSkillCaller:
    """模拟 SkillCaller"""
    pass


class TestSubAgentScheduler:
    """子代理调度器测试"""
    
    @pytest.fixture
    def scheduler(self):
        config = {
            "max_concurrent": 5,
            "default_timeout": 300
        }
        return SubAgentScheduler(
            session_manager=MockSessionManager(),
            skill_caller=MockSkillCaller(),
            config=config
        )
    
    def test_init(self, scheduler):
        """测试初始化"""
        assert scheduler.max_concurrent == 5
        assert scheduler.default_timeout == 300
        assert len(scheduler.active_tasks) == 0
    
    def test_spawn(self, scheduler):
        """测试 spawn 子代理"""
        async def run_test():
            task_id = await scheduler.spawn(
                task="测试任务",
                workspace_path="/tmp"
            )
            assert task_id is not None
            assert len(scheduler.active_tasks) == 1
        
        asyncio.run(run_test())
    
    def test_get_task(self, scheduler):
        """测试获取任务"""
        async def run_test():
            task_id = await scheduler.spawn(task="测试任务")
            task = scheduler.get_task(task_id)
            assert task is not None
            assert task.status == "pending"
        
        asyncio.run(run_test())
    
    def test_list_tasks(self, scheduler):
        """测试列出任务"""
        async def run_test():
            await scheduler.spawn(task="任务 1")
            await scheduler.spawn(task="任务 2")
            await scheduler.spawn(task="任务 3")
            
            tasks = scheduler.list_tasks()
            assert len(tasks) == 3
        
        asyncio.run(run_test())
    
    def test_task_to_dict(self, scheduler):
        """测试任务转换为字典"""
        async def run_test():
            task_id = await scheduler.spawn(task="测试任务")
            task = scheduler.get_task(task_id)
            task_dict = task.to_dict()
            
            assert "id" in task_dict
            assert "task" in task_dict
            assert "status" in task_dict
            assert "created_at" in task_dict
        
        asyncio.run(run_test())
    
    def test_get_task_progress(self, scheduler):
        """测试获取任务进度"""
        async def run_test():
            task_id = await scheduler.spawn(task="测试任务")
            
            # 获取进度
            progress = scheduler.get_task_progress(task_id)
            
            assert progress is not None
            assert "task_id" in progress
            assert "status" in progress
            assert "progress" in progress
            assert "current_step" in progress
        
        asyncio.run(run_test())
    
    def test_event_publisher_initialized(self, scheduler):
        """测试事件发布器已初始化"""
        assert scheduler.event_publisher is not None
        assert hasattr(scheduler, 'event_publisher')


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
