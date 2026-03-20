from __future__ import annotations

import logging
import sqlite3
import time
from contextlib import contextmanager
from typing import Optional, List, Any, Dict
from lingxi.utils.config import get_config


class DatabaseManager:
    """数据库管理器，负责数据库连接、事务管理和初始化"""
    _instance = None  # 单例实例
    def __new__(cls):
        """单例模式：确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化数据库管理器

        Args:
            db_path: 数据库文件路径
            logger: 日志记录器
        """
        self.config = get_config()
        self.db_path = self.config.get("session", {}).get("db_path", "data/assistant.db")
        self.logger = logging.getLogger(__name__)
        self._init_db()
        self._initialized = True

    def _init_db(self):
        """初始化SQLite数据库"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = conn.cursor()

        self._migrate_sessions_table(cursor)
        self._migrate_tasks_table(cursor)
        self._migrate_steps_table(cursor)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_name TEXT NOT NULL DEFAULT 'default',
                title TEXT NOT NULL DEFAULT '新会话',
                current_task_id TEXT,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                checkpoint_json TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                task_type TEXT NOT NULL,
                task_level TEXT NOT NULL DEFAULT 'none',
                plan TEXT,
                user_input TEXT,
                result TEXT,
                status TEXT NOT NULL DEFAULT 'running',
                current_step_idx INTEGER NOT NULL DEFAULT 0,
                replan_count INTEGER NOT NULL DEFAULT 0,
                error_info TEXT,
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS steps (
                step_id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                step_index INTEGER NOT NULL DEFAULT 0,
                step_type TEXT NOT NULL,
                description TEXT,
                thought TEXT,
                result TEXT,
                skill_call TEXT,
                status TEXT NOT NULL DEFAULT 'completed',
                result_description TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
            )
        """)

        self._create_indexes(cursor)
        self._configure_performance(cursor)

        conn.commit()
        conn.close()

        self.logger.debug(f"数据库初始化完成，路径: {self.db_path}")

    def update_db_path(self, new_db_path: str):
        """更新数据库路径（用于工作区切换）

        Args:
            new_db_path: 新的数据库路径
        """
        self.db_path = new_db_path
        self._init_db()
        self.logger.info(f"数据库路径已更新：{new_db_path}")

    def _migrate_sessions_table(self, cursor: sqlite3.Cursor):
        """迁移 sessions 表结构"""
        cursor.execute("PRAGMA table_info(sessions)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        migrations = [
            ('title', "ALTER TABLE sessions ADD COLUMN title TEXT NOT NULL DEFAULT '新会话'"),
            ('current_task_id', "ALTER TABLE sessions ADD COLUMN current_task_id TEXT"),
            ('total_tokens', "ALTER TABLE sessions ADD COLUMN total_tokens INTEGER NOT NULL DEFAULT 0"),
            ('checkpoint_json', "ALTER TABLE sessions ADD COLUMN checkpoint_json TEXT")
        ]

        for column, sql in migrations:
            if columns and column not in columns:
                cursor.execute(sql)

    def _migrate_tasks_table(self, cursor: sqlite3.Cursor):
        """迁移 tasks 表结构"""
        cursor.execute("PRAGMA table_info(tasks)")
        task_columns = {row[1]: row[2] for row in cursor.fetchall()}

        migrations = [
            ('input_tokens', "ALTER TABLE tasks ADD COLUMN input_tokens INTEGER NOT NULL DEFAULT 0"),
            ('output_tokens', "ALTER TABLE tasks ADD COLUMN output_tokens INTEGER NOT NULL DEFAULT 0"),
            ('task_level', "ALTER TABLE tasks ADD COLUMN task_level TEXT NOT NULL DEFAULT 'none'")
        ]

        for column, sql in migrations:
            if task_columns and column not in task_columns:
                cursor.execute(sql)

    def _migrate_steps_table(self, cursor: sqlite3.Cursor):
        """迁移 steps 表结构"""
        cursor.execute("PRAGMA table_info(steps)")
        step_columns = {row[1]: row[2] for row in cursor.fetchall()}

        migrations = [
            ('result_description', "ALTER TABLE steps ADD COLUMN result_description TEXT")
        ]

        for column, sql in migrations:
            if step_columns and column not in step_columns:
                cursor.execute(sql)

    def _create_indexes(self, cursor: sqlite3.Cursor):
        """创建数据库索引"""
        session_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_sessions_user_name ON sessions(user_name)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at DESC)"
        ]

        task_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_tasks_session ON tasks(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_current_step ON tasks(current_step_idx)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_replan_count ON tasks(replan_count)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_input_tokens ON tasks(input_tokens)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_output_tokens ON tasks(output_tokens)"
        ]

        step_indexes = [
            "CREATE INDEX IF NOT EXISTS idx_steps_task ON steps(task_id)",
            "CREATE INDEX IF NOT EXISTS idx_steps_status ON steps(status)",
            "CREATE INDEX IF NOT EXISTS idx_steps_index ON steps(step_index)"
        ]

        for sql in session_indexes + task_indexes + step_indexes:
            cursor.execute(sql)

    def _configure_performance(self, cursor: sqlite3.Cursor):
        """配置数据库性能参数"""
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=5000;")
        cursor.execute("PRAGMA cache_size=-64000;")

    @contextmanager
    def transaction(self):
        """事务上下文管理器，带重试机制

        Yields:
            数据库连接对象

        Raises:
            sqlite3.OperationalError: 数据库操作失败且重试次数用尽
        """
        max_retries = 3
        base_delay = 0.1

        conn = sqlite3.connect(self.db_path, check_same_thread=False)

        try:
            for attempt in range(max_retries):
                try:
                    yield conn
                    conn.commit()
                    return
                except sqlite3.OperationalError as e:
                    if "database is locked" in str(e) and attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        self.logger.warning(f"数据库锁定，第{attempt + 1}次重试，等待{delay:.2f}秒")
                        time.sleep(delay)
                        continue
                    conn.rollback()
                    raise
        finally:
            conn.close()

    def get_connection(self):
        """获取数据库连接（用于简单查询）

        Returns:
            数据库连接对象
        """
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def execute_sql(self, sql: str, params: tuple = None, fetch: bool = False) -> Optional[List[tuple]]:
        """执行SQL语句（使用事务上下文管理器）

        Args:
            sql: SQL语句
            params: SQL参数
            fetch: 是否返回查询结果

        Returns:
            查询结果列表（如果fetch=True），否则返回None
        """
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params or ())
            if fetch:
                return cursor.fetchall()
            return None
