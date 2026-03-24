"""异步 ReAct 引擎核心模块

完全异步化的 ReAct 引擎，解决 WebSocket 阻塞问题
"""

import json
import logging
import time
from typing import Dict, List, Optional, Any, Union
from collections.abc import AsyncGenerator
from lingxi.core.prompts.prompts import PromptTemplates
from lingxi.core.event import global_event_publisher
from lingxi.core.context.task_context import TaskContext
from lingxi.core.llm.async_llm_client import AsyncLLMClient
from lingxi.core.session.session_models import Step
from .base import BaseEngine
from lingxi.utils.config import get_workspace_path


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

        self.max_steps = int(config.get("engine", {}).get("max_steps", 50))
        self.timeout = int(config.get("engine", {}).get("timeout", 60))

        # 异步 LLM 客户端
        self.async_llm_client = AsyncLLMClient(config)

        self.logger = logging.getLogger(__name__)
        self.logger.debug("初始化异步 ReAct 推理引擎核心")

    async def close(self):
        """关闭异步资源"""
        await self.async_llm_client.close()

    

    def _build_initial_messages(self, context: TaskContext, history_context: str) -> List[
        Dict[str, Any]]:
        """构建初始消息

        Args:
            user_input: 用户输入
            task_plan: 任务计划列表
            task_info: 任务信息
            history_context: 历史上下文
            workspace_path: 工作目录路径（可选）

        Returns:
            消息列表
        """
        # 获取可用技能列表
        available_skills = self.skill_caller.list_available_skills(enabled_only=True) if self.skill_caller else []
        skills_list = PromptTemplates.format_skills_list(available_skills)

        # 获取系统信息
        system_info = PromptTemplates.get_system_info(get_workspace_path())
        
        # 格式化任务计划
        task_plan = context.task_info.plan
        # 处理 plan 可能是字符串的情况
        if isinstance(task_plan, str):
            try:
                import json
                task_plan = json.loads(task_plan)
            except (json.JSONDecodeError, TypeError):
                task_plan = []
        task_plan_str = PromptTemplates.format_task_plan(task_plan)

        # 使用build_react_messages_with_cache构建消息列表
        return PromptTemplates.build_react_messages_with_cache(
            context=context,
            history_context=history_context,
            skills_list=skills_list,
            #steps=[],
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
    def _build_step_messages(self, messages: List[Dict[str, Any]], history_context: str):
        """构建步骤消息

        Args:
            messages: 消息列表
            history_context: 历史上下文

        Returns:
            更新后的消息列表
        """
        history_part = f"""
"""
        steps_part = f"""历史上下文:
{history_context}\n
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
        stream: bool,
        thinking_mode: bool = False
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
            full_response = ""
            last_thought = ""
            last_usage = None
            self.logger.debug(f"发往 LLM 的消息: {messages}")
            async for chunk in self.async_llm_client.stream_chat(messages, task_level,enable_thinking=thinking_mode):
                if "usage" in chunk:
                    last_usage = chunk["usage"]
                
                choices = chunk.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})
                    
                    if "content" in delta:
                        content = delta["content"]
                        if content:
                            full_response += content
                            #from lingxi.utils.json_parser import extract_partial_json_field
                            #thought = extract_partial_json_field(full_response, "thought")
                            #if thought and thought != last_thought:
                                #last_thought = thought
                    
                    if "reasoning_content" in delta:
                        reasoning = delta["reasoning_content"]
                        if reasoning:
                            yield {
                                "type": "thought_chunk",
                                "content": reasoning
                            }

            self.logger.debug(f"准备发送 complete chunk，完整响应长度：{len(full_response)}")
            self.logger.debug(f"接收到LLM响应：{full_response if full_response else '空'}")
            
            if last_usage:
                self.logger.debug(f"Token 使用：{last_usage}")
            
            yield {
                "type": "complete",
                "response": full_response,
                "usage": last_usage
            }

        except Exception as e:
            self.logger.error(f"LLM 流式响应失败：{e}", exc_info=True)
            raise

    def _extract_json_fields(self, text: str) -> Optional[Dict[str, Any]]:
        """使用正则表达式从文本中提取JSON字段（处理格式不正确的JSON）"""
        import re
        import json
        result = {}

        # 提取 thought 字段（支持多行和包含引号的内容）
        thought_start = text.find('"thought"')
        if thought_start != -1:
            colon_pos = text.find(':', thought_start)
            if colon_pos != -1:
                first_quote = text.find('"', colon_pos)
                if first_quote != -1:
                    i = first_quote + 1
                    escape_next = False
                    while i < len(text):
                        char = text[i]
                        if escape_next:
                            escape_next = False
                            i += 1
                            continue
                        if char == '\\':
                            escape_next = True
                            i += 1
                            continue
                        if char == '"':
                            thought_value = text[first_quote + 1:i]
                            thought_value = thought_value.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
                            result['thought'] = thought_value
                            break
                        i += 1

        # 提取 description 字段
        desc_match = re.search(r'"description"\s*:\s*"([^"]*)"', text)
        if desc_match:
            result['description'] = desc_match.group(1)

        # 提取 action 字段
        action_match = re.search(r'"action"\s*:\s*"([^"]*)"', text)
        if action_match:
            result['action'] = action_match.group(1)

        # 提取 action_type 字段
        action_type_match = re.search(r'"action_type"\s*:\s*"([^"]*)"', text)
        if action_type_match:
            result['action_type'] = action_type_match.group(1)

        # 提取 action_input 字段
        action_input_start = text.find('"action_input"')
        if action_input_start != -1:
            colon_pos = text.find(':', action_input_start)
            if colon_pos != -1:
                i = colon_pos + 1
                while i < len(text) and text[i].isspace():
                    i += 1

                if i < len(text):
                    if text[i] == '{':
                        brace_count = 1
                        j = i + 1
                        while j < len(text) and brace_count > 0:
                            if text[j] == '{':
                                brace_count += 1
                            elif text[j] == '}':
                                brace_count -= 1
                            j += 1

                        action_input_str = text[i:j]
                        try:
                            action_input = json.loads(action_input_str)
                            result['action_input'] = action_input
                        except json.JSONDecodeError:
                            action_input = {}
                            cwd_match = re.search(r'"cwd"\s*:\s*"([^"]*)"', action_input_str)
                            if cwd_match:
                                action_input['cwd'] = cwd_match.group(1)
                            command_match = re.search(r'"command"\s*:\s*"([^"]*)"', action_input_str)
                            if command_match:
                                command = command_match.group(1)
                                command = command.replace('\\n', '\n').replace('\\t', '\t')
                                action_input['command'] = command
                            shell_type_match = re.search(r'"shell_type"\s*:\s*"([^"]*)"', action_input_str)
                            if shell_type_match:
                                action_input['shell_type'] = shell_type_match.group(1)
                            result['action_input'] = action_input
                    elif text[i] == '"':
                        second_quote = text.find('"', i + 1)
                        if second_quote != -1:
                            result['action_input'] = text[i + 1:second_quote]

        return result if result else None

    def _parse_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析 LLM 响应（支持 JSON 和文本两种格式）"""
        import json
        import re

        if not response:
            return None

        # 尝试 1: 解析 JSON 格式
        try:
            # 查找 JSON 对象的开始和结束
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                # 尝试直接解析
                try:
                    parsed = json.loads(json_str)
                    return parsed
                except json.JSONDecodeError as e:
                    self.logger.debug(f"JSON 直接解析失败，尝试清理转义字符：{e}")
                    try:
                        # 清理路径中的无效转义序列（如 \\w, \\工 等）
                        # 只保留有效的 JSON 转义序列
                        cleaned_json = re.sub(r'\\([^\\nrtbf"\'\\])', r'\\\\\1', json_str)
                        # 再次尝试解析
                        parsed = json.loads(cleaned_json)
                        return parsed
                    except Exception as cleanup_error:
                        self.logger.error(f"JSON 清理后仍然失败：{cleanup_error}")
                        # 如果清理后仍然失败，尝试更激进的清理
                        try:
                            # 移除所有无效的转义序列
                            aggressive_cleaned = re.sub(r'\\[^\\nrtbf"\'\\]', r'\\\\', json_str)
                            parsed = json.loads(aggressive_cleaned)
                            return parsed
                        except Exception as aggressive_error:
                            self.logger.error(f"激进清理后仍然失败：{aggressive_error}")
                            # 尝试使用正则表达式提取字段
                            self.logger.debug("尝试使用正则表达式提取JSON字段")
                            extracted = self._extract_json_fields(response)
                            if extracted:
                                return extracted
                            raise e
        except Exception as e:
            self.logger.error(f"JSON 格式解析失败：{e}，尝试文本格式", exc_info=True)
            return {"status": "error", "message": str(e)}

    async def _execute_step(    
        self,
        step_index: int,
        messages: List[Dict[str, Any]],
        task_level: str,
        context: TaskContext
    ) -> Dict[str, Any]:
        """执行单个步骤（异步）

        Args:
            step_index: 步骤索引
            messages: 消息列表
            task_level: 任务级别
            context: 任务上下文

        Returns:
            执行结果
        """
        session_id = context.session_id
        execution_id = context.execution_id
        stream = context.stream
        task_id = context.task_id
        thinking_mode = context.thinking_mode

        step = Step(
            step_id=f"{session_id}_{task_id}_{step_index}",
            session_id=session_id,
            task_id=task_id,
            step_index=step_index,
            description=f"步骤 {step_index}",
            step_type="call",
            result="",
        )

        context.steps.append(step)
        
        #self._build_step_messages(messages, steps)
        self._build_step_messages(messages, context.session_context.get_history_context())
        

        self.logger.debug(f"生成思考和行动（stream={stream}，thinking_mode={thinking_mode}）")
        self._publish_step_start(context, step_index, self.max_steps)

        full_response = ""
        usage = None
        self._publish_think_start(context, step_index, "")
        try:
            async for response_chunk in self._process_llm_response(messages, task_level, stream, thinking_mode):
                chunk_type = response_chunk["type"]
                
                if chunk_type == "thought_chunk":
                    content = response_chunk["content"]
                    self._publish_think_stream(context, step_index, content)
                    yield response_chunk
                elif chunk_type == "complete":
                    full_response = response_chunk["response"]
                    usage = response_chunk.get("usage")
                    self.logger.debug(f"收到完整响应，长度：{len(full_response) if full_response else 0}")
                    break
        except Exception as e:
            self.logger.error(f"处理LLM响应时出错：{e}", exc_info=True)
            step.status = "failed"
            step.error = str(e)
            step.result = str(e)
            step.description = str(e)
            self._publish_step_end(context, step_index)
            self._publish_task_failed(context, str(e))
            yield {"parsed": None, "usage": None}
            raise
        
        parsed = self._parse_response(full_response)
        self._publish_think_end(context, step_index, parsed.get("thought", "") if parsed else "")

        if not parsed:
            step.status = "failed"
            step.error = "解析响应失败"
            step.result = "解析响应失败"
            step.description = "解析响应失败"
            self._publish_step_end(context, step_index)
            yield {"parsed": parsed, "usage": None}
        elif parsed.get("status") == "error":
            step.status = "failed"
            step.error =  parsed.get("message", "")
            step.result = parsed.get("message", "")
            step.status = "failed"
            step.description =  parsed.get("message", "")    
            self._publish_step_end(context, step_index)
            yield {"parsed": parsed, "usage": None}
        elif parsed.get("action") == "finish":
            final_answer = parsed.get("action_input", "")
            step.status = "completed"
            step.result = final_answer
            step.skill_call = parsed.get("action", "")
            step.description = parsed.get("description", "")
            step.thought = parsed.get("thought", "")
            context.task_info.status = "completed"
            step.step_type = "finish"
            self._publish_step_end(context, step_index)
            #self._handle_finish_action(parsed, steps)
            yield {"parsed": parsed, "usage": usage}
        else:
            step.status = "completed"
            step.skill_call = parsed.get("action", "")
            step.description = parsed.get("description", "")
            step.thought = parsed.get("thought", "")
            step.step_type = "call"
            step.result_description = parsed.get("result_description", "")
            # 调用工具或者技能
            chunk = self._handle_step_complete(parsed, step_index)
            observation = chunk.get("observation", "")
            step.result = observation
            step.result_description = chunk.get("result_description", "")
            self._publish_step_end(context, step_index)
            yield {"parsed": parsed, "usage": usage}
        
    
        
        

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
        task_info = context.task_info
        stream = context.stream
        
        self.logger.debug(f"异步 ReAct 处理任务：{task_info.task_type} (stream={stream})")
        self.logger.debug(f"用户输入：{user_input}")

        task_level = task_info.task_type or "simple"
        history_context = context.session_context.get_history_context()
        messages = self._build_initial_messages(context, history_context)
        step_index = 0
        for step in range(self.max_steps):
            self.logger.debug(f"步骤 {step + 1}/{self.max_steps}")
            step_index = step + 1
            step_result = []
            async for chunk in self._execute_step(step_index, messages, task_level, context):
                if(chunk.get("parsed") is not None):
                    step_result = chunk
                else:
                    yield chunk
            if step_result and "usage" in step_result:
                usage = step_result["usage"]
                if usage:
                    input_tokens = getattr(usage, "prompt_tokens", 0)
                    output_tokens = getattr(usage, "completion_tokens", 0)
                    context.add_tokens(input_tokens, output_tokens)
                    self.logger.debug(f"步骤 {step + 1} Token 使用：input={input_tokens}, output={output_tokens}")
            if step_result and step_result.get("parsed") and step_result.get("parsed").get("action") == "finish":
                self.logger.debug("检测到 finish 动作，结束任务执行")
                final_answer = step_result.get("parsed").get("action_input", "")
                self._publish_task_end(final_answer, context)
                
                yield {"type": "task_finish", "result": final_answer}
                return
            else:
                yield step_result
        if(step_index >= self.max_steps):
            self._publish_task_end( "最大步骤数超过",context)
            yield {"type": "task_finish", "result": "最大步骤数超过"}
            #yield {"type": "task_finish", "result": ""}
            #res = step_result.get("parsed") if step_result else None

            #if res and res.get("action") == "finish":
            #    self.logger.debug("检测到 finish 动作，结束任务执行")
            #    final_answer = res.get("action_input", "")
            #    self._publish_task_end(final_answer, context)
                
            #    yield {"type": "task_finish", "result": final_answer}
            #    return

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
                if chunk.get("type") == "task_finish":
                    result = chunk.get("result", "")
            return result
