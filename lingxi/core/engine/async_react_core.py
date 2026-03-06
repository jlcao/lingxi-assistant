"""异步 ReAct 引擎核心模块

完全异步化的 ReAct 引擎，解决 WebSocket 阻塞问题
"""

import logging
import time
from typing import Dict, List, Optional, Any, Union
from collections.abc import AsyncGenerator
from lingxi.core.engine.base import BaseEngine
from lingxi.core.prompts import PromptTemplates
from lingxi.core.event import global_event_publisher
from lingxi.core.context import TaskContext
from lingxi.core.async_llm_client import AsyncLLMClient


class AsyncReActCore(BaseEngine):
    """异步 ReAct 引擎核心逻辑"""

    def __init__(self, config: Dict[str, Any], skill_caller=None, session_manager=None, websocket_manager=None):
        """初始化异步 ReAct 核心

        Args:
            config: 系统配置
            skill_caller: 技能调用器
            session_manager: 会话管理器
            websocket_manager: WebSocket 管理器
        """
        super().__init__(config, skill_caller, session_manager, websocket_manager)

        self.max_steps = int(config.get("engine", {}).get("max_steps", 10))
        self.timeout = int(config.get("engine", {}).get("timeout", 60))

        # 异步 LLM 客户端
        self.async_llm_client = AsyncLLMClient(config)

        self.logger = logging.getLogger(__name__)
        self.logger.debug("初始化异步 ReAct 推理引擎核心")

    async def close(self):
        """关闭异步资源"""
        await self.async_llm_client.close()

    def _build_history_context(self, history: List[Dict[str, Any]]) -> str:
        """构建历史上下文"""
        if not history:
            return ""
        
        context_lines = []
        for msg in history[-10:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            context_lines.append(f"{role}: {content}")
        
        return "\n".join(context_lines)

    def _build_initial_messages(self, user_input: str, task_plan: List[str], task_info: Dict[str, Any], history_context: str) -> List[
        Dict[str, Any]]:
        """构建初始消息

        Args:
            user_input: 用户输入
            task_plan: 任务计划列表
            task_info: 任务信息
            history_context: 历史上下文

        Returns:
            消息列表
        """
        # 获取可用技能列表
        available_skills = self.skill_caller.list_available_skills(enabled_only=True) if self.skill_caller else []
        skills_list = PromptTemplates.format_skills_list(available_skills)

        # 获取系统信息
        system_info = PromptTemplates.get_system_info()
        
        # 格式化任务计划
        task_plan_str = PromptTemplates.format_task_plan(task_plan)

        # 使用build_react_messages_with_cache构建消息列表
        return PromptTemplates.build_react_messages_with_cache(
            user_input=user_input,
            task_info=task_info,
            history_context=history_context,
            skills_list=skills_list,
            steps=[],
            system_info=system_info,
            task_plan=task_plan_str
        )

    def _build_step_messages(self, messages: List[Dict[str, Any]], steps: List[Dict[str, Any]]):
        """构建步骤消息

        Args:
            messages: 消息列表
            steps: 已执行步骤

        Returns:
            更新后的消息列表
        """
        executed_steps = PromptTemplates.format_executed_steps(steps, include_thought=False, max_prev_length=5000)
        steps_part = f"""已执行步骤:
{executed_steps}
现在请输出下一步:"""

        # 保留system消息中的信息，添加user消息
        if len(messages) == 1:
            messages.append({
                "role": "user",
                "content": [PromptTemplates.build_cached_text_content(steps_part, enable_cache=False)]
            })
        elif len(messages) >= 2:
            messages[-1] = {
                "role": "user",
                "content": [PromptTemplates.build_cached_text_content(steps_part, enable_cache=False)]
            }
        
        # 添加调试日志
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"构建步骤消息，消息数量: {len(messages)}")
        for i, msg in enumerate(messages):
            logger.debug(f"消息 {i}: role={msg['role']}, content={repr(str(msg['content'])[:200])}")
        
        return messages

    async def _process_llm_response(
        self,
        messages: List[Dict[str, Any]],
        task_level: str,
        stream: bool
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """处理 LLM 响应（异步流式）

        Args:
            messages: 消息列表
            task_level: 任务级别
            stream: 是否流式

        Yields:
            响应块
        """
        try:
            self.logger.debug(f"开始流式 LLM 调用")
            full_response = ""  # 收集完整响应
            last_thought = ""
            self.logger.debug(f"发往 LLM 的消息: {messages}")
            async for chunk in self.async_llm_client.stream_chat(messages, task_level):
                choices = chunk.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})
                    
                    if "content" in delta:
                        # 如果没有 thinking_delta，使用原始 content
                        content = delta["content"]
                        full_response += content  # 收集内容
                        from lingxi.utils.json_parser import extract_partial_json_field
                        thought = extract_partial_json_field(full_response, "thought")
                        if thought and thought != last_thought:
                            # 只输出增量的thought内容
                            incremental_thought = thought[len(last_thought):] if last_thought else thought
                            yield {
                                "type": "thought_chunk",
                                "content": incremental_thought
                            }
                            last_thought = thought
                      
                    
                    if "reasoning_content" in delta and delta["reasoning_content"]:
                        reasoning = delta["reasoning_content"]
                        full_response += reasoning  # 收集推理内容
                        self.logger.debug(f"推理块：{repr(reasoning[:50]) if len(reasoning) > 50 else repr(reasoning)}")
                        yield {
                            "type": "reasoning_chunk",
                            "content": reasoning
                        }

            # 收集 usage 信息
            self.logger.debug(f"准备发送 complete chunk，完整响应长度：{len(full_response)}")
            self.logger.debug(f"接收到LLM响应：{full_response if full_response else '空'}")
            
            if self.async_llm_client.last_usage:
                self.logger.debug(f"Token 使用：{self.async_llm_client.last_usage}")
            
            yield {
                "type": "complete",
                "response": full_response,  # 返回完整响应
                "usage": self.async_llm_client.last_usage
            }

        except Exception as e:
            self.logger.error(f"LLM 流式响应失败：{e}", exc_info=True)
            raise

    def _parse_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析 LLM 响应（支持 JSON 和文本两种格式）"""
        import json
        import re
        
        if not response:
            return None

        # 尝试 1: 解析 JSON 格式
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                parsed = json.loads(json_str)
                
                if "thought" in parsed and "action" in parsed:
                    parsed["description"] = parsed.get("thought", "")
                    return parsed
        except Exception as e:
            self.logger.debug(f"JSON 格式解析失败：{e}，尝试文本格式")
        
        # 尝试 2: 解析文本格式 (ReAct 标准格式)
        # Thought: ...\nAction: ...\nAction Input: {...}
        try:
            thought_match = re.search(r'Thought:\s*(.*?)(?=\nAction:|$)', response, re.DOTALL)
            action_match = re.search(r'Action:\s*(\w+)', response)
            action_input_match = re.search(r'Action Input:\s*(\{.*?\})', response, re.DOTALL)
            
            if thought_match and action_match:
                thought = thought_match.group(1).strip()
                action = action_match.group(1).strip()
                
                # 提取 action_input（JSON 格式）
                action_input = {}
                if action_input_match:
                    try:
                        action_input_str = action_input_match.group(1)
                        # 替换单引号为双引号
                        action_input_str = action_input_str.replace("'", '"')
                        # 处理路径中的反斜杠转义问题
                        action_input_str = re.sub(r'\\\\+', r'\\', action_input_str)
                        action_input = json.loads(action_input_str)
                    except Exception as e:
                        self.logger.debug(f"解析 Action Input 失败：{e}")
                
                return {
                    "thought": thought,
                    "action": action,
                    "action_input": action_input,
                    "description": thought
                }
        except Exception as e:
            self.logger.warning(f"文本格式解析失败：{e}")
        
        return None

    def _execute_action(self, action: str, action_input: Any) -> str:
        """执行行动（同步，在线程池中调用）"""
        if action == "finish":
            return action_input if isinstance(action_input, str) else str(action_input)
        
        try:
            if self.skill_caller:
                result = self.skill_caller.call(action, action_input if isinstance(action_input, dict) else {})
                if result.get("success"):
                    return result.get("result", "执行成功")
                else:
                    return f"执行失败：{result.get('error', '未知错误')}"
            else:
                return f"技能调用器未初始化"
        except Exception as e:
            self.logger.error(f"执行行动失败：{e}")
            return f"执行失败：{str(e)}"

    async def _execute_step(
        self,
        step: int,
        messages: List[Dict[str, Any]],
        task_level: str,
        steps: List[Dict[str, Any]],
        context: TaskContext
    ) -> Dict[str, Any]:
        """执行单个步骤（异步）

        Args:
            step: 步骤索引
            messages: 消息列表
            task_level: 任务级别
            steps: 已执行步骤
            context: 任务上下文

        Returns:
            执行结果
        """
        session_id = context.session_id
        execution_id = context.execution_id
        stream = context.stream
        task_id = context.task_id
        
        self._build_step_messages(messages, steps)

        self.logger.debug(f"生成思考和行动（stream={stream}")

        full_response = ""
        usage = None
        
        async for response_chunk in self._process_llm_response(messages, task_level, stream):
            chunk_type = response_chunk["type"]
            
            if chunk_type == "thought_chunk":
                content = response_chunk["content"]
                self._publish_think_stream(session_id, execution_id, step, content)
            elif chunk_type == "complete":
                full_response = response_chunk["response"]
                usage = response_chunk.get("usage")
                self.logger.debug(f"收到完整响应，长度：{len(full_response) if full_response else 0}")
                break

        parsed = self._parse_response(full_response)

        if not parsed:
            self.logger.error(f"LLM 响应解析失败！完整响应：{repr(full_response)}")
            thought = ""
            description = ""
            self._publish_step_end(
                session_id, execution_id, step, "failed", None,
                "无法解析 LLM 响应", thought,
                description, task_id
            )
            self._publish_task_failed(session_id, execution_id, "无法解析 LLM 响应", task_id)
            return {"parsed": parsed, "usage": usage}

        if parsed.get("action") == "finish":
            final_answer = parsed.get("action_input", "")
            self._publish_step_end(
                session_id, execution_id, step, "completed", None,
                final_answer, parsed.get("thought"),
                parsed.get("description", ""), task_id
            )
            self._handle_finish_action(parsed, steps)
            return {"parsed": parsed, "usage": usage}

        chunk = self._handle_step_complete(parsed, step)
        observation = chunk.get("observation", "")
        self._publish_step_end(
            session_id, execution_id, step, "completed", None,
            observation, parsed.get("thought"),
            parsed.get("description", ""), task_id
        )
        return {"parsed": parsed, "usage": usage}

    async def _execute_task_stream(
        self,
        context: TaskContext
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """执行任务（异步流式）

        Args:
            context: 任务上下文

        Yields:
            流式响应块
        """
        user_input = context.user_input
        task_plan = context.task_info.get("plan", [])
        task_info = context.task_info
        history = context.session_history
        session_id = context.session_id
        execution_id = context.execution_id
        stream = context.stream
        task_id = context.task_id
        
        self.logger.debug(f"异步 ReAct 处理任务：{task_info.get('task_type')} (stream={stream})")
        self.logger.debug(f"用户输入：{user_input}")

        task_level = task_info.get("level", "simple")
        history_context = self._build_history_context(history)
        messages = self._build_initial_messages(user_input, task_plan, task_info, history_context)
        steps = []
        
        total_input_tokens = 0
        total_output_tokens = 0

        for step in range(self.max_steps):
            self.logger.debug(f"步骤 {step + 1}/{self.max_steps}")
            self._publish_step_start(session_id, execution_id, step, self.max_steps)
            
            step_result = await self._execute_step(
                step, messages, task_level, steps, context
            )
            
            if step_result and "usage" in step_result:
                usage = step_result["usage"]
                if usage:
                    input_tokens = getattr(usage, "prompt_tokens", 0)
                    output_tokens = getattr(usage, "completion_tokens", 0)
                    total_input_tokens += input_tokens
                    total_output_tokens += output_tokens
                    self.logger.debug(f"步骤 {step + 1} Token 使用：input={input_tokens}, output={output_tokens}")
            
            res = step_result.get("parsed") if step_result else None
            steps.append(res)

            if res and res.get("action") == "finish":
                self.logger.debug("检测到 finish 动作，结束任务执行")
                self._publish_task_end(session_id, execution_id, res.get("action_input", ""), task_id)
                
                if task_id:
                    self.session_manager.update_task_tokens(task_id, total_input_tokens, total_output_tokens)
                    self.session_manager.update_session_tokens(session_id, total_input_tokens, total_output_tokens)
                    self.logger.debug(f"任务 Token 总计：input={total_input_tokens}, output={total_output_tokens}")
                
                yield {"type": "task_end", "result": res.get("action_input", "")}
                return

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
        self.logger.debug(f"异步 ReAct 处理任务：{context.get_task_level()} (stream={context.stream})")
        
        if context.stream:
            return self._execute_task_stream(context)
        else:
            # 非流式模式：收集所有结果
            result = None
            async for chunk in self._execute_task_stream(context):
                if chunk.get("type") == "task_end":
                    result = chunk.get("result", "")
            return result
