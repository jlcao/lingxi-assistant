"""工作目录注册表

负责工作目录的登记、查询和会话关联管理
"""

import logging
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

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
    """工作目录注册表（基于 db_path 的多实例模式）
    
    使用类级别的实例缓存，每个 db_path 对应一个实例。
    这样既保持了单例的优点（同一数据库共享连接），又支持测试隔离。
    """

    _instances: Dict[str, 'WorkspaceRegistry'] = {}

    def __new__(cls, db_path: str):
        """基于 db_path 的实例缓存"""
        # 规范化路径以确保一致性
        normalized_path = str(Path(db_path).resolve())
        
        if normalized_path not in cls._instances:
            cls._instances[normalized_path] = super().__new__(cls)
        return cls._instances[normalized_path]

    def __init__(self, db_path: str):
        """初始化工作目录注册表

        Args:
            db_path: 数据库文件路径
        """
        # 规范化路径
        normalized_path = str(Path(db_path).resolve())
        
        # 防止重复初始化
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.db_path = normalized_path
        self._connection_cache: Optional[sqlite3.Connection] = None

        # 执行数据库迁移
        self._migrate_database()

        self._initialized = True
        logger.debug(f"WorkspaceRegistry 初始化完成，数据库：{db_path}")

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
        """关闭数据库连接并从实例缓存中移除"""
        if self._connection_cache:
            self._connection_cache.close()
            self._connection_cache = None
        
        # 从实例缓存中移除
        if self.db_path in WorkspaceRegistry._instances:
            del WorkspaceRegistry._instances[self.db_path]
        
        self._initialized = False
        logger.debug("WorkspaceRegistry 数据库连接已关闭，实例已移除")

    @classmethod
    def clear_instances(cls):
        """清除所有实例缓存（用于测试）"""
        for instance in cls._instances.values():
            if instance._connection_cache:
                instance._connection_cache.close()
        cls._instances.clear()
        logger.debug("WorkspaceRegistry 所有实例缓存已清除")
