import time
import uuid
from typing import Dict, List, Any, Union, Generator

from lingxi.core.engine.plan_react_core import PlanReActCore
from lingxi.core.context import TaskContext


class PlanReActEngine(PlanReActCore):
    """支持断点重试的Plan+ReAct执行引擎
    
    继承自 PlanReActCore，复用其智能路由和执行逻辑，
    额外支持从检查点恢复执行的功能。
    """

    def process(self, context: TaskContext) -> Union[str, Generator[Dict[str, Any], None, None]]:
        """处理用户输入，支持断点恢复

        Args:
            context: 任务上下文对象

        Returns:
            系统响应（非流式）或流式响应生成器（流式）
        """
        self.logger.debug(f"Plan+ReAct处理任务: {context.get_task_level()} (stream={context.stream})")

        if self.session_manager:
            existing_checkpoint = self.session_manager.restore_checkpoint(context.session_id)

            if existing_checkpoint and existing_checkpoint.get("task") == context.user_input:
                self.logger.debug("从检查点恢复执行")
                return self._resume_from_checkpoint(existing_checkpoint, context)

        return self._execute_task_stream(context)
