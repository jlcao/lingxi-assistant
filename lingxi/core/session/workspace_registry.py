"""工作目录注册表

负责工作目录的登记、查询和会话关联管理
"""

import logging
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from lingxi.utils.config import get_config



from .database_migration import (
    migrate_database,
    get_or_create_workspace,
    update_session_workspace,
    get_sessions_by_workspace,
    get_workspace_by_path,
    list_all_workspaces
)

logger = logging.getLogger(__name__)


class WorkspaceRegistry:
    """工作目录注册表（单例模式）
    
    使用单例模式，确保整个应用只创建一个实例。
    """

    _instance: 'WorkspaceRegistry' = None

    def __new__(cls):
        """单例模式：确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化工作目录注册表

        Args:
            db_path: 数据库文件路径
        """
        # 使用固定的数据库路径：用户目录下面的 .lingxi/data/lingxi.db
        from pathlib import Path
        user_home = Path.home()
        self.db_path = str(user_home / ".lingxi" / "data" / "lingxi.db")
        # 规范化路径
        normalized_path = str(Path(self.db_path).resolve())
        
        # 防止重复初始化
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.db_path = normalized_path
        # 确保数据库目录存在
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        self._connection_cache: Optional[sqlite3.Connection] = None

        # 执行数据库迁移
        self._migrate_database()

        self._initialized = True
        logger.debug(f"WorkspaceRegistry 初始化完成，数据库：{self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接（缓存连接）

        Returns:
            数据库连接对象
        """
        if self._connection_cache is None:
            self._connection_cache = sqlite3.connect(self.db_path, check_same_thread=False)
            # 启用外键支持
            self._connection_cache.execute("PRAGMA foreign_keys = ON;")

        return self._connection_cache

    def _migrate_database(self):
        """执行数据库迁移"""
        try:
            # 检查数据库文件是否存在
            db_file = Path(self.db_path)
            if not db_file.exists():
                # 新数据库，直接创建表结构，跳过迁移
                logger.info(f"新数据库，直接创建表结构：{self.db_path}")
                conn = sqlite3.connect(self.db_path, check_same_thread=False)
                cursor = conn.cursor()
                
                # 启用外键支持
                cursor.execute("PRAGMA foreign_keys = ON;")
                
                # 创建 workspaces 表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS workspaces (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        workspace_path TEXT NOT NULL UNIQUE,
                        name TEXT,
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 创建 sessions 表
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        user_name TEXT NOT NULL DEFAULT 'user',
                        title TEXT NOT NULL DEFAULT '新会话',
                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        total_tokens INTEGER NOT NULL DEFAULT 0,
                        workspace_id INTEGER
                    )
                """)
                
                # 创建索引
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_workspace_id ON sessions(workspace_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_workspaces_path ON workspaces(workspace_path)")
                
                conn.commit()
                conn.close()
                logger.info(f"数据库表结构创建完成：{self.db_path}")
            else:
                # 现有数据库，执行迁移
                success = migrate_database(self.db_path)
                if success:
                    logger.info(f"数据库迁移成功：{self.db_path}")
                else:
                    logger.error(f"数据库迁移失败：{self.db_path}")
        except Exception as e:
            logger.error(f"数据库迁移异常：{e}")

    def register_workspace(self, workspace_path: str, name: Optional[str] = None) -> int:
        """登记工作目录

        Args:
            workspace_path: 工作目录路径
            name: 工作目录名称（可选）

        Returns:
            工作目录 ID
        """
        conn = self._get_connection()
        workspace_id = get_or_create_workspace(conn, workspace_path, name)
        logger.info(f"工作目录已登记：{workspace_path} (id={workspace_id})")
        return workspace_id

    def get_workspace_by_path(self, workspace_path: str) -> Optional[Dict[str, Any]]:
        """根据路径获取工作目录信息

        Args:
            workspace_path: 工作目录路径

        Returns:
            工作目录信息，不存在则返回 None
        """
        conn = self._get_connection()
        return get_workspace_by_path(conn, workspace_path)

    def get_current_workspace_id(self, workspace_path: str) -> int:
        """获取当前工作目录 ID（不存在则创建）

        Args:
            workspace_path: 工作目录路径

        Returns:
            工作目录 ID
        """
        return self.register_workspace(workspace_path)

    def update_session_workspace(self, session_id: str, workspace_id: int) -> bool:
        """更新会话的工作目录关联

        Args:
            session_id: 会话 ID
            workspace_id: 工作目录 ID

        Returns:
            是否成功
        """
        conn = self._get_connection()
        return update_session_workspace(conn, session_id, workspace_id)

    def get_sessions_by_workspace(self, workspace_id: int) -> List[Dict[str, Any]]:
        """获取指定工作目录的所有会话

        Args:
            workspace_id: 工作目录 ID

        Returns:
            会话列表
        """
        conn = self._get_connection()
        return get_sessions_by_workspace(conn, workspace_id)

    def get_sessions_by_workspace_path(self, workspace_path: str) -> List[Dict[str, Any]]:
        """根据工作目录路径获取会话列表

        Args:
            workspace_path: 工作目录路径

        Returns:
            会话列表
        """
        workspace = self.get_workspace_by_path(workspace_path)
        if not workspace:
            logger.warning(f"工作目录不存在：{workspace_path}")
            return []

        return self.get_sessions_by_workspace(workspace['id'])

    def list_all_workspaces(self) -> List[Dict[str, Any]]:
        """列出所有工作目录

        Returns:
            工作目录列表
        """
        conn = self._get_connection()
        return list_all_workspaces(conn)

    def associate_session_with_workspace(self, session_id: str, workspace_path: str) -> bool:
        """将会话与工作目录关联

        Args:
            session_id: 会话 ID
            workspace_path: 工作目录路径

        Returns:
            是否成功
        """
        workspace_id = self.get_current_workspace_id(workspace_path)
        return self.update_session_workspace(session_id, workspace_id)

    def close(self):
        """关闭数据库连接"""
        if self._connection_cache:
            self._connection_cache.close()
            self._connection_cache = None
        
        # 清除单例实例
        WorkspaceRegistry._instance = None
        self._initialized = False
        logger.debug("WorkspaceRegistry 数据库连接已关闭，实例已清除")

    @classmethod
    def clear_instances(cls):
        """清除单例实例（用于测试）"""
        if cls._instance and cls._instance._connection_cache:
            cls._instance._connection_cache.close()
        cls._instance = None
        logger.debug("WorkspaceRegistry 单例实例已清除")
