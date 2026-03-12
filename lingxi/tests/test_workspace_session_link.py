"""工作目录与会话关联测试"""

import pytest
import sqlite3
import os
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from lingxi.core.session.database_migration import (
    migrate_database,
    get_or_create_workspace,
    update_session_workspace,
    get_sessions_by_workspace,
    get_workspace_by_path,
    list_all_workspaces
)
from lingxi.core.session.workspace_registry import WorkspaceRegistry


class TestDatabaseMigration:
    """数据库迁移测试"""

    @pytest.fixture
    def test_db(self, tmp_path):
        """创建测试数据库"""
        db_path = tmp_path / "test_assistant.db"
        # 执行迁移
        success = migrate_database(str(db_path))
        assert success, "数据库迁移失败"
        yield str(db_path)
        # 清理
        if db_path.exists():
            db_path.unlink()

    def test_migrate_database(self, test_db):
        """测试数据库迁移"""
        conn = sqlite3.connect(test_db)
        cursor = conn.cursor()

        # 检查 workspaces 表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='workspaces'")
        assert cursor.fetchone() is not None, "workspaces 表未创建"

        # 检查 sessions 表的 workspace_id 字段
        cursor.execute("PRAGMA table_info(sessions)")
        columns = {row[1] for row in cursor.fetchall()}
        assert 'workspace_id' in columns, "sessions 表缺少 workspace_id 字段"

        conn.close()

    def test_get_or_create_workspace(self, test_db):
        """测试获取或创建工作目录"""
        conn = sqlite3.connect(test_db)

        # 创建新工作目录
        workspace_id = get_or_create_workspace(conn, "/test/workspace1", "测试工作目录 1")
        assert workspace_id > 0, "工作目录 ID 应该大于 0"

        # 再次获取同一工作目录（应该返回相同 ID）
        workspace_id_2 = get_or_create_workspace(conn, "/test/workspace1", "测试工作目录 1")
        assert workspace_id_2 == workspace_id, "同一工作目录应该返回相同 ID"

        conn.close()

    def test_update_session_workspace(self, test_db):
        """测试更新会话工作目录关联"""
        conn = sqlite3.connect(test_db)

        # 创建工作目录
        workspace_id = get_or_create_workspace(conn, "/test/workspace1")

        # 创建测试会话
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sessions (session_id, user_name, title, created_at, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, ("test_session_1", "test_user", "测试会话"))
        conn.commit()

        # 关联会话和工作目录
        success = update_session_workspace(conn, "test_session_1", workspace_id)
        assert success, "关联失败"

        # 验证关联
        cursor.execute("SELECT workspace_id FROM sessions WHERE session_id = ?", ("test_session_1",))
        row = cursor.fetchone()
        assert row[0] == workspace_id, "会话工作目录关联不正确"

        conn.close()

    def test_get_sessions_by_workspace(self, test_db):
        """测试获取工作目录的会话列表"""
        conn = sqlite3.connect(test_db)

        # 创建工作目录
        workspace_id = get_or_create_workspace(conn, "/test/workspace1")

        # 创建多个会话并关联
        for i in range(3):
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (session_id, user_name, title, created_at, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (f"test_session_{i}", "test_user", f"测试会话{i}"))
            conn.commit()

            update_session_workspace(conn, f"test_session_{i}", workspace_id)

        # 获取会话列表
        sessions = get_sessions_by_workspace(conn, workspace_id)
        assert len(sessions) == 3, f"应该返回 3 个会话，实际返回{len(sessions)}个"

        conn.close()

    def test_list_all_workspaces(self, test_db):
        """测试列出所有工作目录"""
        conn = sqlite3.connect(test_db)

        # 创建多个工作目录
        for i in range(3):
            get_or_create_workspace(conn, f"/test/workspace{i}", f"测试工作目录{i}")

        # 获取所有工作目录
        workspaces = list_all_workspaces(conn)
        assert len(workspaces) == 3, f"应该返回 3 个工作目录，实际返回{len(workspaces)}个"

        conn.close()


class TestWorkspaceRegistry:
    """工作目录注册表测试"""

    @pytest.fixture
    def test_registry(self, tmp_path):
        """创建测试注册表"""
        db_path = tmp_path / "test_assistant.db"
        registry = WorkspaceRegistry(str(db_path))
        yield registry
        # 清理
        registry.close()
        if db_path.exists():
            db_path.unlink()

    def test_register_workspace(self, test_registry):
        """测试登记工作目录"""
        workspace_id = test_registry.register_workspace("/test/workspace1", "测试工作目录 1")
        assert workspace_id > 0, "工作目录 ID 应该大于 0"

    def test_get_workspace_by_path(self, test_registry):
        """测试根据路径获取工作目录"""
        # 先登记
        test_registry.register_workspace("/test/workspace1", "测试工作目录 1")

        # 获取
        workspace = test_registry.get_workspace_by_path("/test/workspace1")
        assert workspace is not None, "工作目录应该存在"
        assert workspace['name'] == "测试工作目录 1", "工作目录名称不正确"

    def test_get_workspace_by_path_not_found(self, test_registry):
        """测试获取不存在的工作目录"""
        workspace = test_registry.get_workspace_by_path("/nonexistent/workspace")
        assert workspace is None, "不存在的工作目录应该返回 None"

    def test_associate_session_with_workspace(self, test_registry):
        """测试会话与工作目录关联"""
        # 登记工作目录
        workspace_id = test_registry.register_workspace("/test/workspace1")

        # 创建测试会话（直接操作数据库）
        conn = test_registry._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sessions (session_id, user_name, title, created_at, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, ("test_session_1", "test_user", "测试会话"))
        conn.commit()

        # 关联
        success = test_registry.associate_session_with_workspace("test_session_1", "/test/workspace1")
        assert success, "关联失败"

    def test_get_sessions_by_workspace_path(self, test_registry):
        """测试根据工作目录路径获取会话"""
        # 登记工作目录
        test_registry.register_workspace("/test/workspace1")

        # 创建并关联会话
        conn = test_registry._get_connection()
        for i in range(2):
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (session_id, user_name, title, created_at, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (f"test_session_{i}", "test_user", f"测试会话{i}"))
            conn.commit()

            test_registry.associate_session_with_workspace(f"test_session_{i}", "/test/workspace1")

        # 获取会话列表
        sessions = test_registry.get_sessions_by_workspace_path("/test/workspace1")
        assert len(sessions) == 2, f"应该返回 2 个会话，实际返回{len(sessions)}个"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
