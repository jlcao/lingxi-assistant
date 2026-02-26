from typing import Dict, List, Optional, Any, Union, Generator
from .react_core import ReActCore


class ReActEngine(ReActCore):
    """ReAct推理引擎，结合推理和行动"""

    def process(self, user_input: str, task_info: Dict[str, Any], session_history: List[Dict[str, str]] = None, 
                session_id: str = "default", stream: bool = False) -> Union[str, Generator[Dict[str, Any], None, None]]:
        """处理用户输入

        Args:
            user_input: 用户输入
            task_info: 任务信息
            session_history: 会话历史
            session_id: 会话ID
            stream: 是否启用流式输出

        Returns:
            系统响应（非流式）或流式响应生成器（流式）
        """
        return self._process_task(user_input, task_info, session_history, session_id, stream)
