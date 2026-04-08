#!/usr/bin/env python3
"""Tasks API 路由单元测试"""

import pytest
import sys
import os
import tempfile
import shutil
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient
from lingxi.web.fastapi_server import app


class TestTasksRoute:
    """Tasks API 路由测试"""
    
    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)
    
    def test_tasks_route_exists(self, client):
        """测试 tasks 路由存在"""
        response = client.options("/api/tasks/execute")
        assert response.status_code != 404
    
    def test_execute_task_sync_mode(self, client):
        """测试同步模式执行任务"""
        response = client.post(
            "/api/tasks/execute",
            json={
                "task": "hello",
                "session_id": "test_session",
                "async_mode": False
            }
        )
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert "code" in data
            assert "message" in data
    
    def test_execute_task_async_mode(self, client):
        """测试异步模式执行任务"""
        response = client.post(
            "/api/tasks/execute",
            json={
                "task": "hello",
                "session_id": "test_session_async",
                "async_mode": True
            }
        )
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert "code" in data
            assert "message" in data
            if data.get("code") == 0:
                assert "data" in data
                task_data = data.get("data", {})
                assert "sessionId" in task_data
                assert "taskId" in task_data
                assert "status" in task_data
    
    def test_task_status_endpoint_exists(self, client):
        """测试任务状态查询端点存在"""
        response = client.options("/api/tasks/test_task_id/status")
        assert response.status_code != 404
    
    def test_get_task_status_nonexistent(self, client):
        """测试查询不存在的任务状态"""
        response = client.get("/api/tasks/nonexistent_task_id/status")
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert "code" in data
