"""Session 实体模块 - 数据模型定义"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Step:
    """任务步骤实体类（使用 dataclass）"""
    step_id: str
    task_id: str  # 任务ID
    step_index: int = 0  # 步骤索引
    step_type: str = "thinking"
    description: str = ""  # 步骤描述
    status: str = "completed"  # 步骤状态 completed 或 thinking
    thought: str = ""  # 思考内容 
    result: str = ""  # 步骤结果
    skill_call: str = ""  # 调用的技能
    result_description: str = ""  # 步骤结果描述
    created_at: datetime = datetime.now()  # 创建时间
    updated_at: datetime = datetime.now()  # 更新时间


@dataclass
class Task:
    """任务实体类（使用 dataclass）"""
    task_id: str
    session_id: str
    task_type: str = "simple"  # 任务类型 simple 或 complex
    plan: str = "[]"  # 计划步骤
    user_input: str = ""  # 用户输入
    result: str = ""  # 任务结果
    status: str = "running" #执行中 running ,完成 completed ,手动中断 interrupted
    current_step_idx: int = 0  # 当前步骤索引
    replan_count: int = 0  # 重新计划次数
    error_info: str = ""  # 错误信息
    input_tokens: int = 0  # 输入token数
    output_tokens: int = 0  # 输出token数
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()


@dataclass
class Session:
    """会话实体类（使用 dataclass）"""
    session_id: str
    user_name: str = "default"
    title: str = "新会话"  
    current_task_id: str = ""  # 当前任务 ID
    total_tokens: int = 0  # 总token数
    created_at: datetime = datetime.now()  # 创建时间
    updated_at: datetime = datetime.now()  # 更新时间
    
    def get_info(self):
        """获取会话信息字符串"""
        return f"{self.session_id}，{self.user_name}，{self.created_at}，{self.updated_at}"
