#!/usr/bin/env python3
"""测试数据库路径是否固定为用户目录下面的 .lingxi/data/lingxi.db"""

from pathlib import Path
from lingxi.core.session.database_manager import DatabaseManager
from lingxi.core.session.session_manager import SessionManager
from lingxi.management.workspace_manager import get_workspace_manager
from lingxi.utils.config import get_config

print("测试数据库路径固定功能")
print("=" * 50)

# 获取用户目录
user_home = Path.home()
fixed_db_path = str(user_home / ".lingxi" / "data" / "lingxi.db")
print(f"预期数据库路径: {fixed_db_path}")

# 测试 DatabaseManager
print("\n测试 DatabaseManager:")
db_manager = DatabaseManager()
print(f"DatabaseManager 数据库路径: {db_manager.db_path}")
if db_manager.db_path == fixed_db_path:
    print("✅ DatabaseManager 数据库路径正确")
else:
    print("❌ DatabaseManager 数据库路径错误")

# 测试 SessionManager
print("\n测试 SessionManager:")
session_manager = SessionManager()
print(f"SessionManager 数据库路径: {session_manager.db_path}")
if session_manager.db_path == fixed_db_path:
    print("✅ SessionManager 数据库路径正确")
else:
    print("❌ SessionManager 数据库路径错误")

# 测试 WorkspaceManager
print("\n测试 WorkspaceManager:")
workspace_manager = get_workspace_manager()
print("WorkspaceManager 初始化完成")

print("\n测试完成！")
