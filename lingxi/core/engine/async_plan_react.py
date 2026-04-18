"""异步 Plan+ReAct 引擎模块

完全异步化的 Plan+ReAct 引擎，解决 WebSocket 阻塞问题
"""

import time
import uuid
import json
import logging
from typing import Dict, List, Any, Union, Optional
from collections.abc import AsyncGenerator
from lingxi.core.context.task_context import TaskContext
from lingxi.core.engine.async_react_core import AsyncReActCore
from lingxi.core.prompts.prompts import PromptTemplates
from lingxi.utils.config import get_config
from lingxi.core.context.task_context import TaskStoppedException

class AsyncPlanReActEngine(AsyncReActCore):
    """异步 Plan+ReAct 引擎
    
    继承自 AsyncReActCore，实现完全异步的执行流程
    """

    def __init__(self, config: Dict[str, Any], action_caller=None, session_manager=None, websocket_manager=None):
        """初始化异步 Plan+ReAct 引擎

        Args:
            config: 系统配置
            action_caller: 行动调用器
            session_manager: 会话管理器
            websocket_manager: WebSocket 管理器
        """
        super().__init__(config, action_caller, session_manager, websocket_manager)
        
        config = get_config()
        complex_config = config.get("execution_mode", {}).get("complex", {})
        self.max_plan_steps = int(complex_config.get("max_plan_steps", 8))
        self.max_replan_count = int(complex_config.get("max_replan_count", 2))
        self.max_step_retries = int(complex_config.get("max_step_retries", 3))
        self.max_loop_per_step = int(complex_config.get("max_loop_per_step", 5))

        self.logger = logging.getLogger(__name__)
        self.logger.debug("初始化异步 Plan+ReAct 执行引擎")

    def _format_plan_for_prompt(self, plan: List[str]) -> str:
        """格式化计划用于提示词"""
        return "\n".join([f"{i+1}. {step}" for i, step in enumerate(plan)])

    async def _execute_plan_steps(
        self,
        plan: List[str],
        context: TaskContext
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """执行计划步骤（异步）

        Args:
            plan: 计划步骤列表
            context: 任务上下文

        Yields:
            流式响应块
        """
        stream = context.stream
        try:
           

            async for chunk in super()._execute_task_stream(context):
                if stream:
                    yield chunk

        except TaskStoppedException as e:
            raise e
        except Exception as e:
            import traceback
            self.logger.error(f"计划执行失败：{e}\n{traceback.format_exc()}")

            if stream:
                yield {"type": "error", "message": str(e)}

    async def _execute_task_stream(
        self,
        context: TaskContext
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """执行任务（异步流式）- 统一入口，智能路由

        Args:
            context: 任务上下文

        Yields:
            流式响应块
        """
        task = context.user_input
        task_info = context.task_info
        plan_descriptions = []
        
        task_level = task_info.task_type
        self._publish_task_start(context)

        # 分析任务
        plan_info={}
        if(get_config().get("engine", {}).get("enable_plan", True)):
            plan_info = await self._analyze_task_and_plan(context)
            self.logger.debug(f"异步 Plan+ReAct 引擎处理任务：level={task_level}, task={task}")
            if not plan_info:
                self.logger.warning("任务分析失败，降级为父类执行")
                async for chunk in super()._execute_task_stream(context):
                   yield chunk
                return
        
        task_level = plan_info.get("level", "complex")
        context.task_info.task_type = task_level
        context.description = plan_info.get("summary", context.user_input)

        self._publish_plan_start(context)
        next_action = plan_info.get("next_action")
        plan = plan_info.get("plan", [])
        plan_descriptions = []
        if plan:
            plan_descriptions = [step.get("description", str(step)) for step in plan]

        context.task_info.plan = json.dumps(plan_descriptions)
        self._publish_plan_events(context,plan_descriptions)
        self.logger.debug(f"分析结果：level={plan_info.get('level', '')}, has_next_action={next_action is not None}, plan_steps={len(plan)}")
        direct_answer = plan_info.get("direct_answer", "")
        # 检查用户是否明确要求使用某个技能
        user_input_lower = context.user_input.lower()
        skill_mentioned = any(skill in user_input_lower for skill in ["spawn_subagent", "子代理"])
        if plan:
            self.logger.debug("复杂任务，执行计划")
            async for chunk in self._execute_plan_steps(plan_descriptions, context):
                yield chunk
        elif task_level == "simple" and direct_answer not in ["", None] and not skill_mentioned:
            self.logger.debug("直接回答任务，执行 next_action")
            async for chunk in self._execute_direct_action(direct_answer, context):
                yield chunk
        elif task_level == "simple":
             self.logger.warning("简单任务分析未提供 next_action 或用户明确要求使用技能，降级为父类执行")
             async for chunk in super()._execute_task_stream(context):
                yield chunk
        elif task_level == "direct" and not skill_mentioned:
            self.logger.debug("直接回答任务，执行 next_action")
            async for chunk in self._execute_direct_action(direct_answer, context):
                yield chunk
        elif task_level == "direct":
            self.logger.debug("用户明确要求使用技能，降级为父类执行")
            async for chunk in super()._execute_task_stream(context):
                yield chunk
        else:
            self.logger.warning("无法处理任务，降级为父类执行")
            async for chunk in super()._execute_task_stream(context):
                yield chunk
        

    async def _execute_direct_action(
        self,
        direct_answer: str,
        context: TaskContext
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """直接执行行动（异步）

        Args:
            action_data: 行动数据
            context: 任务上下文

        Yields:
            流式响应块
        """
        stream = context.stream
        context.task_info.result = direct_answer
        context.task_info.status = "completed"
        self.logger.debug(f"直接执行行动：action=finish, thought={direct_answer[:50]}...")
        self._publish_task_end(direct_answer,context)
        
        if stream:
            yield {"type": "task_finish", "result": direct_answer}
        return

    async def _analyze_task_and_plan(
        self,
        context: TaskContext,
    ) -> Optional[Dict[str, Any]]:
        """分析任务并生成计划（异步）

        Args:
            task: 任务内容
            task_info: 任务信息

        Returns:
            分析结果
        """
        task_info = context.task_info
        available_skills = self.action_caller.list_available_skills(enabled_only=True) if self.action_caller else []
        history_context = context.session_context.get_history_context()
        
        messages = PromptTemplates.build_task_analysis_messages_with_cache(
            task=context.user_input,
            history_context=history_context,
            skills_list=PromptTemplates.format_skills_list(available_skills),
            context=context
        )
        self.logger.debug(f"发往 LLM 的任务计划消息：{messages}")
        last_thought = ""
        try:
            full_response = ""
            self._publish_think_start(context, 0, "")
            async for chunk in self.async_llm_client.stream_chat(messages, task_info.task_type, enable_thinking=context.thinking_mode):
                choices = chunk.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})
                    if "content" in delta:
                        content = delta["content"]
                        if content:  # 只有当 content 不为 None 和空字符串时才处理
                            full_response += content
                            # 尝试提取thought字段
                            from lingxi.utils.json_parser import extract_partial_json_field
                            thought = extract_partial_json_field(full_response, "thought")
                            if thought and thought != last_thought:
                                # 只输出增量的thought内容
                                incremental_thought = thought[len(last_thought):] if last_thought else thought
                                last_thought = thought
                                self._publish_think_stream(context, 0, incremental_thought)

            self.logger.debug(f"原始 LLM 响应：{full_response}")

            self._publish_think_end(context, 0, last_thought)
            
            from lingxi.core.engine.utils import parse_json_with_escape_cleaning
            return parse_json_with_escape_cleaning(full_response, self.logger)
        except Exception as e:
            self.logger.error(f"任务分析失败：{e}", exc_info=True)
            self._publish_task_failed(context,error=str(e))
            raise e

    async def process(
        self,
        context: TaskContext
    ) -> Union[str, AsyncGenerator[Dict[str, Any], None]]:
        """处理用户输入（异步）

        Args:
            context: 任务上下文
        Returns:
            系统响应或异步生成器
        """
        self.logger.debug(f"异步 Plan+ReAct 处理任务：{context.task_info.task_type} (stream={context.stream})")

        if context.stream:
            return self._execute_task_stream(context)
        else:
            # 非流式模式：收集所有结果
            result = None
            async for chunk in self._execute_task_stream(context):
                if chunk.get("type") == "task_finish":
                    result = chunk.get("result", "")
            return result
