# lingxi/core/context.py
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from lingxi.core.context.session_context import SessionContext
from lingxi.core.session.session_models import Step, Task


class TaskStoppedException(Exception):
    """任务被终止的异常"""
    pass

@dataclass
class TaskContext:
    """任务上下文对象，封装任务执行所需的所有上下文信息"""
    
    user_input: str           #用户输入
    task_info: Task = None        #任务信息
    session_id: str = "default"     #会话ID
    session_history: Optional[List[Dict[str, str]]] = None  #历史会话
    stream: bool = False          #流式模式开关
    task_id: Optional[str] = None     #任务Id
    execution_id: Optional[str] = None   
    input_tokens: int = 0         #输入token数
    output_tokens: int = 0     #输出token数
    workspace_path: Optional[str] = None   #工作目录
    thinking_mode: bool = False     #深度思考模式开关
    session_context: Optional[SessionContext] = None  #会话上下文
    steps:List[Step]=field(default_factory=list)  #当前任务已经执行步骤
    soul_prompt: Optional[str] = None  #SOUL提示词
    rule: Optional[str] = None  #规则
    userMemory: Optional[str] = None  #用户记忆
    projectMemory: Optional[str] = None  #项目记忆
    description: Optional[str] = None  #任务描述
    
    
    def __post_init__(self):
        if self.session_history is None:
            self.session_history = []
        if self.task_id is None:
            import uuid
            self.task_id = f"task_{self.session_id}_{uuid.uuid4().hex[:8]}"
            self.task_info = Task(task_id=self.task_id,session_id=self.session_id,user_input=self.user_input)
        if self.execution_id is None:
            import time
            self.execution_id = f"exec_{int(time.time())}"
        
        # 任务终止标志
        self._is_stopped = False
        # 终止事件
        self._stop_event = asyncio.Event()
    
    def stop(self):
        """终止任务"""
        self._is_stopped = True
        self.task_info.status='interrupted'
        self.task_info.result='用户手动终止'
        self._stop_event.set()

    @property
    def is_stopped(self) -> bool:
        """检查任务是否已终止"""
        return self._is_stopped

    def check_stopped(self):
        """检查任务是否已终止，如果是则抛出异常"""
        if self._is_stopped:
            raise TaskStoppedException("任务已被用户终止")

    async def wait_for_stop(self, timeout: float = None):
        """等待终止信号（可选超时）"""
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass
        
    
    def get_task_level(self) -> str:
        """获取任务级别"""
        if hasattr(self.task_info, 'get'):
            return self.task_info.get("level", "simple")
        else:
            return getattr(self.task_info, "level", "simple")
    
    def get_task_type(self) -> str:
        """获取任务类型"""
        if hasattr(self.task_info, 'get'):
            return self.task_info.get("task_type", "unknown")
        else:
            return getattr(self.task_info, "task_type", "unknown")
    
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