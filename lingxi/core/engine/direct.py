import logging
from typing import Dict, List, Optional, Any, Union
from lingxi.core.llm_client import LLMClient
from lingxi.core.prompts import PromptTemplates
from lingxi.core.context import TaskContext


class DirectEngine:
    """直接响应引擎，用于trivial级别任务"""

    def __init__(self, config: Dict[str, Any]):
        """初始化直接响应引擎

        Args:
            config: 系统配置
        """
        self.config = config
        self.llm_client = LLMClient(config)
        self.logger = logging.getLogger(__name__)

        direct_config = config.get("execution_mode", {}).get("trivial", {})
        self.max_tokens = direct_config.get("max_tokens", 1000)

        self.logger.debug("初始化直接响应引擎")

    def process(self, context: TaskContext) -> Union[str, Any]:
        """处理用户输入，直接返回LLM响应

        Args:
            context: 任务上下文对象

        Returns:
            系统响应（非流式）或流式响应生成器（流式）
        """
        self.logger.debug(f"Direct模式处理任务: {context.get_task_level()}")

        task_level = context.get_task_level()
        history_context = self._build_history_context(context.session_history)

        prompt = f"""你是灵犀智能助手，一个聪明、友好的AI助手。

历史对话：
{history_context}

用户输入：
{context.user_input}

请直接回答用户的问题，不需要调用任何工具。"""

        if not context.stream:
            response = self.llm_client.complete(prompt, task_level=task_level)
            return response
        else:
            return self.llm_client.stream_complete(prompt, task_level=task_level)

    def _build_history_context(self, session_history: List[Dict[str, str]]) -> str:
        """构建历史上下文

        Args:
            session_history: 会话历史

        Returns:
            历史上下文字符串
        """
        return PromptTemplates.format_history_context(session_history, max_count=5)
