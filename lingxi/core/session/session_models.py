"""Session 实体模块 - 数据模型定义"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Step:
    """任务步骤实体类（使用 dataclass）"""
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
    """任务实体类（使用 dataclass）"""
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
    """会话实体类（使用 dataclass）"""
    session_id: str
    user_name: str = "default"
    title: str = "新会话"
    current_task_id: str = ""
    total_tokens: int = 0
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    
    def get_info(self):
        """获取会话信息字符串"""
        return f"{self.session_id}，{self.user_name}，{self.created_at}，{self.updated_at}"
