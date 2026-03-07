from __future__ import annotations

import logging
import sqlite3
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from contextlib import contextmanager

from pydantic_core.core_schema import nullable_schema
from lingxi.core.classifier import TaskClassifier
from lingxi.core.llm_client import LLMClient
from lingxi.context.manager import ContextManager, ContentType


def step_to_dict(step: Step) -> dict:
    """将 Step 对象转换为字典（用于数据库存储）"""
    return {
        "step_id": step.step_id,
        "task_id": step.task_id,
        "step_index": step.step_index,
        "step_type": step.step_type,
        "description": step.description,
        "status": step.status,
        "thought": step.thought,
        "result": step.result,
        "skill_call": step.skill_call,
        "created_at": step.created_at.isoformat() if step.created_at else None
    }


def dict_to_step(step_dict: dict) -> Step:
    """将字典转换为 Step 对象"""
    return Step(
        step_id=step_dict.get("step_id", ""),
        task_id=step_dict.get("task_id", ""),
        step_index=step_dict.get("step_index", 0),
        step_type=step_dict.get("step_type", "thinking"),
        description=step_dict.get("description", ""),
        status=step_dict.get("status", "completed"),
        thought=step_dict.get("thought", ""),
        result=step_dict.get("result", ""),
        skill_call=step_dict.get("skill_call", ""),
        created_at=datetime.fromisoformat(step_dict["created_at"]) if step_dict.get("created_at") else None
    )


def task_to_dict(task: Task) -> dict:
    """将 Task 对象转换为字典（用于数据库存储）"""
    return {
        "task_id": task.task_id,
        "session_id": task.session_id,
        "task_type": task.task_type,
        "plan": task.plan,
        "user_input": task.user_input,
        "result": task.result,
        "status": task.status,
        "current_step_idx": task.current_step_idx,
        "replan_count": task.replan_count,
        "error_info": task.error_info,
        "input_tokens": task.input_tokens,
        "output_tokens": task.output_tokens,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None
    }


def dict_to_task(task_dict: dict) -> Task:
    """将字典转换为 Task 对象"""
    return Task(
        task_id=task_dict.get("task_id", ""),
        session_id=task_dict.get("session_id", ""),
        task_type=task_dict.get("task_type", "simple"),
        plan=task_dict.get("plan", "[]"),
        user_input=task_dict.get("user_input", ""),
        result=task_dict.get("result", ""),
        status=task_dict.get("status", "running"),
        current_step_idx=task_dict.get("current_step_idx", 0),
        replan_count=task_dict.get("replan_count", 0),
        error_info=task_dict.get("error_info", ""),
        input_tokens=task_dict.get("input_tokens", 0),
        output_tokens=task_dict.get("output_tokens", 0),
        created_at=datetime.fromisoformat(task_dict["created_at"]) if task_dict.get("created_at") else None,
        updated_at=datetime.fromisoformat(task_dict["updated_at"]) if task_dict.get("updated_at") else None
    )


def session_to_dict(session: Session) -> dict:
    """将 Session 对象转换为字典（用于数据库存储）"""
    return {
        "session_id": session.session_id,
        "user_name": session.user_name,
        "title": session.title,
        "current_task_id": session.current_task_id,
        "total_tokens": session.total_tokens,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None
    }


def dict_to_session(session_dict: dict) -> Session:
    """将字典转换为 Session 对象"""
    return Session(
        session_id=session_dict.get("session_id", ""),
        user_name=session_dict.get("user_name", "default"),
        title=session_dict.get("title", "新会话"),
        current_task_id=session_dict.get("current_task_id", ""),
        total_tokens=session_dict.get("total_tokens", 0),
        created_at=datetime.fromisoformat(session_dict["created_at"]) if session_dict.get("created_at") else None,
        updated_at=datetime.fromisoformat(session_dict["updated_at"]) if session_dict.get("updated_at") else None
    )


