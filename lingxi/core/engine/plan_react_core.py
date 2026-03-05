import logging
import time
import json
import re
from typing import Dict, List, Optional, Any, Union, Generator
from lingxi.core.engine.react_core import ReActCore
from lingxi.core.engine.utils import parse_plan
from lingxi.core.prompts import PromptTemplates
from lingxi.core.event import global_event_publisher
from lingxi.core.context import local_context
from lingxi.core.session import SessionManager
from lingxi.utils.json_parser import extract_partial_json_field


class PlanReActCore(ReActCore):
    """Plan+ReAct 引擎 - 统一入口，智能路由
    
    继承自 ReActCore，复用其执行逻辑：
    - 简单任务：直接调用父类 _execute_task_stream
    - 复杂任务：生成计划后，逐个子任务调用父类方法执行
    """

    def __init__(self, config: Dict[str, Any], skill_caller=None, session_manager: SessionManager = None, websocket_manager=None):
        super().__init__(config, skill_caller, session_manager, websocket_manager)

        complex_config = config.get("execution_mode", {}).get("complex", {})
        self.max_plan_steps = int(complex_config.get("max_plan_steps", 8))
        self.max_replan_count = int(complex_config.get("max_replan_count", 2))
        self.max_step_retries = int(complex_config.get("max_step_retries", 3))
        self.max_loop_per_step = int(complex_config.get("max_loop_per_step", 5))

        self.logger.debug("初始化Plan+ReAct执行引擎核心（继承ReActCore）")

    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """解析任务分析响应

        Args:
            response: LLM响应

        Returns:
            解析后的字典
        """
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group(0))
                
                level = result.get("level", "simple")
                if level not in ["simple", "complex"]:
                    level = "simple"
                
                return {
                    "level": level,
                    "confidence": float(result.get("confidence", 0.5)),
                    "reason": result.get("reason", ""),
                    "direct_answer": result.get("direct_answer", ""),
                    "next_action": result.get("next_action"),
                    "plan": result.get("plan", [])
                }
        except Exception as e:
            self.logger.error(f"解析任务分析响应失败: {e}")

        return {
            "level": "simple",
            "confidence": 0.5,
            "reason": "解析失败，默认simple",
            "direct_answer": "",
            "next_action": None,
            "plan": []
        }

    def _analyze_task_and_plan(self, task: str, task_info: Dict[str, Any],
                                history_context: str, session_id: str,
                                execution_id: str) -> Optional[Dict[str, Any]]:
        """分析任务并生成计划

        Args:
            task: 任务文本
            task_info: 任务信息
            history_context: 历史上下文
            session_id: 会话ID
            execution_id: 执行ID

        Returns:
            分析结果字典，失败返回None
        """
        available_skills = self.skill_caller.list_available_skills(enabled_only=True) if self.skill_caller else []
        skills_list = PromptTemplates.format_skills_list(available_skills)
        system_info = PromptTemplates.get_system_info()

        messages = PromptTemplates.build_task_analysis_messages_with_cache(
            task=task,
            history_context=history_context,
            skills_list=skills_list,
            system_info=system_info,
            max_plan_steps=self.max_plan_steps
        )

        stream_response = self.llm_client.stream_chat_complete_with_cache(messages, task_level="simple")
        full_response = ""
        last_thought = ""

        for chunk in stream_response:
            if hasattr(chunk, 'choices') and chunk.choices:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    full_response += delta.content
                    thought = extract_partial_json_field(full_response, "thought", nested_path="next_action")
                    if thought and thought != last_thought:
                        incremental_thought = thought[len(last_thought):] if last_thought else thought
                        self._publish_think_stream(session_id, execution_id, 0, incremental_thought)
                        last_thought = thought

        return self._parse_analysis_response(full_response)

    def _publish_plan_start(self, session_id: str, execution_id: str):
        """发布计划开始事件

        Args:
            session_id: 会话ID
            execution_id: 执行ID
        """
        task_id = getattr(local_context, 'task_id', None)

        global_event_publisher.publish(
            'plan_start',
            session_id=session_id,
            execution_id=execution_id,
            task_id=task_id
        )

    def _publish_plan_events(self, session_id: str, execution_id: str, plan: List[str]):
        """发布计划相关事件

        Args:
            session_id: 会话ID
            execution_id: 执行ID
            plan: 计划步骤列表
        """
        task_id = getattr(local_context, 'task_id', None)

        global_event_publisher.publish(
            'plan_final',
            session_id=session_id,
            execution_id=execution_id,
            task_id=task_id,
            plan=[{"step": i+1, "description": step} for i, step in enumerate(plan)]
        )

    def _create_initial_checkpoint(self, task: str, plan: List[str]) -> Dict[str, Any]:
        """创建初始检查点

        Args:
            task: 任务文本
            plan: 计划步骤列表

        Returns:
            初始检查点
        """
        return {
            "task": task,
            "plan": plan,
            "current_step_idx": 0,
            "completed_steps": [],
            "step_results": [],
            "replan_count": 0,
            "execution_status": "running",
            "error_info": None,
            "timestamp": time.time()
        }

    def _save_plan_checkpoint(self, session_id: str, checkpoint: Dict[str, Any]):
        """保存计划检查点

        Args:
            session_id: 会话ID
            checkpoint: 检查点
        """
        if self.session_manager:
            self.session_manager.save_checkpoint(session_id, checkpoint)

    def _execute_plan_steps(self, plan: List[str], task: str, task_info: Dict[str, Any],
                           history: List[Dict[str, str]], session_id: str,
                           execution_id: str, stream: bool) -> Generator[Dict[str, Any], None, None]:
        """执行计划中的步骤（将完整计划封装到ReAct提示词中，单次调用执行）

        Args:
            plan: 计划步骤列表
            task: 原始任务文本
            task_info: 任务信息
            history: 会话历史
            session_id: 会话ID
            execution_id: 执行ID
            stream: 是否流式输出

        Yields:
            流式响应块
        """
        # 检查是否有检查点可以恢复
        checkpoint = self.session_manager.restore_checkpoint(session_id) if self.session_manager else None
        
        if checkpoint and checkpoint.get("execution_status") in ["running", "failed"]:
            self.logger.info(f"从检查点恢复执行，当前步骤: {checkpoint.get('current_step_idx', 0)}/{len(plan)}")
            # 从检查点恢复
            yield from self._resume_from_checkpoint(checkpoint, task, task_info, history, session_id, execution_id, stream)
        else:
            # 创建新的检查点
            checkpoint = self._create_initial_checkpoint(task, plan)
            self._save_plan_checkpoint(session_id, checkpoint)

            try:
                # 获取会话历史
                session_history = self.session_manager.get_history(session_id) if self.session_manager else history

                # 构建包含完整计划的任务信息
                enhanced_task_info = {
                    "level": "complex",
                    "description": task,
                    "plan": plan,
                    "plan_formatted": self._format_plan_for_prompt(plan),
                    "reason": task_info.get("reason", "复杂任务，需要多步骤执行")
                }

                # 调用父类方法执行完整计划
                # 父类ReActCore会根据提示词中的计划自行按步骤执行
                # 父类 _execute_task_stream 现在返回生成器
                final_result = None
                for chunk in super()._execute_task_stream(
                    task, plan, enhanced_task_info, session_history, session_id, execution_id, stream
                ):
                    # 转发所有流式事件
                    if stream:
                        yield chunk
                    
                    # 捕获最终结果
                    if chunk.get("type") == "task_end":
                        final_result = chunk.get("result", "任务执行完成")

                # 更新检查点
                checkpoint["current_step_idx"] = len(plan)
                checkpoint["execution_status"] = "completed"
                checkpoint["timestamp"] = time.time()
                self._save_plan_checkpoint(session_id, checkpoint)

            except Exception as e:
                import traceback
                self.logger.error(f"计划执行失败: {e}\n{traceback.format_exc()}")
                checkpoint["execution_status"] = "failed"
                checkpoint["error_info"] = str(e)
                checkpoint["timestamp"] = time.time()
                self._save_plan_checkpoint(session_id, checkpoint)

                if stream:
                    yield {"type": "error", "message": str(e)}

    def _resume_from_checkpoint(self, checkpoint: Dict[str, Any], task: str, task_info: Dict[str, Any],
                                history: List[Dict[str, str]], session_id: str,
                                execution_id: str, stream: bool) -> Generator[Dict[str, Any], None, None]:
        """从检查点恢复执行

        Args:
            checkpoint: 检查点数据
            task: 原始任务文本
            task_info: 任务信息
            history: 会话历史
            session_id: 会话ID
            execution_id: 执行ID
            stream: 是否流式输出

        Yields:
            流式响应块
        """
        plan = checkpoint.get("plan", [])
        current_step_idx = checkpoint.get("current_step_idx", 0)
        
        if current_step_idx >= len(plan):
            self.logger.warning("检查点显示任务已完成，无需恢复")
            yield {"type": "task_end", "result": checkpoint.get("result", "任务已完成")}
            return
        
        # 更新检查点状态
        checkpoint["execution_status"] = "running"
        checkpoint["timestamp"] = time.time()
        self._save_plan_checkpoint(session_id, checkpoint)
        
        try:
            # 获取会话历史
            session_history = self.session_manager.get_history(session_id) if self.session_manager else history

            # 构建包含完整计划的任务信息
            enhanced_task_info = {
                "level": "complex",
                "description": task,
                "plan": plan,
                "plan_formatted": self._format_plan_for_prompt(plan),
                "reason": task_info.get("reason", "复杂任务，需要多步骤执行"),
                "resume_from_step": current_step_idx
            }

            # 调用父类方法执行完整计划
            # 父类ReActCore会根据提示词中的计划自行按步骤执行
            final_result = None
            for chunk in super()._execute_task_stream(
                task, plan, enhanced_task_info, session_history, session_id, execution_id, stream
            ):
                # 转发所有流式事件
                if stream:
                    yield chunk
                
                # 捕获最终结果
                if chunk.get("type") == "task_end":
                    final_result = chunk.get("result", "任务执行完成")

            # 更新检查点
            checkpoint["current_step_idx"] = len(plan)
            checkpoint["execution_status"] = "completed"
            checkpoint["result"] = final_result
            checkpoint["timestamp"] = time.time()
            self._save_plan_checkpoint(session_id, checkpoint)

        except Exception as e:
            import traceback
            self.logger.error(f"恢复执行失败: {e}\n{traceback.format_exc()}")
            checkpoint["execution_status"] = "failed"
            checkpoint["error_info"] = str(e)
            checkpoint["timestamp"] = time.time()
            self._save_plan_checkpoint(session_id, checkpoint)

            if stream:
                yield {"type": "error", "message": str(e)}

    def _format_plan_for_prompt(self, plan: List[str]) -> str:
        """将计划格式化为提示词中的计划描述

        Args:
            plan: 计划步骤列表

        Returns:
            格式化后的计划文本
        """
        lines = ["任务执行计划："]
        for i, step in enumerate(plan, 1):
            lines.append(f"  步骤 {i}: {step}")
        lines.append("\n请按照上述计划逐步执行任务，每完成一个步骤后进行下一步。")
        return "\n".join(lines)

    def _summarize_results(self, task: str, results: List[str]) -> str:
        """汇总所有步骤的结果

        Args:
            task: 原始任务
            results: 各步骤结果列表

        Returns:
            汇总后的最终结果
        """
        if not results:
            return "任务执行完成，但未产生结果"

        if len(results) == 1:
            return results[0]

        prompt = f"""请汇总以下任务执行结果，生成简洁的最终回答。

原始任务：{task}

各步骤执行结果：
{chr(10).join(f'{i+1}. {r}' for i, r in enumerate(results))}

请直接输出汇总结果，不要包含其他说明："""

        return self.llm_client.complete(prompt, task_level="simple")

    def _execute_task_stream(self, task: str, task_info: Dict[str, Any], history: List[Dict[str, str]],
                           session_id: str, execution_id: str, stream: bool) -> Generator[Dict[str, Any], None, None]:
        """执行任务（流式）- 统一入口，智能路由

        Args:
            task: 任务文本
            task_info: 任务信息
            history: 会话历史
            session_id: 会话ID
            execution_id: 执行ID
            stream: 是否启用流式输出

        Yields:
            流式响应块
        """
        task_level = task_info.get("level", "simple")
        history_context = self._build_history_context(history)

        self.logger.debug(f"PlanReActCore处理任务: level={task_level}, task={task}")
        #self._publish_task_start(session_id, execution_id, task, task_info)
    
        analysis = self._analyze_task_and_plan(task, task_info, history_context, session_id, execution_id)
        
        if not analysis:
            self.logger.warning("任务分析失败，降级为父类执行")
            for chunk in super()._execute_task_stream(task, task_info, history, session_id, execution_id, stream):
                yield chunk
            return
        analyzed_level = analysis.get("level", "simple")
        next_action = analysis.get("next_action")
        plan = analysis.get("plan", [])

        self.logger.debug(f"分析结果: level={analyzed_level}, has_next_action={next_action is not None}, plan_steps={len(plan)}")

        if analyzed_level == "simple" and next_action:
            self.logger.debug("简单任务，直接执行next_action")

            for chunk in self._execute_direct_action(next_action, session_id, execution_id, task, stream):
                yield chunk
        elif plan:
            self.logger.debug("复杂任务，执行计划")

            self._publish_plan_start(session_id, execution_id)

            plan_descriptions = [step.get("description", str(step)) for step in plan]

            self._publish_plan_events(session_id, execution_id, plan_descriptions)

            # 调用 _execute_plan_steps 并透传所有 chunk
            for chunk in self._execute_plan_steps(
                plan_descriptions, task, task_info, history, session_id, execution_id, stream
            ):
                yield chunk
        else:
            self.logger.warning("无法处理任务，降级为父类执行")
            for chunk in super()._execute_task_stream(task, task_info, history, session_id, execution_id, stream):
                yield chunk

    def _execute_direct_action(self, action_data: Dict[str, Any], session_id: str, 
                               execution_id: str, task: str, stream: bool) -> Generator[Dict[str, Any], None, None]:
        """直接执行分析结果中的行动（减少简单任务的LLM调用）

        Args:
            action_data: 行动数据（包含 thought, action, action_input）
            session_id: 会话ID
            execution_id: 执行ID
            task: 原始任务
            stream: 是否流式输出

        Yields:
            流式响应块
        """
        thought = action_data.get("thought", "")
        action = action_data.get("action", "")
        action_input = action_data.get("action_input")

        self.logger.debug(f"直接执行行动: action={action}, thought={thought[:50]}...")
        self._publish_step_start(session_id, execution_id, 0, 1)
        if thought:
            self._publish_think_stream(session_id, execution_id, 0, thought)

        if action == "finish":
            result = action_input if isinstance(action_input, str) else str(action_input)
            self._publish_task_end(session_id, execution_id, result)
            if stream:
                yield {"type": "task_end", "result": result}
        else:
            observation = self._execute_action(action, action_input)
            self._publish_step_end(
                session_id, execution_id, 0,
                "completed", None, observation, thought, action
            )
            final_result = self._generate_final_response(task, [{"thought": thought, "action": action, "observation": observation}], "simple")
            self._publish_task_end(session_id, execution_id, final_result)
            if stream:
                yield {"type": "task_end", "result": final_result}

    def _resume_from_checkpoint(self, checkpoint: Dict[str, Any], history: List[Dict[str, str]] = None,
                               session_id: str = "default", stream: bool = False) -> Union[str, Generator[Dict[str, Any], None, None]]:
        """从检查点恢复执行

        Args:
            checkpoint: 检查点状态
            history: 会话历史
            session_id: 会话ID
            stream: 是否启用流式输出

        Returns:
            执行结果（非流式）或流式响应生成器（流式）
        """
        self.logger.debug(f"从检查点恢复执行，当前步骤：{checkpoint['current_step_idx']}")

        plan = checkpoint["plan"]
        current_step_idx = int(checkpoint["current_step_idx"])

        execution_id = f"plan_{int(time.time())}"
        task = checkpoint["task"]
        task_info = {"level": "complex", "reason": "从检查点恢复"}

        # 获取剩余计划步骤
        remaining_plan = plan[current_step_idx:]

        if stream:
            # 流式模式：返回生成器
            return self._execute_plan_steps(
                remaining_plan, task, task_info, history or [],
                session_id, execution_id, stream
            )
        else:
            # 非流式模式：直接执行并返回结果
            final_result = "任务恢复执行完成"
            result_gen = self._execute_plan_steps(
                remaining_plan, task, task_info, history or [],
                session_id, execution_id, stream
            )
            # 消费生成器获取结果
            try:
                for chunk in result_gen:
                    if chunk.get("type") == "task_end":
                        final_result = chunk.get("result", "任务恢复执行完成")
            except Exception as e:
                self.logger.error(f"恢复执行失败: {e}")
                return f"恢复执行失败: {str(e)}"
            return final_result
