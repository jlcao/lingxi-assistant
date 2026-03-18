"""数据库迁移脚本 - 添加工作目录关联功能

迁移内容：
1. 创建 workspaces 表（工作目录登记表）
2. 修改 sessions 表，添加 workspace_id 外键
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def migrate_database(db_path: str) -> bool:
    """执行数据库迁移

    Args:
        db_path: 数据库文件路径

    Returns:
        迁移是否成功
    """
    try:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        cursor = conn.cursor()

        # 启用外键支持
        cursor.execute("PRAGMA foreign_keys = ON;")

        # 1. 创建 workspaces 表
        _create_workspaces_table(cursor)

        # 2. 修改 sessions 表，添加 workspace_id 字段
        _add_workspace_id_to_sessions(cursor)

        # 3. 修改 steps 表，添加 result_description 字段
        _add_result_description_to_steps(cursor)

        # 4. 创建索引
        _create_migration_indexes(cursor)

        conn.commit()
        logger.info(f"数据库迁移完成：{db_path}")
        return True

    except Exception as e:
        logger.error(f"数据库迁移失败：{e}")
        return False

    finally:
        conn.close()


def _create_workspaces_table(cursor: sqlite3.Cursor):
    """创建 workspaces 表

    表结构：
    - id: 主键
    - workspace_path: 工作目录绝对路径（唯一）
    - name: 工作目录名称（可选）
    - created_at: 创建时间
    - updated_at: 更新时间
    """
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workspaces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workspace_path TEXT NOT NULL UNIQUE,
            name TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    logger.debug("workspaces 表创建完成")


def _add_workspace_id_to_sessions(cursor: sqlite3.Cursor):
    """修改 sessions 表，添加 workspace_id 外键

    SQLite 不支持直接添加外键约束，需要：
    1. 检查 sessions 表是否存在
    2. 如果不存在，先创建 sessions 表
    3. 检查 workspace_id 字段是否已存在
    4. 添加 workspace_id 字段（不帶外键约束，SQLite 限制）
    """
    # 检查 sessions 表是否存在
    cursor.execute("""
        SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'
    """)
    table_exists = cursor.fetchone() is not None

    if not table_exists:
        # sessions 表不存在，先创建基础表结构
        logger.info("sessions 表不存在，创建基础表结构")
        cursor.execute("""
            CREATE TABLE sessions (
                session_id TEXT PRIMARY KEY,
                user_name TEXT NOT NULL DEFAULT 'user',
                title TEXT NOT NULL DEFAULT '新会话',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                workspace_id INTEGER
            )
        """)
        logger.debug("sessions 表创建完成")
    else:
        # sessions 表已存在，检查 workspace_id 字段是否已存在
        cursor.execute("PRAGMA table_info(sessions)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        if 'workspace_id' in columns:
            logger.debug("workspace_id 字段已存在，跳过迁移")
            return

        # 添加 workspace_id 字段（不帶外键约束，SQLite 限制）
        cursor.execute("""
            ALTER TABLE sessions ADD COLUMN workspace_id INTEGER
        """)
        logger.debug("sessions 表 workspace_id 字段添加完成")

    # 添加外键约束的索引
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_sessions_workspace_id ON sessions(workspace_id)
    """)
    logger.debug("sessions 表索引创建完成")


def _add_result_description_to_steps(cursor: sqlite3.Cursor):
    """修改 steps 表，添加 result_description 字段"""
    # 检查 steps 表是否存在
    cursor.execute("""
        SELECT name FROM sqlite_master WHERE type='table' AND name='steps'
    """)
    table_exists = cursor.fetchone() is not None

    if not table_exists:
        # steps 表不存在，不需要迁移（会在 database_manager 中创建）
        return

    # 检查 result_description 字段是否已存在
    cursor.execute("PRAGMA table_info(steps)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}

    if 'result_description' in columns:
        logger.debug("result_description 字段已存在，跳过迁移")
        return

    # 添加 result_description 字段
    cursor.execute("""
        ALTER TABLE steps ADD COLUMN result_description TEXT
    """)
    logger.debug("steps 表 result_description 字段添加完成")


def _create_migration_indexes(cursor: sqlite3.Cursor):
    """创建迁移相关的索引"""
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_workspaces_path ON workspaces(workspace_path)",
        "CREATE INDEX IF NOT EXISTS idx_sessions_workspace ON sessions(workspace_id)"
    ]

    for sql in indexes:
        cursor.execute(sql)

    logger.debug("迁移索引创建完成")


