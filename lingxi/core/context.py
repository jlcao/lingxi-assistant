# lingxi/core/context.py
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

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
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "user_input": self.user_input,
            "task_info": self.task_info,
            "session_id": self.session_id,
            "session_history": self.session_history,
            "stream": self.stream,
            "task_id": self.task_id,
            "execution_id": self.execution_id
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
            execution_id=data.get("execution_id")
        )