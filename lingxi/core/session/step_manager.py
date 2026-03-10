from __future__ import annotations

import logging
import sqlite3
from typing import Dict, List, Optional, Any
from datetime import datetime

from lingxi.core.session.session_models import Step


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


class StepManager:
    """步骤管理器，负责任务步骤的增删改查"""
    _instance = None  # 单例实例

    def __new__(cls, db_manager, logger: logging.Logger):
        """单例模式：确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db_manager, logger: logging.Logger):
        """初始化步骤管理器

        Args:
            db_manager: 数据库管理器实例
            logger: 日志记录器
        """
        self.db_manager = db_manager
        self.logger = logger
        self._initialized = True

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
        with self.db_manager.transaction() as conn:
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

    def get_steps(self, task_id: str) -> List[Dict[str, Any]]:
        """获取任务的所有步骤

        Args:
            task_id: 任务ID

        Returns:
            步骤列表
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT step_id, task_id, step_index, step_type, description, 
                   thought, result, skill_call, status, created_at
            FROM steps
            WHERE task_id = ?
            ORDER BY step_index ASC
        """, (task_id,))

        rows = cursor.fetchall()
        conn.close()

        steps = []
        for row in rows:
            steps.append({
                "step_id": row[0],
                "task_id": row[1],
                "step_index": row[2],
                "step_type": row[3],
                "description": row[4],
                "thought": row[5],
                "result": row[6],
                "skill_call": row[7],
                "status": row[8],
                "created_at": row[9]
            })

        return steps

    def get_completed_steps(self, task_id: str, current_idx: int) -> List[Dict[str, Any]]:
        """获取已完成的步骤

        Args:
            task_id: 任务ID
            current_idx: 当前步骤索引

        Returns:
            已完成步骤列表
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT step_id, task_id, step_index, step_type, description, thought, result, skill_call, status, created_at
            FROM steps
            WHERE task_id = ? AND step_index < ?
            ORDER BY step_index ASC
        """, (task_id, current_idx))

        rows = cursor.fetchall()
        conn.close()

        completed_steps = []
        for row in rows:
            completed_steps.append({
                "step_id": row[0],
                "task_id": row[1],
                "step_index": row[2],
                "step_type": row[3],
                "description": row[4],
                "thought": row[5],
                "result": row[6],
                "skill_call": row[7],
                "status": row[8],
                "created_at": row[9]
            })

        return completed_steps

    def delete_steps(self, task_id: str):
        """删除任务的所有步骤

        Args:
            task_id: 任务ID
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM steps WHERE task_id = ?", (task_id,))
        conn.commit()
        conn.close()

        self.logger.debug(f"任务步骤已删除，task_id: {task_id}")
