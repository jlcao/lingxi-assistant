"""Session 模块 - 兼容性封装

为保持向后兼容，将数据模型和管理器重新导出到同一命名空间
"""

from lingxi.core.session.session_models import Step, Task, Session
from lingxi.core.session.session_manager import (
    step_to_dict,
    dict_to_step,
    task_to_dict,
    dict_to_task,
    session_to_dict,
    dict_to_session,
    SessionManager
)

__all__ = [
    "Step",
    "Task",
    "Session",
    "step_to_dict",
    "dict_to_step",
    "task_to_dict",
    "dict_to_task",
    "session_to_dict",
    "dict_to_session",
    "SessionManager",
]
