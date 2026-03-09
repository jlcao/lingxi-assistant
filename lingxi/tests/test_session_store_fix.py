"""测试工作区切换时 session_store 是否正确设置"""

import pytest
import tempfile
import shutil
from pathlib import Path
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from lingxi.core.async_main import AsyncLingxiAssistant
from lingxi.management.workspace import WorkspaceManager


class TestSessionStoreFix:
    """测试 session_store 修复"""
    
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
        
        # 创建配置文件
        config_file = lingxi_dir / "conf" / "config.yml"
        config_file.write_text("workspace_name: workspace1\n", encoding='utf-8')
        
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
        
        # 创建配置文件
        config_file = lingxi_dir / "conf" / "config.yml"
        config_file.write_text("workspace_name: workspace2\n", encoding='utf-8')
        
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
            },
            "system": {
                "name": "灵犀助手",
                "version": "0.2.0"
            }
        }
    
    def test_session_store_set_in_init(self, config):
        """测试在 __init__ 中 session_store 是否被设置"""
        print("\n=== 测试 1: BaseAssistant.__init__ 中的修复 ===")
        
        assistant = AsyncLingxiAssistant(config)
        
        # 检查 skill_caller 是否有 workspace_manager
        assert hasattr(assistant.skill_caller, 'workspace_manager'), "skill_caller 应该有 workspace_manager"
        
        workspace_manager = assistant.skill_caller.workspace_manager
        
        # 检查 session_store 是否被设置
        print(f"workspace_manager.session_store: {workspace_manager.session_store}")
        print(f"assistant.session_manager: {assistant.session_manager}")
        print(f"是否相同：{workspace_manager.session_store is assistant.session_manager}")
        
        assert workspace_manager.session_store is not None, "session_store 应该被设置"
        assert workspace_manager.session_store is assistant.session_manager, "session_store 应该是 assistant.session_manager"
        
        print("PASS: 测试 1 通过：session_store 在 __init__ 中被正确设置")
    
    def test_session_store_after_switch(self, temp_workspace1, temp_workspace2, config):
        """测试切换工作区后 session_store 是否仍然有效"""
        print("\n=== 测试 2: 切换工作区后的 session_store ===")
        
        # 创建助手
        assistant = AsyncLingxiAssistant(config)
        workspace_manager = assistant.skill_caller.workspace_manager
        
        # 初始化第一个工作区
        print(f"初始化工作区 1: {temp_workspace1}")
        assistant.initialize(str(temp_workspace1))
        
        # 检查 session_store
        print(f"工作区 1 - session_store: {workspace_manager.session_store}")
        assert workspace_manager.session_store is not None, "工作区 1 的 session_store 应该被设置"
        
        # 在工作区 1 创建会话
        session_id = "test_session_1"
        assistant.session_manager.create_session_by_id(session_id, "Workspace 1 Session")
        
        sessions = assistant.session_manager.list_all_sessions()
        print(f"工作区 1 的会话数：{len(sessions)}")
        assert len(sessions) == 1, f"工作区 1 应该有 1 个会话，但有 {len(sessions)} 个"
        
        # 切换到工作区 2
        print(f"切换到工作区 2: {temp_workspace2}")
        import asyncio
        asyncio.run(workspace_manager.switch_workspace(str(temp_workspace2)))
        
        # 检查切换后的 session_store
        print(f"切换后 - session_store: {workspace_manager.session_store}")
        print(f"切换后 - session_store 是否为 None: {workspace_manager.session_store is None}")
        
        # 这是关键的修复点：切换后 session_store 应该仍然有效
        assert workspace_manager.session_store is not None, "切换后 session_store 应该仍然被设置"
        assert workspace_manager.session_store is assistant.session_manager, "切换后 session_store 应该仍然是 assistant.session_manager"
        
        # 验证工作区 2 的会话是空的
        sessions_after_switch = assistant.session_manager.list_all_sessions()
        print(f"工作区 2 的会话数：{len(sessions_after_switch)}")
        assert len(sessions_after_switch) == 0, f"工作区 2 应该是空的，但有 {len(sessions_after_switch)} 个会话"
        
        print("✅ 测试 2 通过：切换工作区后 session_store 仍然有效")
    
    def test_workspace_isolation(self, temp_workspace1, temp_workspace2, config):
        """测试工作区之间的会话隔离"""
        print("\n=== 测试 3: 工作区会话隔离 ===")
        
        assistant = AsyncLingxiAssistant(config)
        workspace_manager = assistant.skill_caller.workspace_manager
        
        # 初始化工作区 1
        assistant.initialize(str(temp_workspace1))
        
        # 在工作区 1 创建会话
        session1_id = "ws1_session"
        assistant.session_manager.create_session_by_id(session1_id, "Workspace 1 Session")
        
        # 切换到工作区 2
        import asyncio
        asyncio.run(workspace_manager.switch_workspace(str(temp_workspace2)))
        
        # 在工作区 2 创建会话
        session2_id = "ws2_session"
        assistant.session_manager.create_session_by_id(session2_id, "Workspace 2 Session")
        
        # 验证工作区 2 只有自己的会话
        sessions_in_ws2 = assistant.session_manager.list_all_sessions()
        print(f"工作区 2 的会话：{[s['session_id'] for s in sessions_in_ws2]}")
        assert len(sessions_in_ws2) == 1
        assert sessions_in_ws2[0]['session_id'] == session2_id
        
        # 切换回工作区 1
        asyncio.run(workspace_manager.switch_workspace(str(temp_workspace1)))
        
        # 验证工作区 1 只有自己的会话
        sessions_in_ws1 = assistant.session_manager.list_all_sessions()
        print(f"工作区 1 的会话：{[s['session_id'] for s in sessions_in_ws1]}")
        assert len(sessions_in_ws1) == 1
        assert sessions_in_ws1[0]['session_id'] == session1_id
        
        print("✅ 测试 3 通过：工作区之间会话正确隔离")


if __name__ == "__main__":
    # 允许直接运行测试
    pytest.main([__file__, "-v", "-s"])