def get_or_create_workspace(conn: sqlite3.Connection, workspace_path: str, name: Optional[str] = None) -> int:
    """获取或创建工作目录记录

    Args:
        conn: 数据库连接
        workspace_path: 工作目录路径
        name: 工作目录名称（可选）

    Returns:
        工作目录 ID
    """
    cursor = conn.cursor()

    # 尝试获取现有记录
    cursor.execute("""
        SELECT id FROM workspaces WHERE workspace_path = ?
    """, (workspace_path,))

    row = cursor.fetchone()
    if row:
        logger.debug(f"工作目录已存在：{workspace_path}, id={row[0]}")
        return row[0]

    # 创建新记录
    cursor.execute("""
        INSERT INTO workspaces (workspace_path, name, created_at, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """, (workspace_path, name))

    workspace_id = cursor.lastrowid
    conn.commit()

    logger.info(f"工作目录已登记：{workspace_path}, id={workspace_id}")
    return workspace_id


def update_session_workspace(conn: sqlite3.Connection, session_id: str, workspace_id: int) -> bool:
    """更新会话的工作目录关联

    Args:
        conn: 数据库连接
        session_id: 会话 ID
        workspace_id: 工作目录 ID

    Returns:
        是否成功
    """
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE sessions SET workspace_id = ?, updated_at = CURRENT_TIMESTAMP
        WHERE session_id = ?
    """, (workspace_id, session_id))

    updated = cursor.rowcount > 0
    conn.commit()

    if updated:
        logger.debug(f"会话工作目录已更新：session={session_id}, workspace={workspace_id}")
    else:
        logger.warning(f"会话不存在，无法更新工作目录：{session_id}")

    return updated


def get_sessions_by_workspace(conn: sqlite3.Connection, workspace_id: int) -> list:
    """获取指定工作目录的所有会话

    Args:
        conn: 数据库连接
        workspace_id: 工作目录 ID

    Returns:
        会话列表
    """
    cursor = conn.cursor()

    cursor.execute("""
        SELECT session_id, title, created_at, updated_at, total_tokens
        FROM sessions
        WHERE workspace_id = ?
        ORDER BY updated_at DESC
    """, (workspace_id,))

    rows = cursor.fetchall()

    sessions = []
    for row in rows:
        sessions.append({
            "session_id": row[0],
            "title": row[1],
            "created_at": row[2],
            "updated_at": row[3],
            "total_tokens": row[4],
            "workspace_id": workspace_id
        })

    logger.debug(f"获取工作目录 {workspace_id} 的会话列表，共 {len(sessions)} 个")
    return sessions


def get_workspace_by_path(conn: sqlite3.Connection, workspace_path: str) -> Optional[dict]:
    """根据路径获取工作目录信息

    Args:
        conn: 数据库连接
        workspace_path: 工作目录路径

    Returns:
        工作目录信息，不存在则返回 None
    """
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, workspace_path, name, created_at, updated_at
        FROM workspaces
        WHERE workspace_path = ?
    """, (workspace_path,))

    row = cursor.fetchone()

    if row:
        return {
            "id": row[0],
            "workspace_path": row[1],
            "name": row[2],
            "created_at": row[3],
            "updated_at": row[4]
        }

    return None


def list_all_workspaces(conn: sqlite3.Connection) -> list:
    """列出所有工作目录

    Args:
        conn: 数据库连接

    Returns:
        工作目录列表
    """
    cursor = conn.cursor()

    cursor.execute("""
        SELECT w.id, w.workspace_path, w.name, w.created_at, w.updated_at,
               COUNT(s.session_id) as session_count
        FROM workspaces w
        LEFT JOIN sessions s ON w.id = s.workspace_id
        GROUP BY w.id
        ORDER BY w.updated_at DESC
    """)

    rows = cursor.fetchall()

    workspaces = []
    for row in rows:
        workspaces.append({
            "id": row[0],
            "workspace_path": row[1],
            "name": row[2],
            "created_at": row[3],
            "updated_at": row[4],
            "session_count": row[5]
        })

    logger.debug(f"获取所有工作目录，共 {len(workspaces)} 个")
    return workspaces
