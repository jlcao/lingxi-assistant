"""异步 Plan+ReAct 引擎模块

完全异步化的 Plan+ReAct 引擎，解决 WebSocket 阻塞问题
"""

import time
import uuid
import logging
from typing import Dict, List, Any, Union, Optional
from collections.abc import AsyncGenerator
from lingxi.core.context.task_context import TaskContext
from lingxi.core.engine.async_react_core import AsyncReActCore
from lingxi.core.prompts.prompts import PromptTemplates

class AsyncPlanReActEngine(AsyncReActCore):
    """异步 Plan+ReAct 引擎
    
    继承自 AsyncReActCore，实现完全异步的执行流程
    """

    def __init__(self, config: Dict[str, Any], skill_caller=None, session_manager=None, websocket_manager=None):
        """初始化异步 Plan+ReAct 引擎

        Args:
            config: 系统配置
            skill_caller: 技能调用器
            session_manager: 会话管理器
            websocket_manager: WebSocket 管理器
        """
        super().__init__(config, skill_caller, session_manager, websocket_manager)

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
        task = context.user_input
        task_info = context.task_info
        history = context.session_history
        session_id = context.session_id
        execution_id = context.execution_id
        stream = context.stream
        thinking_mode = context.thinking_mode
        task_id = context.task_id
        
        try:
            session_history = self.session_manager.get_history(session_id) if self.session_manager else history

            enhanced_task_info = {
                **task_info,
                "level": "complex",
                "description": task,
                "plan": plan,
                "plan_formatted": self._format_plan_for_prompt(plan),
                "reason": task_info.get("reason", "复杂任务，需要多步骤执行")
            }

            parent_context = TaskContext(
                user_input=task,
                task_info=enhanced_task_info,
                session_id=session_id,
                session_history=session_history,
                stream=stream,
                task_id=task_id,
                execution_id=execution_id,
                workspace_path=context.workspace_path,
                thinking_mode=context.thinking_mode,
                session_context=context.session_context
            )

            async for chunk in super()._execute_task_stream(parent_context):
                if stream:
                    yield chunk

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
        history = context.session_history
        session_id = context.session_id
        execution_id = context.execution_id
        stream = context.stream
        thinking_mode = context.thinking_mode
        task_id = context.task_id
        plan_descriptions = []
        
        task_level = task_info.get("level", "simple")
        history_context = self._build_history_context(history)

        self.logger.debug(f"异步 Plan+ReAct 引擎处理任务：level={task_level}, task={task}")
    
        self._publish_task_start(session_id, execution_id, task, task_info, task_id)
        
        analysis = await self._analyze_task_and_plan(context, history_context)
        
        if not analysis:
            self.logger.warning("任务分析失败，降级为父类执行")
            async for chunk in super()._execute_task_stream(context):
                yield chunk
            return
        
        analyzed_level = analysis.get("level", "simple")
        summary = analysis.get("summary", "")
        self._publish_plan_start(session_id, execution_id, task_id, analyzed_level, summary)
        context.task_info["level"] = analyzed_level
        next_action = analysis.get("next_action")
        plan = analysis.get("plan", [])
        plan_descriptions = []
        if plan:
            plan_descriptions = [step.get("description", str(step)) for step in plan]
        self._publish_plan_events(session_id, execution_id, plan_descriptions, task_id)
        self.logger.debug(f"分析结果：level={analyzed_level}, has_next_action={next_action is not None}, plan_steps={len(plan)}")
        
        if analyzed_level == "simple" and analysis.get("direct_answer", "") not in ["", None]:
            self.logger.debug("直接回答任务，执行 next_action")
            async for chunk in self._execute_direct_action(analysis.get("direct_answer", ""), context):
                yield chunk
        elif analyzed_level == "simple":
             self.logger.warning("简单任务分析未提供 next_action，降级为父类执行")
             async for chunk in super()._execute_task_stream(context):
                yield chunk
        elif analyzed_level == "direct":
            self.logger.debug("直接回答任务，执行 next_action")
            async for chunk in self._execute_direct_action(analysis.get("direct_answer", ""), context):
                yield chunk
        elif plan:
            self.logger.debug("复杂任务，执行计划")
            plan_descriptions = [step.get("description", str(step)) for step in plan]
            async for chunk in self._execute_plan_steps(plan_descriptions, context):
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
        self.logger.debug(f"直接执行行动：action=finish, thought={direct_answer[:50]}...")
        self._publish_task_end(direct_answer, context)
        
        if stream:
            yield {"type": "task_finish", "result": direct_answer}
        return

    async def _analyze_task_and_plan(
        self,
        context: TaskContext,
        history_context: str,
    ) -> Optional[Dict[str, Any]]:
        """分析任务并生成计划（异步）

        Args:
            task: 任务内容
            task_info: 任务信息
            history_context: 历史上下文
            session_id: 会话 ID
            execution_id: 执行 ID

        Returns:
            分析结果
        """
        session_id = context.session_id
        execution_id = context.execution_id
        task = context.user_input
        task_info = context.task_info
        available_skills = self.skill_caller.list_available_skills(enabled_only=True) if self.skill_caller else []
        skills_list = PromptTemplates.format_skills_list(available_skills)
        system_info = PromptTemplates.get_system_info()
        soul_prompt = context.session_context.soul_prompt
        thinking_mode = context.thinking_mode
        
        messages = PromptTemplates.build_task_analysis_messages_with_cache(
            task=task,
            history_context=history_context,
            skills_list=skills_list,
            system_info=system_info,
            max_plan_steps=self.max_plan_steps,
            soul_system_prompt=soul_prompt
        )
        self.logger.debug(f"发往 LLM 的任务计划消息：{messages}")
        last_thought = ""
        try:
            full_response = ""
            self._publish_think_start(session_id, execution_id, -1, "")
            async for chunk in self.async_llm_client.stream_chat(messages, task_info.get("level", "simple"), enable_thinking=thinking_mode):
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
                                self._publish_think_stream(session_id, execution_id, -1, incremental_thought)

            self.logger.debug(f"原始 LLM 响应：{full_response}")
            self._publish_think_end(session_id, execution_id, 0, last_thought)
            
            from lingxi.core.engine.utils import parse_json_with_escape_cleaning
            return parse_json_with_escape_cleaning(full_response, self.logger)
        except Exception as e:
            self.logger.error(f"任务分析失败：{e}", exc_info=True)
            raise e
        
        return None

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
        self.logger.debug(f"异步 Plan+ReAct 处理任务：{context.get_task_level()} (stream={context.stream})")

        return self._execute_task_stream(context)
