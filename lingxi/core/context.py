# lingxi/core/context.py
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from lingxi.context.manager import ContextManager

@dataclass
class TaskContext:
    """任务上下文对象，封装任务执行所需的所有上下文信息"""
    
    user_input: str
    task_info: Dict[str, Any]
    session_id: str = "default"
    session_history: Optional[List[Dict[str, str]]] = None
    stream: bool = False
    task_id: Optional[str] = None
    execution_id: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    workspace_path: Optional[str] = None
    thinking_mode: bool = False
    session_context: Optional[ContextManager] = None
    
    def __post_init__(self):
        if self.session_history is None:
            self.session_history = []
        if self.task_id is None:
            import uuid
            self.task_id = f"task_{self.session_id}_{uuid.uuid4().hex[:8]}"
        if self.execution_id is None:
            import time
            self.execution_id = f"exec_{int(time.time())}"
    
    def get_task_level(self) -> str:
        """获取任务级别"""
        return self.task_info.get("level", "simple")
    
    def get_task_type(self) -> str:
        """获取任务类型"""
        return self.task_info.get("task_type", "unknown")
    
    def add_tokens(self, input_tokens: int, output_tokens: int) -> None:
        """累加 token 使用量

        Args:
            input_tokens: 输入 token 数
            output_tokens: 输出 token 数
        """
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
    
    def get_total_tokens(self) -> int:
        """获取总 token 数"""
        return self.input_tokens + self.output_tokens
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "user_input": self.user_input,
            "task_info": self.task_info,
            "session_id": self.session_id,
            "session_history": self.session_history,
            "stream": self.stream,
            "task_id": self.task_id,
            "execution_id": self.execution_id,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "workspace_path": self.workspace_path
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskContext':
        """从字典创建上下文对象"""
        return cls(
            user_input=data.get("user_input", ""),
            task_info=data.get("task_info", {}),
            session_id=data.get("session_id", "default"),
            session_history=data.get("session_history", []),
            stream=data.get("stream", False),
            task_id=data.get("task_id"),
            execution_id=data.get("execution_id"),
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            workspace_path=data.get("workspace_path")
        )