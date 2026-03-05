from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import json
import time


class EventType(str, Enum):
    """流式响应事件类型"""
    TASK_START = "task_start"
    THINK_START = "think_start"
    THINK_STREAM = "think_stream"
    THINK_FINAL = "think_final"
    PLAN_START = "plan_start"
    PLAN_FINAL = "plan_final"
    STEP_START = "step_start"
    STEP_END = "step_end"
    TASK_END = "task_end"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    PING = "ping"
    STREAM_END = "stream_end"


@dataclass
class StreamEvent:
    """流式响应事件"""
    event_type: EventType
    data: Dict[str, Any]

    def to_sse(self) -> str:
        """转换为 SSE 格式

        Returns:
            SSE 格式字符串
        """
        event_data = {
            "event_type": self.event_type.value,
            "data": self.data
        }
        return f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"

    @classmethod
    def create_task_start(cls, execution_id: str, task: str, task_level: str, model: str, session_id: str = "default") -> 'StreamEvent':
        """创建任务开始事件

        Args:
            execution_id: 执行ID
            task: 任务内容
            task_level: 任务级别
            model: 使用的模型
            session_id: 会话ID

        Returns:
            任务开始事件
        """
        return cls(
            event_type=EventType.TASK_START,
            data={
                "execution_id": execution_id,
                "task": task,
                "task_level": task_level,
                "model": model,
                "session_id": session_id,
                "timestamp": time.time()
            }
        )

    @classmethod
    def create_think_start(cls, execution_id: str, step_id: int = 0, content: str = "") -> 'StreamEvent':
        """创建思考开始事件

        Args:
            execution_id: 执行ID
            step_id: 步骤ID
            content: 思考内容

        Returns:
            思考开始事件
        """
        return cls(
            event_type=EventType.THINK_START,
            data={
                "execution_id": execution_id,
                "step_id": step_id,
                "content": content,
                "timestamp": time.time()
            }
        )

    @classmethod
    def create_think_stream(cls, execution_id: str, thought: str, step_id: int = 0) -> 'StreamEvent':
        """创建思考流式事件

        Args:
            execution_id: 执行ID
            thought: 思考内容
            step_id: 步骤ID

        Returns:
            思考流式事件
        """
        return cls(
            event_type=EventType.THINK_STREAM,
            data={
                "execution_id": execution_id,
                "thought": thought,
                "step_id": step_id,
                "timestamp": time.time()
            }
        )

    @classmethod
    def create_think_final(cls, execution_id: str, thought: str, step_id: int = 0) -> 'StreamEvent':
        """创建思考完成事件

        Args:
            execution_id: 执行ID
            thought: 完整思考内容
            step_id: 步骤ID

        Returns:
            思考完成事件
        """
        return cls(
            event_type=EventType.THINK_FINAL,
            data={
                "execution_id": execution_id,
                "thought": thought,
                "step_id": step_id,
                "timestamp": time.time()
            }
        )

    @classmethod
    def create_plan_start(cls, execution_id: str, task_id: Optional[str] = None) -> 'StreamEvent':
        """创建计划开始事件

        Args:
            execution_id: 执行ID
            task_id: 任务ID

        Returns:
            计划开始事件
        """
        return cls(
            event_type=EventType.PLAN_START,
            data={
                "execution_id": execution_id,
                "task_id": task_id,
                "timestamp": time.time()
            }
        )

    @classmethod
    def create_plan_final(cls, execution_id: str, plan: list, task_id: Optional[str] = None) -> 'StreamEvent':
        """创建计划完成事件

        Args:
            execution_id: 执行ID
            plan: 计划列表
            task_id: 任务ID

        Returns:
            计划完成事件
        """
        return cls(
            event_type=EventType.PLAN_FINAL,
            data={
                "execution_id": execution_id,
                "task_id": task_id,
                "plan": plan,
                "timestamp": time.time()
            }
        )

    @classmethod
    def create_step_start(cls, execution_id: str, step_index: int, description: str, task_id: Optional[str] = None) -> 'StreamEvent':
        """创建步骤开始事件

        Args:
            execution_id: 执行ID
            step_index: 步骤索引
            description: 步骤描述
            task_id: 任务ID

        Returns:
            步骤开始事件
        """
        return cls(
            event_type=EventType.STEP_START,
            data={
                "execution_id": execution_id,
                "task_id": task_id,
                "step_index": step_index,
                "description": description,
                "timestamp": time.time()
            }
        )

    @classmethod
    def create_step_end(cls, execution_id: str, step_index: int, result: Dict[str, Any], 
                        status: str = "success", task_id: Optional[str] = None) -> 'StreamEvent':
        """创建步骤结束事件

        Args:
            execution_id: 执行ID
            step_index: 步骤索引
            result: 步骤结果
            status: 步骤状态
            task_id: 任务ID

        Returns:
            步骤结束事件
        """
        return cls(
            event_type=EventType.STEP_END,
            data={
                "execution_id": execution_id,
                "task_id": task_id,
                "step_index": step_index,
                "result": result,
                "status": status,
                "timestamp": time.time()
            }
        )

    @classmethod
    def create_task_end(cls, execution_id: str, result: Dict[str, Any], status: str = "completed") -> 'StreamEvent':
        """创建任务结束事件

        Args:
            execution_id: 执行ID
            result: 任务结果
            status: 任务状态

        Returns:
            任务结束事件
        """
        return cls(
            event_type=EventType.TASK_END,
            data={
                "execution_id": execution_id,
                "result": result,
                "status": status,
                "timestamp": time.time()
            }
        )

    @classmethod
    def create_task_failed(cls, execution_id: str, error: str, error_code: str = "UNKNOWN",
                          traceback: Optional[str] = None, recoverable: bool = True) -> 'StreamEvent':
        """创建任务失败事件

        Args:
            execution_id: 执行ID
            error: 错误信息
            error_code: 错误码
            traceback: 错误堆栈
            recoverable: 是否可恢复

        Returns:
            任务失败事件
        """
        data = {
            "execution_id": execution_id,
            "error": error,
            "error_code": error_code,
            "recoverable": recoverable,
            "timestamp": time.time()
        }
        if traceback:
            data["traceback"] = traceback

        return cls(
            event_type=EventType.TASK_FAILED,
            data=data
        )

    @classmethod
    def create_task_cancelled(cls, execution_id: str, task_id: Optional[str] = None, reason: str = "client_abort",
                              current_step: int = 0, completed_steps: int = 0, can_resume: bool = True) -> 'StreamEvent':
        """创建任务取消事件

        Args:
            execution_id: 执行ID
            task_id: 任务ID
            reason: 取消原因
            current_step: 当前步骤
            completed_steps: 已完成步骤数
            can_resume: 是否可恢复

        Returns:
            任务取消事件
        """
        return cls(
            event_type=EventType.TASK_CANCELLED,
            data={
                "execution_id": execution_id,
                "task_id": task_id,
                "cancelled_at": time.time(),
                "reason": reason,
                "current_step": current_step,
                "completed_steps": completed_steps,
                "can_resume": can_resume
            }
        )

    @classmethod
    def create_ping(cls) -> 'StreamEvent':
        """创建心跳事件

        Returns:
            心跳事件
        """
        return cls(
            event_type=EventType.PING,
            data={
                "timestamp": time.time()
            }
        )

    @classmethod
    def create_stream_end(cls) -> 'StreamEvent':
        """创建流结束事件

        Returns:
            流结束事件
        """
        return cls(
            event_type=EventType.STREAM_END,
            data={}
        )


def create_heartbeat_sse() -> str:
    """创建心跳 SSE 消息（SSE comment 格式）

    Returns:
        SSE 心跳消息
    """
    return ": heartbeat\n\n"
