from __future__ import annotations

import json
import logging
import sqlite3
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from lingxi.core.session.session_models import Task
from lingxi.core.session.step_manager import StepManager
from lingxi.core.session.database_manager import DatabaseManager


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


class TaskManager:
    """任务管理器，负责任务的增删改查和状态管理"""
    _instance = None  # 单例实例

    def __new__(cls):
        """单例模式：确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化任务管理器

        Args:
            db_manager: 数据库管理器实例
            step_manager: 步骤管理器实例
            logger: 日志记录器
        """
        self.db_manager = DatabaseManager()
        self.step_manager = StepManager()
        self.logger = logging.getLogger(__name__)
        self._initialized = True

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
        with self.db_manager.transaction() as conn:
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
        conn = self.db_manager.get_connection()
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

    def set_task_result(self, session_id: str, task_id: str, result: str = None, user_input: str = None, status: str = None):
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

            sql = f"UPDATE tasks SET {', '.join(update_fields)} WHERE task_id = ?"
            self.db_manager.execute_sql(sql, tuple(update_values))

            self.logger.debug(f"任务结果已更新，task_id: {task_id}")

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
        self.db_manager.execute_sql(sql, (input_tokens, output_tokens, task_id))

        self.logger.debug(f"任务 Token 已更新，task_id: {task_id}, input_tokens: {input_tokens}, output_tokens: {output_tokens}")

    def get_task_tokens(self, task_id: str) -> dict:
        """获取任务的 Token 使用情况

        Args:
            task_id: 任务ID

        Returns:
            Token 使用情况字典
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT input_tokens, output_tokens FROM tasks WHERE task_id = ?
        """, (task_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "input_tokens": row[0],
                "output_tokens": row[1],
                "total_tokens": row[0] + row[1]
            }

        return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

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
        self.db_manager.execute_sql(sql, (plan, task_id))

        self.logger.debug(f"任务计划已保存，session_id: {session_id}, task_id: {task_id}")

    def restore_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """恢复任务状态

        Args:
            task_id: 任务ID

        Returns:
            任务状态字典
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT task_id, session_id, task_type, plan, user_input, result, status,
                   current_step_idx, replan_count, error_info, input_tokens, output_tokens
            FROM tasks
            WHERE task_id = ?
        """, (task_id,))

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        task_info = {
            "task_id": row[0],
            "session_id": row[1],
            "task_type": row[2],
            "user_input": row[4],
            "result": row[5],
            "status": row[6],
            "current_step_idx": row[7],
            "replan_count": row[8],
            "error_info": row[9],
            "input_tokens": row[10],
            "output_tokens": row[11]
        }

        current_idx = task_info["current_step_idx"]
        completed_steps = self.step_manager.get_completed_steps(task_id, current_idx)

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
            step_index: 步骤索引
        """
        sql = """
            UPDATE tasks SET current_step_idx = ?, updated_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
        """
        self.db_manager.execute_sql(sql, (step_index, task_id))

        self.logger.debug(f"任务进度已更新，task_id: {task_id}, step_index: {step_index}")

    def increment_replan_count(self, task_id: str):
        """增加重新规划次数

        Args:
            task_id: 任务ID
        """
        sql = """
            UPDATE tasks SET replan_count = replan_count + 1, updated_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
        """
        self.db_manager.execute_sql(sql, (task_id,))

        self.logger.debug(f"重新规划次数已增加，task_id: {task_id}")

    def set_task_error(self, task_id: str, error_info: str):
        """设置任务错误信息

        Args:
            task_id: 任务ID
            error_info: 错误信息
        """
        sql = """
            UPDATE tasks SET error_info = ?, status = 'failed', updated_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
        """
        self.db_manager.execute_sql(sql, (error_info, task_id))

        self.logger.debug(f"任务错误已设置，task_id: {task_id}, error: {error_info}")

    def get_tasks_by_session(self, session_id: str) -> List[Task]:
        """获取会话的所有任务

        Args:
            session_id: 会话ID

        Returns:
            任务列表
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT task_id, session_id, task_type, task_level, plan, user_input, result, 
                   status, current_step_idx, replan_count, error_info,
                   input_tokens, output_tokens, created_at, updated_at
            FROM tasks
            WHERE session_id = ?
            ORDER BY created_at ASC
        """, (session_id,))

        rows = cursor.fetchall()
        conn.close()

        tasks: List[Task] = []
        for row in rows:
            task = dict_to_task(task_dict = {
                "task_id": row[0],
                "session_id": row[1],
                "task_type": row[2],
                "task_level": row[3],
                "plan": row[4],
                "user_input": row[5],
                "result": row[6],
                "status": row[7],
                "current_step_idx": row[8],
                "replan_count": row[9],
                "error_info": row[10],
                "input_tokens": row[11],
                "output_tokens": row[12],
                "created_at": row[13],
                "updated_at": row[14]
            })
            task.steps = self.step_manager.get_steps(row[0])
            tasks.append(task)
        return tasks

    def get_tasks_by_session_for_frontend(self, session_id: str):
        """获取会话的所有任务

        Args:
            session_id: 会话ID

        Returns:
            任务列表
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT task_id, session_id, task_type, task_level, plan, user_input, result, 
                   status, current_step_idx, replan_count, error_info,
                   input_tokens, output_tokens, created_at, updated_at
            FROM tasks
            WHERE session_id = ?
            ORDER BY created_at ASC
        """, (session_id,))

        rows = cursor.fetchall()
        conn.close()

        tasks = []
        for row in rows:
            # 处理时间戳，确保返回数字类型的时间戳（毫秒）
            created_at = row[13]
            updated_at = row[14]
            
            # 转换创建时间
            if isinstance(created_at, datetime):
                created_at_timestamp = int(created_at.timestamp() * 1000)
            elif isinstance(created_at, str):
                try:
                    # 尝试解析字符串时间戳
                    created_at_dt = datetime.fromisoformat(created_at)
                    created_at_timestamp = int(created_at_dt.timestamp() * 1000)
                except:
                    try:
                        # 尝试另一种格式
                        created_at_dt = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                        created_at_timestamp = int(created_at_dt.timestamp() * 1000)
                    except:
                        created_at_timestamp = int(time.time() * 1000)
            else:
                created_at_timestamp = int(time.time() * 1000)
            
            # 转换更新时间
            if isinstance(updated_at, datetime):
                updated_at_timestamp = int(updated_at.timestamp() * 1000)
            elif isinstance(updated_at, str):
                try:
                    # 尝试解析字符串时间戳
                    updated_at_dt = datetime.fromisoformat(updated_at)
                    updated_at_timestamp = int(updated_at_dt.timestamp() * 1000)
                except:
                    try:
                        # 尝试另一种格式
                        updated_at_dt = datetime.strptime(updated_at, '%Y-%m-%d %H:%M:%S')
                        updated_at_timestamp = int(updated_at_dt.timestamp() * 1000)
                    except:
                        updated_at_timestamp = int(time.time() * 1000)
            else:
                updated_at_timestamp = int(time.time() * 1000)
            
            task_data = {
                "taskId": row[0],
                "sessionId": row[1],
                "taskType": row[2],
                "taskLevel": row[3],
                "plan": row[4],
                "userInput": row[5],
                "result": row[6],
                "status": row[7],
                "current_step_idx": row[8],
                "replanCount": row[9],
                "errorInfo": row[10],
                "inputTokens": row[11],
                "outputTokens": row[12],
                "createdAt": created_at_timestamp,
                "updatedAt": updated_at_timestamp,
                "steps": self.step_manager.get_steps_for_frontend(row[0])
            }
            tasks.append(task_data)
        return tasks


    def delete_tasks_by_session(self, session_id: str):
        """删除会话的所有任务

        Args:
            session_id: 会话ID
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT task_id FROM tasks WHERE session_id = ?", (session_id,))
        task_ids = [row[0] for row in cursor.fetchall()]

        for task_id in task_ids:
            self.step_manager.delete_steps(task_id)

        cursor.execute("DELETE FROM tasks WHERE session_id = ?", (session_id,))

        conn.commit()
        conn.close()

        self.logger.debug(f"会话任务已删除，session_id: {session_id}，删除了 {len(task_ids)} 个任务")
