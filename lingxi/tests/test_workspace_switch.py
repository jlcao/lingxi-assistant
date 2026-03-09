"""工作区切换测试模块

测试工作区切换后会话数据是否正确隔离
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any
import os

from lingxi.management.workspace import WorkspaceManager, WorkspaceError
from lingxi.core.session import SessionManager


class TestWorkspaceSwitch:
    """工作区切换测试类"""
    
    @pytest.fixture
    def temp_workspace1(self, tmp_path):
        """创建第一个临时工作区"""
        workspace_dir = tmp_path / "workspace1"
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化 .lingxi 目录
        lingxi_dir = workspace_dir / ".lingxi"
        lingxi_dir.mkdir(parents=True, exist_ok=True)
        (lingxi_dir / "conf").mkdir(exist_ok=True)
        (lingxi_dir / "data").mkdir(exist_ok=True)
        (lingxi_dir / "skills").mkdir(exist_ok=True)
        
        yield workspace_dir
        
        # 清理
        if workspace_dir.exists():
            shutil.rmtree(workspace_dir)
    
    @pytest.fixture
    def temp_workspace2(self, tmp_path):
        """创建第二个临时工作区"""
        workspace_dir = tmp_path / "workspace2"
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化 .lingxi 目录
        lingxi_dir = workspace_dir / ".lingxi"
        lingxi_dir.mkdir(parents=True, exist_ok=True)
        (lingxi_dir / "conf").mkdir(exist_ok=True)
        (lingxi_dir / "data").mkdir(exist_ok=True)
        (lingxi_dir / "skills").mkdir(exist_ok=True)
        
        yield workspace_dir
        
        # 清理
        if workspace_dir.exists():
            shutil.rmtree(workspace_dir)
    
    @pytest.fixture
    def config(self):
        """创建测试配置"""
        return {
            "session": {
                "db_path": "data/assistant.db",
                "memory_db": "data/long_term_memory.db",
                "max_history_turns": 50
            },
            "llm": {
                "default_model": "test-model"
            }
        }
    
    @pytest.fixture
    def session_manager(self, config):
        """创建 SessionManager 实例"""
        return SessionManager(config)
    
    def test_workspace_switch_isolates_sessions(self, temp_workspace1, temp_workspace2, config):
        """测试工作区切换后会话数据隔离"""
        
        # 1. 初始化 WorkspaceManager
        workspace_manager = WorkspaceManager(config)
        
        # 2. 创建一个全局的 SessionManager（模拟应用启动时的初始化）
        # 注意：这里使用默认配置，db_path 是相对路径
        global_session_manager = SessionManager(config)
        workspace_manager.set_resources(session_store=global_session_manager)
        
        # 3. 初始化第一个工作区
        workspace_manager.initialize(str(temp_workspace1))
        
        # 4. 初始化数据库（这会设置正确的数据库路径并创建表结构）
        data_dir = temp_workspace1 / ".lingxi" / "data"
        workspace_manager._initialize_database(data_dir)
        
        # 5. 在 workspace1 中创建会话
        session1_id = "session_ws1_001"
        global_session_manager.create_session_by_id(session1_id, "Workspace1 Session 1")
        
        # 6. 验证 workspace1 中有会话
        sessions_in_ws1 = global_session_manager.list_all_sessions()
        assert len(sessions_in_ws1) == 1, f"workspace1 应该有 1 个会话，但有 {len(sessions_in_ws1)} 个"
        assert sessions_in_ws1[0]["session_id"] == session1_id
        
        # 6. 切换到第二个工作区
        import asyncio
        asyncio.run(workspace_manager.switch_workspace(str(temp_workspace2)))
        
        # 7. 验证 session_manager 的数据库路径已更新
        expected_db_path = str(temp_workspace2 / ".lingxi" / "data" / "assistant.db")
        assert global_session_manager.db_path == expected_db_path
        
        # 8. 验证 workspace2 中没有会话（空的）
        sessions_in_ws2 = global_session_manager.list_all_sessions()
        assert len(sessions_in_ws2) == 0, f"切换工作区后应该没有会话，但找到了 {len(sessions_in_ws2)} 个会话"
        
        # 9. 在 workspace2 中创建新会话
        session2_id = "session_ws2_001"
        global_session_manager.create_session_by_id(session2_id, "Workspace2 Session 1")
        
        # 10. 验证 workspace2 中有且仅有自己的会话
        sessions_in_ws2_after = global_session_manager.list_all_sessions()
        assert len(sessions_in_ws2_after) == 1
        assert sessions_in_ws2_after[0]["session_id"] == session2_id
        
        # 11. 再次切换回 workspace1
        asyncio.run(workspace_manager.switch_workspace(str(temp_workspace1)))
        
        # 12. 验证 session_manager 的数据库路径已更新回 workspace1
        expected_db_path_ws1 = str(temp_workspace1 / ".lingxi" / "data" / "assistant.db")
        assert global_session_manager.db_path == expected_db_path_ws1
        
        # 13. 验证 workspace1 中仍然有自己的会话
        sessions_in_ws1_final = global_session_manager.list_all_sessions()
        assert len(sessions_in_ws1_final) == 1
        assert sessions_in_ws1_final[0]["session_id"] == session1_id
        assert sessions_in_ws1_final[0]["title"] == "Workspace1 Session 1"
        
        print("✅ 所有测试通过！工作区切换后会话数据正确隔离")
    
    def test_workspace_database_path_update(self, temp_workspace1, temp_workspace2, config):
        """测试工作区切换时数据库路径正确更新"""
        
        # 1. 初始化 WorkspaceManager
        workspace_manager = WorkspaceManager(config)
        
        # 2. 创建 SessionManager 并设置到 workspace_manager
        session_manager = SessionManager(config)
        workspace_manager.set_resources(session_store=session_manager)
        
        # 3. 初始化第一个工作区
        workspace_manager.initialize(str(temp_workspace1))
        
        # 4. 验证初始数据库路径
        initial_db_path = session_manager.db_path
        expected_ws1_db = str(temp_workspace1 / ".lingxi" / "data" / "assistant.db")
        assert initial_db_path == expected_ws1_db
        
        # 5. 切换到第二个工作区
        import asyncio
        asyncio.run(workspace_manager.switch_workspace(str(temp_workspace2)))
        
        # 6. 验证数据库路径已更新
        updated_db_path = session_manager.db_path
        expected_ws2_db = str(temp_workspace2 / ".lingxi" / "data" / "assistant.db")
        assert updated_db_path == expected_ws2_db
        assert updated_db_path != initial_db_path
        
        print("✅ 数据库路径更新测试通过！")


if __name__ == "__main__":
    # 允许直接运行测试
    pytest.main([__file__, "-v", "-s"])