@dataclass
class Step:
    """任务步骤实体类（使用dataclass）"""
    step_id: str
    task_id: str
    step_index: int = 0
    step_type: str = "thinking"
    description: str = ""
    status: str = "completed"
    thought: str = ""
    result: str = ""
    skill_call: str = ""
    created_at: datetime = datetime.now()


@dataclass
class Task:
    """任务实体类（使用dataclass）"""
    task_id: str
    session_id: str
    task_type: str = "simple"
    plan: str = "[]"
    user_input: str = ""
    result: str = ""
    status: str = "running"
    current_step_idx: int = 0
    replan_count: int = 0
    error_info: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()


@dataclass
class Session:
    """会话实体类（使用dataclass）"""
    session_id: str
    user_name: str = "default"
    title: str = "新会话"
    current_task_id: str = ""
    total_tokens: int = 0
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    
    def get_info(self):
        return f"{self.session_id}，{self.user_name}，{self.created_at}，{self.updated_at}"


class SessionManager:
    """会话管理器，实现SQLite存储、检查点功能和上下文管理"""

    def __init__(self, config: Dict[str, Any], session_id: str = "default"):
        """初始化会话管理器

        Args:
            config: 系统配置
            session_id: 会话ID
        """
        self.config = config
        self.session_id = session_id
        self.db_path = config.get("session", {}).get("db_path", "data/assistant.db")
        self.max_history_turns = config.get("session", {}).get("max_history_turns", 50)
        self.memory_cache = {}

        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"初始化会话管理器，数据库: {self.db_path}")

        self._init_db()

        self.context_manager = ContextManager(config, session_id)

    def _init_db(self):
        """初始化SQLite数据库"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        cursor = conn.cursor()
        
        # 检查并迁移旧表结构
        cursor.execute("PRAGMA table_info(sessions)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        # 如果表存在但缺少 title 列，添加该列
        if columns and 'title' not in columns:
            cursor.execute("ALTER TABLE sessions ADD COLUMN title TEXT NOT NULL DEFAULT '新会话'")
        
        # 如果表存在但缺少 current_task_id 列，添加该列
        if columns and 'current_task_id' not in columns:
            cursor.execute("ALTER TABLE sessions ADD COLUMN current_task_id TEXT")
        
        # 如果表存在但缺少 total_tokens 列，添加该列
        if columns and 'total_tokens' not in columns:
            cursor.execute("ALTER TABLE sessions ADD COLUMN total_tokens INTEGER NOT NULL DEFAULT 0")
        
        # 检查 tasks 表结构
        cursor.execute("PRAGMA table_info(tasks)")
        task_columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        # 如果 tasks 表存在但缺少 input_tokens 列，添加该列
        if task_columns and 'input_tokens' not in task_columns:
            cursor.execute("ALTER TABLE tasks ADD COLUMN input_tokens INTEGER NOT NULL DEFAULT 0")
        
        # 如果 tasks 表存在但缺少 output_tokens 列，添加该列
        if task_columns and 'output_tokens' not in task_columns:
            cursor.execute("ALTER TABLE tasks ADD COLUMN output_tokens INTEGER NOT NULL DEFAULT 0")
        
        # 如果 tasks 表存在但缺少 task_level 列，添加该列
        if task_columns and 'task_level' not in task_columns:
            cursor.execute("ALTER TABLE tasks ADD COLUMN task_level TEXT NOT NULL DEFAULT 'none'")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_name TEXT NOT NULL DEFAULT 'default',
                title TEXT NOT NULL DEFAULT '新会话',
                current_task_id TEXT,
                total_tokens INTEGER NOT NULL DEFAULT 0,
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
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_name ON sessions(user_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at DESC)")
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_session ON tasks(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_current_step ON tasks(current_step_idx)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_replan_count ON tasks(replan_count)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_input_tokens ON tasks(input_tokens)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_output_tokens ON tasks(output_tokens)")
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_steps_task ON steps(task_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_steps_status ON steps(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_steps_index ON steps(step_index)")
        
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA busy_timeout=5000;")
        cursor.execute("PRAGMA cache_size=-64000;")
        
        conn.commit()
        conn.close()
        
        self.logger.debug("数据库初始化完成，已启用WAL模式和并发优化配置")

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

    def _get_connection(self):
        """获取数据库连接（用于简单查询）

        Returns:
            数据库连接对象
        """
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _execute_sql(self, sql: str, params: tuple = None, fetch: bool = False) -> Optional[List[tuple]]:
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

    def get_history(self, session_id: str, max_turns: int = None) -> List[Dict[str, Any]]:
        """获取会话历史

        Args:
            session_id: 会话ID
            max_turns: 最大返回轮次

        Returns:
            会话历史记录（任务列表，包含步骤信息）
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT task_id, session_id, task_type, plan, user_input, result, 
                   status, current_step_idx, replan_count, error_info,
                   input_tokens, output_tokens, created_at, updated_at
            FROM tasks
            WHERE session_id = ?
            ORDER BY created_at DESC
        """, (session_id,))
        
        rows = cursor.fetchall()
        
        tasks = []
        for row in rows:
            task_dict = {
                "task_id": row[0],
                "session_id": row[1],
                "task_type": row[2],
                "plan": row[3],
                "user_input": row[4],
                "result": row[5],
                "status": row[6],
                "current_step_idx": row[7],
                "replan_count": row[8],
                "error_info": row[9],
                "input_tokens": row[10],
                "output_tokens": row[11],
                "created_at": row[12],
                "updated_at": row[13]
            }
            
            # 查询该任务的所有步骤
            cursor.execute("""
                SELECT step_id, task_id, step_index, step_type, description, 
                       thought, result, skill_call, status, created_at
                FROM steps
                WHERE task_id = ?
                ORDER BY step_index ASC
            """, (task_dict["task_id"],))
            
            step_rows = cursor.fetchall()
            steps = []
            for step_row in step_rows:
                step_dict = {
                    "step_id": step_row[0],
                    "task_id": step_row[1],
                    "step_index": step_row[2],
                    "step_type": step_row[3],
                    "description": step_row[4],
                    "thought": step_row[5],
                    "result": step_row[6],
                    "skill_call": step_row[7],
                    "status": step_row[8],
                    "created_at": step_row[9]
                }
                steps.append(step_dict)
            
            task_dict["steps"] = steps
            tasks.append(task_dict)
        
        conn.close()
        
        if max_turns and len(tasks) > max_turns:
            tasks = tasks[:max_turns]
        
        return tasks

    def create_task(self, session_id: str, task_id: str, task_type: str, user_input: str = "", task_level: str = "none") -> str:
        """创建新任务

        Args:
            session_id: 会话ID
            task_id: 任务ID
            task_type: 任务类型
            user_input: 用户输入
            task_level: 任务级别

        Returns:
            任务ID
        """
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tasks 
                (task_id, session_id, task_type, task_level, user_input, status, current_step_idx, replan_count, 
                 input_tokens, output_tokens, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'running', 0, 0, 0, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (task_id, session_id, task_type, task_level, user_input))
        
        self.logger.debug(f"任务已创建，session_id: {session_id}, task_id: {task_id}, task_type: {task_type}, task_level: {task_level}")
        
        return task_id

    def get_task(self, session_id: str, task_id: str) -> Optional[Task]:
        """获取任务

        Args:
            session_id: 会话ID
            task_id: 任务ID

        Returns:
            任务实体类
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT task_id, session_id, task_type, plan, user_input, result, 
                   status, current_step_idx, replan_count, error_info,
                   input_tokens, output_tokens, created_at, updated_at
            FROM tasks
            WHERE task_id = ?
        """, (task_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict_to_task({
                "task_id": row[0],
                "session_id": row[1],
                "task_type": row[2],
                "plan": row[3],
                "user_input": row[4],
                "result": row[5],
                "status": row[6],
                "current_step_idx": row[7],
                "replan_count": row[8],
                "error_info": row[9],
                "input_tokens": row[10],
                "output_tokens": row[11],
                "created_at": row[12],
                "updated_at": row[13]
            })
        
        return None
        
    def add_step(self, session_id: str, task_id: str, step_index: int, result: str, status: str = None, thought: str = None, action: str = None, action_input: str = None, description: str = None):
        """添加任务步骤

        Args:
            session_id: 会话ID
            task_id: 任务ID
            step_index: 步骤索引
            result: 步骤结果（字符串格式）
            thought: 思考过程
            action: 执行行动
            action_input: 行动输入
            description: 步骤描述
        """
        with self.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO steps 
                (step_id, task_id, step_index, step_type, description, thought, result, skill_call, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                f"{task_id}_step_{step_index}",
                task_id,
                step_index,
                action or "unknown",
                description or "",
                thought or "",
                result,
                action or "",
                status or "completed"
            ))
        
        self.logger.debug(f"步骤已添加，session_id: {session_id}, task_id: {task_id}, step_index: {step_index}")

    def set_task_result(self, session_id: str, task_id: str, result: str = None ,user_input: str = None, status: str = None):
        """设置任务结果

        Args:
            session_id: 会话 ID
            task_id: 任务 ID
            result: 任务结果
            user_input: 用户输入
            status: 任务状态
        """
        if result is not None or user_input is not None or status is not None:
            update_fields = []
            update_values = []
            
            if result is not None:
                update_fields.append("result = ?")
                update_values.append(result)
            
            if user_input is not None:
                update_fields.append("user_input = ?")
                update_values.append(user_input)
            
            if status is not None:
                update_fields.append("status = ?")
                update_values.append(status)
            
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            update_values.append(task_id)
            
            sql = f"""
                UPDATE tasks SET {', '.join(update_fields)}
                WHERE task_id = ?
            """
            self._execute_sql(sql, tuple(update_values))
        
        self.logger.debug(f"任务结果已保存，session_id: {session_id}, task_id: {task_id}")

    def update_task_tokens(self, task_id: str, input_tokens: int, output_tokens: int):
        """更新任务 Token 数量

        Args:
            task_id: 任务ID
            input_tokens: 输入 Token 数量
            output_tokens: 输出 Token 数量
        """
        sql = """
            UPDATE tasks 
            SET input_tokens = input_tokens + ?, 
                output_tokens = output_tokens + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
        """
        self._execute_sql(sql, (input_tokens, output_tokens, task_id))
        self.logger.debug(f"任务 Token 已更新，task_id: {task_id}, input_tokens: {input_tokens}, output_tokens: {output_tokens}")

    def get_task_tokens(self, task_id: str) -> dict:
        """获取任务 Token 数量

        Args:
            task_id: 任务ID

        Returns:
            Token 数量字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT input_tokens, output_tokens FROM tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "input_tokens": row[0] or 0,
                "output_tokens": row[1] or 0,
                "total_tokens": (row[0] or 0) + (row[1] or 0)
            }
        return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    def update_session_tokens(self, session_id: str, input_tokens: int, output_tokens: int):
        """更新会话 Token 总数

        Args:
            session_id: 会话ID
            input_tokens: 输入 Token 数量
            output_tokens: 输出 Token 数量
        """
        sql = """
            UPDATE sessions 
            SET total_tokens = total_tokens + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """
        self._execute_sql(sql, (input_tokens + output_tokens, session_id))
        self.logger.debug(f"会话 Token 已更新，session_id: {session_id}, tokens: {input_tokens + output_tokens}")
    
    def save_plan(self, session_id: str, task_id: str, plan: str):
        """保存任务计划

        Args:
            session_id: 会话ID
            task_id: 任务ID
            plan: 任务计划（JSON字符串）
        """
        sql = """
            UPDATE tasks SET plan = ?, updated_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
        """
        self._execute_sql(sql, (plan, task_id))
        
        self.logger.debug(f"任务计划已保存，session_id: {session_id}, task_id: {task_id}")


    def restore_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """恢复任务执行

        Args:
            task_id: 任务ID

        Returns:
            任务恢复信息，如果任务不存在则返回None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT task_id, session_id, task_type, plan, user_input, result, 
                   status, current_step_idx, replan_count, error_info,
                   input_tokens, output_tokens, created_at, updated_at
            FROM tasks
            WHERE task_id = ?
        """, (task_id,))
        
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return None
        
        task_info = {
            "task_id": row[0],
            "session_id": row[1],
            "task_type": row[2],
            "plan": row[3],
            "user_input": row[4],
            "result": row[5],
            "status": row[6],
            "current_step_idx": row[7],
            "replan_count": row[8],
            "error_info": row[9],
            "input_tokens": row[10],
            "output_tokens": row[11],
            "created_at": row[12],
            "updated_at": row[13]
        }
        
        current_idx = task_info.get("current_step_idx", 0)
        
        cursor.execute("""
            SELECT step_id, task_id, step_index, step_type, description, thought, result, skill_call, status, created_at
            FROM steps
            WHERE task_id = ? AND step_index < ?
            ORDER BY step_index ASC
        """, (task_id, current_idx))
        
        rows = cursor.fetchall()
        completed_steps = []
        for step_row in rows:
            completed_steps.append({
                "step_id": step_row[0],
                "task_id": step_row[1],
                "step_index": step_row[2],
                "step_type": step_row[3],
                "description": step_row[4],
                "thought": step_row[5],
                "result": step_row[6],
                "skill_call": step_row[7],
                "status": step_row[8],
                "created_at": step_row[9]
            })
        
        conn.close()
        
        plan = []
        if task_info.get("plan"):
            try:
                plan = json.loads(task_info["plan"])
            except json.JSONDecodeError:
                plan = []
        
        remaining_plan = plan[current_idx:]
        
        return {
            "task_id": task_id,
            "session_id": task_info["session_id"],
            "task_type": task_info["task_type"],
            "user_input": task_info["user_input"],
            "remaining_plan": remaining_plan,
            "current_step_idx": current_idx,
            "execution_status": task_info["status"],
            "completed_steps": completed_steps,
            "replan_count": task_info.get("replan_count", 0),
            "error_info": task_info.get("error_info"),
            "input_tokens": task_info.get("input_tokens", 0),
            "output_tokens": task_info.get("output_tokens", 0)
        }

    def update_task_progress(self, task_id: str, step_index: int):
        """更新任务进度

        Args:
            task_id: 任务ID
            step_index: 当前步骤索引
        """
        sql = """
            UPDATE tasks SET current_step_idx = ?, updated_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
        """
        self._execute_sql(sql, (step_index, task_id))

    def increment_replan_count(self, task_id: str):
        """增加重规划次数

        Args:
            task_id: 任务ID
        """
        sql = """
            UPDATE tasks SET replan_count = replan_count + 1, updated_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
        """
        self._execute_sql(sql, (task_id,))

    def set_task_error(self, task_id: str, error_info: str):
        """设置任务错误

        Args:
            task_id: 任务ID
            error_info: 错误信息
        """
        sql = """
            UPDATE tasks SET status = 'failed', error_info = ?, updated_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
        """
        self._execute_sql(sql, (error_info, task_id))

    def _save_to_db(self, session_id: str, history: List[Dict[str, Any]]):
        """保存会话历史到数据库（已废弃，保留向后兼容）"""
        pass

    def _save_task_list_to_db(self, session_id: str, task_list: Dict[str, Any]):
        """保存任务列表到数据库（已废弃，保留向后兼容）"""
        pass

    def save_checkpoint(self, session_id: str, state: Dict[str, Any]):
        """保存执行检查点

        Args:
            session_id: 会话ID
            state: 检查点状态
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sessions 
            SET checkpoint_json = ?, updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """, (json.dumps(state, ensure_ascii=False), session_id))
        conn.commit()
        conn.close()

    def restore_checkpoint(self, session_id: str) -> Optional[Dict[str, Any]]:
        """恢复检查点

        Args:
            session_id: 会话ID

        Returns:
            检查点状态，如果不存在则返回None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT checkpoint_json FROM sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        conn.close()

        if row and row[0]:
            return json.loads(row[0])
        return None

    def clear_session(self, session_id: str):
        """清空会话（包括所有任务和步骤）

        Args:
            session_id: 会话ID
        """
        if session_id in self.memory_cache:
            del self.memory_cache[session_id]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        
        conn.commit()
        conn.close()
        
        self.logger.debug(f"会话已清空，session_id: {session_id}")

    def clear_session_history(self, session_id: str):
        """清除会话历史记录（删除所有任务和步骤），但保留会话本身

        Args:
            session_id: 会话ID
        """
        if session_id in self.memory_cache:
            del self.memory_cache[session_id]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT task_id FROM tasks WHERE session_id = ?", (session_id,))
        task_ids = [row[0] for row in cursor.fetchall()]
        
        for task_id in task_ids:
            cursor.execute("DELETE FROM steps WHERE task_id = ?", (task_id,))
        
        cursor.execute("DELETE FROM tasks WHERE session_id = ?", (session_id,))
        
        cursor.execute("""
            UPDATE sessions SET current_task_id = NULL, total_tokens = 0, checkpoint_json = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """, (session_id,))
        
        conn.commit()
        conn.close()
        
        self.logger.debug(f"会话历史已清空，session_id: {session_id}，删除了 {len(task_ids)} 个任务")

    def get_checkpoint_status(self, session_id: str) -> Dict[str, Any]:
        """获取检查点状态信息

        Args:
            session_id: 会话ID

        Returns:
            检查点状态信息
        """
        checkpoint = self.restore_checkpoint(session_id)
        if not checkpoint:
            return {"has_checkpoint": False}

        return {
            "has_checkpoint": True,
            "task": checkpoint.get("task"),
            "current_step": checkpoint.get("current_step_idx", 0),
            "total_steps": len(checkpoint.get("plan", [])),
            "execution_status": checkpoint.get("execution_status"),
            "replan_count": checkpoint.get("replan_count", 0),
            "timestamp": checkpoint.get("timestamp"),
            "error_info": checkpoint.get("error_info")
        }

    def clear_checkpoint(self, session_id: str):
        """清除指定会话的检查点

        Args:
            session_id: 会话ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sessions SET checkpoint_json = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """, (session_id,))
        conn.commit()
        conn.close()

    def cleanup_expired_checkpoints(self, ttl_hours: int = 24) -> int:
        """清理过期的检查点

        Args:
            ttl_hours: 生存时间（小时）

        Returns:
            清理的检查点数量
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT session_id, checkpoint_json, updated_at FROM sessions")
        sessions = cursor.fetchall()

        current_time = time.time()
        ttl_seconds = ttl_hours * 3600
        cleaned_count = 0

        for session_id, checkpoint_json, updated_at in sessions:
            if checkpoint_json:
                try:
                    checkpoint = json.loads(checkpoint_json)
                    checkpoint_time = checkpoint.get("timestamp", updated_at)

                    if current_time - checkpoint_time > ttl_seconds:
                        cursor.execute("""
                            UPDATE sessions SET checkpoint_json = NULL, updated_at = CURRENT_TIMESTAMP
                            WHERE session_id = ?
                        """, (session_id,))
                        cleaned_count += 1
                        self.logger.debug(f"清除过期检查点：{session_id}")
                except Exception as e:
                    self.logger.error(f"处理检查点{session_id}时出错：{e}")

        conn.commit()
        conn.close()

        if cleaned_count > 0:
            self.logger.debug(f"清理了{cleaned_count}个过期检查点")

        return cleaned_count

    def list_active_checkpoints(self) -> List[Dict[str, Any]]:
        """列出所有活跃的检查点

        Returns:
            检查点列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT session_id, checkpoint_json, updated_at
            FROM sessions
            WHERE checkpoint_json IS NOT NULL
        """)
        rows = cursor.fetchall()
        conn.close()

        checkpoints = []
        for session_id, checkpoint_json, updated_at in rows:
            try:
                checkpoint = json.loads(checkpoint_json)
                checkpoints.append({
                    "session_id": session_id,
                    "task": checkpoint.get("task"),
                    "current_step": checkpoint.get("current_step_idx", 0),
                    "total_steps": len(checkpoint.get("plan", [])),
                    "execution_status": checkpoint.get("execution_status"),
                    "updated_at": updated_at
                })
            except Exception as e:
                self.logger.error(f"解析检查点{session_id}时出错：{e}")

        return checkpoints

    def process_input(self, user_input: str, session_id: str = "default") -> str:
        """处理用户输入（简化版，仅用于测试）

        Args:
            user_input: 用户输入
            session_id: 会话ID

        Returns:
            响应
        """
        
        classifier = TaskClassifier(self.config)
        history = self.get_history(session_id)
        task_info = classifier.classify(user_input, history)

        response = f"任务级别: {task_info['level']}\n置信度: {task_info['confidence']}\n理由: {task_info['reason']}"

        return response

    def get_context_for_llm(self) -> List[Dict[str, str]]:
        """获取发送给LLM的上下文

        Returns:
            上下文列表
        """
        return self.context_manager.get_context_for_llm()

    def get_context_stats(self) -> Dict[str, Any]:
        """获取上下文统计信息

        Returns:
            统计信息
        """
        return self.context_manager.get_stats()

    def set_current_task(self, task_id: str):
        """设置当前任务ID

        Args:
            task_id: 任务ID
        """
        self.context_manager.set_current_task(task_id)

    def compress_context(self, strategy: str = None) -> Dict[str, Any]:
        """手动触发上下文压缩

        Args:
            strategy: 压缩策略

        Returns:
            压缩统计信息
        """
        return self.context_manager.compress(strategy)

    def retrieve_relevant_history(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """检索相关历史记忆

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            相关历史记录
        """
        return self.context_manager.retrieve_relevant_history(query, top_k)

    def list_all_sessions(self) -> List[Dict[str, Any]]:
        """列出所有会话

        Returns:
            会话列表，包含session_id、创建时间、更新时间、消息数量等信息
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.session_id, s.title, s.created_at, s.updated_at, COUNT(t.task_id) as task_count
            FROM sessions s
            LEFT JOIN tasks t ON s.session_id = t.session_id
            GROUP BY s.session_id
            ORDER BY s.updated_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()

        sessions = []
        for session_id, title, created_at, updated_at, task_count in rows:
            try:
                # 获取该会话的第一条用户消息
                cursor = sqlite3.connect(self.db_path)
                c = cursor.cursor()
                c.execute("""
                    SELECT user_input FROM tasks
                    WHERE session_id = ? AND user_input IS NOT NULL
                    ORDER BY created_at ASC
                    LIMIT 1
                """, (session_id,))
                first_message_row = c.fetchone()
                first_message = first_message_row[0][:50] if first_message_row and first_message_row[0] else ""
                cursor.close()
                
                sessions.append({
                    "session_id": session_id,
                    "title": title,
                    "message_count": task_count,
                    "first_message": first_message,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "has_checkpoint": False
                })
            except Exception as e:
                self.logger.error(f"解析会话{session_id}时出错：{e}")

        return sessions
    
    

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话详细信息

        Args:
            session_id: 会话ID

        Returns:
            会话信息
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT session_id, title, total_tokens, checkpoint_json, created_at, updated_at
            FROM sessions
            WHERE session_id = ?
        """, (session_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        session_id, title, total_tokens, checkpoint_json, created_at, updated_at = row
        
        # 获取该会话的所有任务
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT task_id, task_type, task_level, plan, user_input, result, status, created_at, updated_at
            FROM tasks
            WHERE session_id = ?
            ORDER BY created_at ASC
        """, (session_id,))
        task_rows = cursor.fetchall()
        
        # 组装任务列表
        task_list = []
        for task_row in task_rows:
            task_id, task_type, task_level, plan, user_input, result, status, task_created_at, task_updated_at = task_row
            
            # 查询该任务的所有步骤
            cursor.execute("""
                SELECT step_id, task_id, step_index, step_type, description, 
                       thought, result, skill_call, status, created_at
                FROM steps
                WHERE task_id = ?
                ORDER BY step_index ASC
            """, (task_id,))
            
            step_rows = cursor.fetchall()
            steps = []
            for step_row in step_rows:
                step_dict = {
                    "step_id": step_row[0],
                    "task_id": step_row[1],
                    "step_index": step_row[2],
                    "step_type": step_row[3],
                    "description": step_row[4],
                    "thought": step_row[5],
                    "result": step_row[6],
                    "skill_call": step_row[7],
                    "status": step_row[8],
                    "created_at": step_row[9]
                }
                steps.append(step_dict)
            
            task_list.append({
                "task_id": task_id,
                "task_type": task_type,
                "task_level": task_level,
                "plan": plan,
                "user_input": user_input,
                "result": result,
                "status": status,
                "created_at": task_created_at,
                "updated_at": task_updated_at,
                "steps": steps
            })
        
        conn.close()

        return {
            "session_id": session_id,
            "title": title,
            "task_count": len(task_list),
            "task_list": task_list,
            "total_tokens": total_tokens,
            "created_at": created_at,
            "updated_at": updated_at,
            "has_checkpoint": checkpoint_json is not None
        }

    def rename_session(self, session_id: str, new_title: str) -> bool:
        """重命名会话

        Args:
            session_id: 会话ID
            new_title: 新标题

        Returns:
            是否成功
        """
        # 确保会话在缓存中
        if session_id not in self.memory_cache:
            self.memory_cache[session_id] = Session(session_id=session_id)

        # 更新缓存中的标题
        self.memory_cache[session_id].title = new_title

        # 更新数据库中的标题
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sessions SET title = ?, updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """, (new_title, session_id))
        conn.commit()
        conn.close()

        return True

    def delete_session(self, session_id: str) -> bool:
        """删除会话

        Args:
            session_id: 会话ID

        Returns:
            是否成功
        """
        if session_id in self.memory_cache:
            del self.memory_cache[session_id]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return deleted

    def create_session(self, user_name: str = "default") -> str:
        """创建新会话

        Args:
            user_name: 用户名

        Returns:
            会话ID
        """
        import uuid
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        # 确保user_name不是None
        user_name = user_name if user_name is not None else "default"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sessions (session_id, user_name, title, total_tokens)
            VALUES (?, ?, ?, ?)
        """, (session_id, user_name, "新会话", 0))
        conn.commit()
        conn.close()
        
        self.memory_cache[session_id] = Session(session_id=session_id, user_name=user_name, title="新会话")
        return session_id

    def create_session_by_id(self, session_id: str, user_name: str = "default") -> str:
        """使用指定的 session_id 创建新会话

        Args:
            session_id: 会话 ID
            user_name: 用户名

        Returns:
            会话 ID
        """
        # 确保 user_name 不是 None
        user_name = user_name if user_name is not None else "default"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sessions (session_id, user_name, title, total_tokens)
            VALUES (?, ?, ?, ?)
        """, (session_id, user_name, "新会话", 0))
        conn.commit()
        conn.close()
        
        self.memory_cache[session_id] = Session(session_id=session_id, user_name=user_name, title="新会话")
        self.logger.debug(f"会话已创建，session_id: {session_id}")
        return session_id
