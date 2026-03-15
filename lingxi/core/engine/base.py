import logging
import time
import json
import uuid
import threading
import asyncio
import re
from typing import Dict, List, Optional, Any, Union, Generator, TYPE_CHECKING
from lingxi.core.llm.llm_client import LLMClient
from lingxi.core.soul import SoulInjector
from lingxi.core.skill_caller import SkillCaller
from lingxi.core.prompts.prompts import PromptTemplates
from lingxi.core.event import global_event_publisher
from lingxi.core.context import TaskContext
from lingxi.core.utils.security import SecurityError
from lingxi.core.confirmation.confirmation import ConfirmationManager, DangerousSkillChecker, RiskLevel
from lingxi.core.memory import MemorySearch
from .utils import parse_llm_response, parse_action_parameters, process_parameters, calculate_expression
from lingxi.utils.json_parser import stream_with_thought_only

if TYPE_CHECKING:
    from lingxi.core.session import SessionManager

class BaseEngine:
    """引擎基类，提供公共功能"""

    def __init__(self, config: Dict[str, Any], skill_caller: SkillCaller = None, session_manager: 'SessionManager' = None, websocket_manager=None):
        """初始化引擎

        Args:
            config: 系统配置
            skill_caller: 技能调用器
            session_manager: 会话管理器
            websocket_manager: WebSocket管理器（已弃用，使用事件系统）
        """
        self.config = config
        self.skill_caller = skill_caller
        self.session_manager = session_manager
        self.websocket_manager = websocket_manager
        self.llm_client = LLMClient(config)
        self.logger = logging.getLogger(__name__)
        
        # 初始化 SOUL 注入器
        workspace_path = config.get("workspace", {}).get("default_path", "./workspace")
        self.soul_injector = SoulInjector(workspace_path)
        self.soul_injector.load()
        self.logger.debug("BaseEngine: SOUL 注入器已初始化")
        
        # 初始化确认管理器（V4.0新增）
        security_config = config.get("security", {})
        self.confirmation_manager = ConfirmationManager(
            timeout=security_config.get("confirmation_timeout", 60),
            auto_reject_timeout=security_config.get("auto_reject_timeout", True)
        )
        
        # 子代理调度器（从 skill_caller 获取）
        self.subagent_scheduler = None
        if hasattr(skill_caller, "subagent_scheduler"):
            self.subagent_scheduler = skill_caller.subagent_scheduler
            self.logger.debug("子代理调度器已启用")
        
        # 记忆搜索
        if session_manager and hasattr(session_manager, 'memory_manager'):
            self.memory_search = MemorySearch(session_manager.memory_manager)
        else:
            self.memory_search = None
        
        self.logger.debug("BaseEngine: 记忆搜索已初始化")

    def process(self, context: TaskContext) -> Union[str, Generator[Dict[str, Any], None, None]]:
        """处理用户输入

        Args:
            context: 任务上下文对象

        Returns:
            系统响应（非流式）或流式响应生成器（流式）
        """
        return self._process_with_context(context)
    
    def _process_with_context(self, context: TaskContext) -> Union[str, Generator[Dict[str, Any], None, None]]:
        """使用TaskContext处理用户输入

        Args:
            context: 任务上下文对象

        Returns:
            系统响应（非流式）或流式响应生成器（流式）
        """
        raise NotImplementedError("子类必须实现 _process_with_context 方法")

    def _build_history_context(self, session_history: List[Dict[str, str]]) -> str:
        """构建历史上下文

        Args:
            session_history: 会话历史

        Returns:
            历史上下文字符串
        """
        return PromptTemplates.format_history_context(session_history, max_count=5)

    def _parse_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析LLM响应

        Args:
            response: LLM响应

        Returns:
            解析后的字典
        """
        self.logger.debug(f"开始解析LLM响应: {repr(response)}")
        parsed = parse_llm_response(response)
        if parsed:
            self.logger.debug(f"解析成功: thought={parsed['thought'][:30]}..., action={parsed['action']}")
        else:
            self.logger.warning(f"解析失败，响应内容: {repr(response)}")
        return parsed

    def _execute_action(self, action: str, action_input: Any) -> str:
        """执行行动

        Args:
            action: 行动名称
            action_input: 行动输入（可以是字符串或字典）

        Returns:
            观察结果
        """
        if action == "finish":
            return action_input

        if not self.skill_caller:
            return f"错误: 技能调用器未初始化"

        try:
            # 如果 action_input 是字符串，尝试解析为参数字典
            if isinstance(action_input, str):
                parameters = self._parse_action_parameters(action_input)
                parameters = self._process_parameters(parameters)
            else:
                # action_input 已经是字典（对象）
                parameters = action_input if isinstance(action_input, dict) else {}
            
            # 检查是否为高危操作（V4.0新增）
            skill_risk = DangerousSkillChecker.check_skill_risk(action)
            command_risk = RiskLevel.LOW
            
            if action == "system.exec" and isinstance(parameters.get("command"), str):
                command_risk = DangerousSkillChecker.check_command_risk(parameters["command"])
            
            # 如果是高危操作，需要用户确认
            if skill_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL] or command_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                self.logger.info(f"检测到高危操作: {action}, 风险级别: {skill_risk.value if skill_risk != RiskLevel.LOW else command_risk.value}")
                
                # 创建确认请求
                request = self.confirmation_manager.create_request(
                    operation=action,
                    description=f"参数: {parameters}",
                    risk_level=skill_risk if skill_risk != RiskLevel.LOW else command_risk,
                    metadata={"parameters": parameters}
                )
                
                # 发送确认请求事件
                global_event_publisher.publish(
                    "require_confirmation",
                    {
                        "request_id": request.request_id,
                        "operation": action,
                        "description": f"参数: {parameters}",
                        "risk_level": request.risk_level.value,
                        "timeout": request.timeout
                    }
                )
                
                # 等待用户确认
                try:
                    confirmed = asyncio.run(self.confirmation_manager.wait_for_confirmation(request.request_id))
                    
                    if not confirmed:
                        self.logger.warning(f"用户拒绝高危操作: {action}")
                        return f"{action} 操作已被用户拒绝"
                    
                    self.logger.info(f"用户确认高危操作: {action}")
                except Exception as e:
                    self.logger.error(f"等待确认失败: {e}")
                    return f"{action} 确认失败: {str(e)}"
            
            # 使用带安全检查的技能调用
            result = self.skill_caller.call_with_security_check(
                action,
                parameters,
                require_confirmation=False
            )

            if result.get("success"):
                return action + " " + result.get("result", "执行成功")
            else:
                error_msg = result.get('error', '未知错误')
                error_code = result.get('error_code', '')
                
                # 如果是安全错误，返回详细信息
                if error_code:
                    return f"{action} 执行失败: {error_msg} (错误码: {error_code})"
                else:
                    return action + " " + f"执行失败: {error_msg}"
        except SecurityError as e:
            self.logger.error(f"安全检查失败: {e}")
            return f"{action} 安全检查失败: {str(e)} (错误码: {e.error_code})"
        except Exception as e:
            self.logger.error(f"执行行动失败: {e}")
            return action + " " + f"执行失败: {str(e)}"

    def _parse_action_parameters(self, action_input: str) -> Dict[str, Any]:
        """解析行动参数

        Args:
            action_input: 行动输入字符串

        Returns:
            参数字典
        """
        self.logger.debug(f"开始解析 action_input，长度: {len(action_input)}")
        parameters = parse_action_parameters(action_input)
        self.logger.debug(f"解析结果: {len(parameters)} 个参数")
        return parameters

    def _process_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """处理参数，转换转义字符

        Args:
            parameters: 原始参数字典

        Returns:
            处理后的参数字典
        """
        return process_parameters(parameters)

    def _calculate(self, expression: str) -> str:
        """计算表达式

        Args:
            expression: 数学表达式

        Returns:
            计算结果
        """
        return calculate_expression(expression)

    def _generate_final_response(self, task: str, results: List[Dict[str, Any]], task_level: str = "simple") -> str:
        """生成最终响应

        Args:
            task: 任务文本
            results: 执行结果
            task_level: 任务级别

        Returns:
            最终响应
        """
        prompt = PromptTemplates.build_final_response_prompt(
            user_input=task,
            steps=results,
            include_thought=False
        )

        self.logger.debug("生成最终响应提示词: %s", prompt)
        response = self.llm_client.complete(prompt, task_level=task_level)
        self.logger.debug("最终响应LLM响应: %s", response)
        return response

    def _generate_error_response(self, task: str, failed_step: int, error: str) -> str:
        """生成错误响应

        Args:
            task: 任务文本
            failed_step: 失败的步骤
            error: 错误信息

        Returns:
            错误响应
        """
        return f"任务执行失败：在步骤{failed_step + 1}时遇到错误\n\n错误信息：{error}\n\n您可以使用相同的会话ID重新尝试，系统将从失败的步骤继续执行。"

    def _build_step_messages(self, messages: List[Dict[str, Any]], steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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

    def _inject_soul_to_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """注入 SOUL 到消息列表
        
        Args:
            messages: 消息列表
            
        Returns:
            注入后的消息列表
        """
        if not hasattr(self, 'soul_injector') or not self.soul_injector.soul_data:
            return messages

    def _should_use_subagent(self, task: str, context: dict = None) -> bool:
        """
        检测是否需要使用子代理
        
        Args:
            task: 任务描述
            context: 上下文
        
        Returns:
            是否需要子代理
        """
        # 1. 检测关键词（并行/多任务意图）
        parallel_keywords = [
            "并行", "同时", "一起", "分别", "各自",
            "多个", "几个", "每个",
            "分析...和...", "对比...和...",
            "第一部分...第二部分...", "首先...然后..."
        ]
        
        for keyword in parallel_keywords:
            if keyword in task:
                self.logger.debug(f"检测到并行意图关键词：{keyword}")
                return True
        
        # 2. 检测任务复杂度（长度超过阈值）
        if len(task) > 200:
            self.logger.debug("任务较长，可能需要分解")
            return True
        
        # 3. 检测上下文中的子代理请求
        if context:
            if isinstance(context, dict):
                if context.get("use_subagent") is True:
                    return True
                if context.get("parallel") is True:
                    return True
        
        # 4. 检测任务列表格式（使用换行符检测）
        if chr(10) in task:  # chr(10) is newline character
            lines = [l.strip() for l in task.split(chr(10)) if l.strip()]
            if len(lines) > 1:
                self.logger.debug(f"检测到多行任务，共{len(lines)}行")
                return True
        
        return False
    
    def _decompose_task(self, task: str, context: dict = None) -> List[str]:
        """
        分解任务为子任务
        
        Args:
            task: 原始任务
            context: 上下文
        
        Returns:
            子任务列表
        """
        # 1. 按换行符分解
        if chr(10) in task:
            subtasks = [l.strip() for l in task.split(chr(10)) if l.strip()]
            if len(subtasks) > 1:
                return subtasks
        
        # 2. 按逗号/分号分解
        if ',' in task or '，' in task:
            subtasks = [t.strip() for t in re.split(r'[,，]', task) if t.strip()]
            if len(subtasks) > 1:
                return subtasks
        
        # 3. 按"和"、"与"分解
        if '和' in task or '与' in task:
            subtasks = [t.strip() for t in re.split(r'[和与]', task) if t.strip()]
            if len(subtasks) > 1:
                return subtasks
        
        # 4. 默认：不分解，返回原任务
        return [task]
    
    def _aggregate_subagent_results(self, results: List) -> str:
        """
        聚合子代理结果
        
        Args:
            results: 子代理结果列表
        
        Returns:
            聚合后的结果字符串
        """
        aggregated = []
        
        for i, result in enumerate(results, 1):
            if hasattr(result, 'result'):
                aggregated.append(f"【子任务{i}】" + chr(10) + str(result.result))
            elif isinstance(result, dict) and 'result' in result:
                aggregated.append(f"【子任务{i}】" + chr(10) + result['result'])
            else:
                aggregated.append(f"【子任务{i}】" + chr(10) + str(result))
        
        return chr(10) + chr(10).join(aggregated)


        # 构建 SOUL 系统提示词
        soul_prompt = self.soul_injector.build_system_prompt("")
        
        # 查找现有的系统消息
        for i, msg in enumerate(messages):
            if msg.get("role") == "system":
                # 在现有系统消息后追加 SOUL 内容
                original_content = msg.get("content", "")
                messages[i]["content"] = f"{original_content}\n\n{soul_prompt}"
                self.logger.debug(f"SOUL 已注入到系统消息 (索引 {i})")
                return messages
        
        # 如果没有系统消息，在开头添加
        messages.insert(0, {
            "role": "system",
            "content": soul_prompt
        })
        self.logger.debug("SOUL 已作为新系统消息添加")
        return messages


    def _get_json_schema(self) -> Dict[str, Any]:
        """获取JSON Schema

        Returns:
            JSON Schema
        """
        return {
            "name": "action_plan",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "thought": {
                        "type": "string",
                        "description": "你的思考过程，这部分需要流式展示给用户"
                    },
                    "action": {
                        "type": "string",
                        "description": "行动名称"
                    },
                    "action_input": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": True
                    }
                },
                "required": ["thought", "action", "action_input"],
                "additionalProperties": False
            }
        }

    def _publish_think_stream(self, session_id: str, execution_id: str, step: int, content: str):
        """发布思考流式事件

        Args:
            session_id: 会话 ID
            execution_id: 执行 ID
            step: 步骤索引
            content: 思考内容
        """
        global_event_publisher.publish(
            'think_stream',
            session_id=session_id,
            execution_id=execution_id,
            step_index=step,
            content=content,
            body={"reasoning_content": content},
            is_partial=True
        )

    def _publish_think_start(self, session_id: str, execution_id: str, step: int, content: str):
        """发布思考开始事件

        Args:
            session_id: 会话 ID
            execution_id: 执行 ID
            step: 步骤索引
            content: 初始思考内容
        """
        global_event_publisher.publish(
            'think_start',
            session_id=session_id,
            execution_id=execution_id,
            step_index=step,
            content=content
        )

    def _publish_think_end(self, session_id: str, execution_id: str, step: int, content: str):
        """发布思考结束事件

        Args:
            session_id: 会话 ID
            execution_id: 执行 ID
            step: 步骤索引
            content: 最终思考内容
        """
        global_event_publisher.publish(
            'think_end',
            session_id=session_id,
            execution_id=execution_id,
            step_index=step,
            content=content
        )

    def _publish_step_start(self, session_id: str, execution_id: str, step_idx: int, total_steps: int):
        """发布步骤开始事件

        Args:
            session_id: 会话ID
            execution_id: 执行ID
            step_idx: 步骤索引
            total_steps: 总步骤数
        """
        global_event_publisher.publish(
            'step_start',
            session_id=session_id,
            execution_id=execution_id,
            step_index=step_idx,
            total_steps=total_steps
        )

    def _publish_step_end(self, session_id: str, execution_id: str, step_idx: int, status: str, error: str = None, result: str = "", thought: str = "",description:str="", task_id: str = None):
        """发布步骤结束事件

        Args:
            session_id: 会话 ID
            execution_id: 执行 ID
            step_idx: 步骤索引
            status: 状态
            error: 错误信息
            result: 结果
            task_id: 任务 ID
        """
        global_event_publisher.publish(
            'step_end',
            session_id=session_id,
            execution_id=execution_id,
            task_id=task_id,
            step_index=step_idx,
            status=status,
            error=error,
            result=result,
            thought=thought,
            description=description
        )

    def _publish_task_end(self, result: str, context: TaskContext):
        """发布任务结束事件

        Args:
            result: 结果
            context: 任务上下文
        """
        global_event_publisher.publish(
            'task_end',
            session_id=context.session_id,
            execution_id=context.execution_id,
            task_id=context.task_id,
            task_input=context.user_input,
            result=result,
            task_level=context.get_task_level(),
            input_tokens=context.input_tokens,
            output_tokens=context.output_tokens
        )
        
        return {
            "type": "task_end",
            "result": result
        }
    def _publish_task_failed(self, session_id: str, execution_id: str, error: str, task_id: str = None):
        """发布任务失败事件

        Args:
            session_id: 会话 ID
            execution_id: 执行 ID
            error: 错误信息
            task_id: 任务 ID
        """
        global_event_publisher.publish(
            'task_failed',
            session_id=session_id,
            execution_id=execution_id,
            task_id=task_id,
            error=error
        )

    def _publish_plan_start(self, session_id: str, execution_id: str, task_id: str = None, task_level: str = "none"):
        """发布计划开始事件

        Args:
            session_id: 会话ID
            execution_id: 执行ID
            task_id: 任务ID
            task_level: 任务级别
        """
        global_event_publisher.publish(
            'plan_start',
            session_id=session_id,
            execution_id=execution_id,
            task_id=task_id,
            task_level=task_level
        )

    def _publish_plan_events(self, session_id: str, execution_id: str, plan: List[str], task_id: str = None):
        """发布计划相关事件

        Args:
            session_id: 会话ID
            execution_id: 执行ID
            plan: 计划步骤列表
            task_id: 任务ID
        """
        global_event_publisher.publish(
            'plan_final',
            session_id=session_id,
            execution_id=execution_id,
            task_id=task_id,
            plan=[{"step": i+1, "description": step} for i, step in enumerate(plan)]
        )

    def handle_confirmation_response(self, request_id: str, confirmed: bool, reason: Optional[str] = None) -> bool:
        """处理客户端确认响应（V4.0新增）

        Args:
            request_id: 确认请求ID
            confirmed: 是否确认
            reason: 拒绝原因（可选）

        Returns:
            是否成功处理
        """
        if not hasattr(self, 'confirmation_manager'):
            self.logger.warning("确认管理器未初始化")
            return False
        
        success = self.confirmation_manager.respond_confirmation(request_id, confirmed, reason)
        
        if success:
            self.logger.debug(f"确认响应处理成功: request_id={request_id}, confirmed={confirmed}")
        else:
            self.logger.warning(f"确认响应处理失败: request_id={request_id}")
        
        return success

    def _process_llm_response(self, messages: List[Dict[str, Any]], task_level: str, stream: bool) -> Generator[Dict[str, Any], None, None]:
        """处理LLM响应

        Args:
            messages: 消息列表
            task_level: 任务级别
            stream: 是否流式输出

        Returns:
            流式响应生成器
        """
        # 注入 SOUL 到消息列表
        messages = self._inject_soul_to_messages(messages)

        # 添加调试日志
        self.logger.debug(f"处理LLM响应，消息数量: {len(messages)}")
        for i, msg in enumerate(messages):
            self.logger.debug(f"消息 {i}: role={msg['role']}, content={repr(str(msg['content'])[:200])}")
        
        json_schema = self._get_json_schema()

        if stream:
            stream_response = self.llm_client.stream_chat_complete_with_cache(
                messages,
                task_level=task_level,
                response_format={"type": "json_schema", "json_schema": json_schema}
            )

            full_response = ""
            last_thought = ""
            for chunk in stream_response:
                if hasattr(chunk, 'choices') and chunk.choices:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        content = delta.content
                        full_response += content
                        # 尝试提取thought字段
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
            
            yield {
                "type": "complete",
                "response": full_response
            }
        else:
            result = self.llm_client.chat_complete_with_cache(messages, task_level=task_level)
            
            # 如果返回的是元组，说明包含 usage 信息
            if isinstance(result, tuple):
                response, usage = result
                self.logger.debug(f"LLM 响应包含 Token 使用信息: {usage}")
            else:
                response = result
                usage = None
            
            yield {
                "type": "complete",
                "response": response,
                "usage": usage
            }

    def _handle_finish_action(self, parsed: Dict[str, Any], steps: List[Dict[str, Any]]):
        """处理finish行动

        Args:
            parsed: 解析后的响应
            steps: 已执行步骤
        """
        self.logger.debug("任务完成")
        final_answer = parsed.get("thought", "") + " " + parsed.get("observation", "")
        steps.append(parsed)

    def _handle_step_complete(self, parsed: Dict[str, Any], step: int) -> Dict[str, Any]:
        """处理步骤完成

        Args:
            parsed: 解析后的响应
            step: 步骤索引

        Returns:
            步骤完成信息
        """
        observation = self._execute_action(parsed.get("action"), parsed.get("action_input"))
        parsed["observation"] = observation

        self.logger.debug(f"思考: {parsed.get('thought')}")
        self.logger.debug(f"行动: {parsed.get('action')} - {parsed.get('action_input')}")
        self.logger.debug(f"观察: {observation.replace(chr(10), chr(92) + 'n')}")

        return {
            "type": "step_complete",
            "step": step,
            "thought": parsed.get('thought'),
            "action": parsed.get('action'),
            "action_input": parsed.get('action_input'),
            "observation": observation,
            "success": True
        }

    def _execute_task_stream(self, context: TaskContext) -> Generator[Dict[str, Any], None, None]:
        """执行任务

        Args:
            context: 任务上下文对象

        Returns:
            响应生成器
        """
        raise NotImplementedError("子类必须实现 _execute_task_stream 方法")

    def _execute_new_task(self, context: TaskContext) -> Union[str, Generator[Dict[str, Any], None, None]]:
        """执行新任务（统一使用流式处理逻辑）

        Args:
            context: 任务上下文对象

        Returns:
            执行结果（非流式）或流式响应生成器（流式）
        """
        try:
            task = context.user_input
            task_info = context.task_info
            history = context.session_history
            session_id = context.session_id
            stream = context.stream
            task_id = context.task_id
            execution_id = context.execution_id
            
            self.logger.debug(f"开始执行新任务：{task} (stream={stream})")
            
            self.logger.debug(f"任务 ID：{task_id}")
            self.logger.debug(f"执行 ID：{execution_id}")
            
            self._publish_task_start(session_id, execution_id, task, task_info, task_id)

            if stream:
                return self._execute_task_stream(context)
            else:
                for _ in self._execute_task_stream(context):
                    pass
                return ""

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            error_message = str(e)
            self.logger.error(f"执行新任务时发生异常: {error_message}\n{error_trace}")
            if stream:
                def error_generator():
                    yield {"type": "error", "message": f"{error_message}\n堆栈信息:\n{error_trace}"}
                return error_generator()
            return self._generate_error_response(task, -1, f"{error_message}\n堆栈信息:\n{error_trace}")

    def _handle_task_completion(self, checkpoint: Dict[str, Any], all_results: List[Dict[str, Any]], 
                              context: TaskContext) -> Generator[Dict[str, Any], None, None]:
        """处理任务完成

        Args:
            checkpoint: 检查点
            all_results: 所有结果
            context: 任务上下文

        Returns:
            流式响应生成器
        """
        session_id = context.session_id
        execution_id = context.execution_id
        task = context.user_input
        task_level = context.get_task_level()
        
        checkpoint["execution_status"] = "completed"
        checkpoint["error_info"] = None
        if hasattr(self, "_save_plan_checkpoint"):
            self._save_plan_checkpoint(session_id, checkpoint)

        # 检查最后一个步骤是否是 finish 动作
        final_response = ""
        if all_results and all_results[-1].get("action") == "finish":
            # 如果最后一个步骤是 finish，直接使用 finish 的内容
            finish_step = all_results[-1]
            final_response = finish_step.get("action_input", "")
            if not final_response:
                # 如果 action_input 为空，尝试使用 thought 和 observation
                final_response = finish_step.get("thought", "") + " " + finish_step.get("observation", "")
        else:
            # 否则调用模型生成最终响应
            final_response = self._generate_final_response(task, all_results, task_level)

        self._publish_task_end(final_response, context)

    def _handle_step_failure(self, step_result: Dict[str, Any], checkpoint: Dict[str, Any],
                           session_id: str, execution_id: str, step_idx: int, task: str):
        """处理步骤失败

        Args:
            step_result: 步骤结果
            checkpoint: 检查点
            session_id: 会话ID
            execution_id: 执行ID
            step_idx: 步骤索引
            task: 任务文本
        """
        self.logger.error(f"步骤{step_idx + 1}执行失败: {step_result.get('error')}")

        checkpoint["execution_status"] = "failed"
        checkpoint["error_info"] = step_result.get("error")
        if hasattr(self, "_save_plan_checkpoint"):
            self._save_plan_checkpoint(session_id, checkpoint)

        if self.session_manager:
            error_response = self._generate_error_response(task, step_idx, step_result.get("error"))
            
    def _should_search_memory(self, task: str) -> bool:
        """检测是否需要搜索记忆"""
        keywords = [
            "我记得", "你记得", "之前说过", "上次", "以前",
            "偏好", "习惯", "喜欢", "讨厌",
            "记住", "别忘了", "记得吗"
        ]
        return any(kw in task for kw in keywords)

    def _should_extract_memory(self, task: str) -> bool:
        """检测是否需要提取记忆"""
        keywords = [
            "记住", "记下", "保存", "别忘了",
            "重要的是", "记住我", "记一下"
        ]
        return any(kw in task for kw in keywords)

    def _publish_task_start(self, session_id: str, execution_id: str, task: str, task_info: Dict[str, Any], task_id: str = None):
        """发布任务开始事件

        Args:
            session_id: 会话ID
            execution_id: 执行ID
            task: 任务文本
            task_info: 任务信息
            task_id: 任务ID
        """
        global_event_publisher.publish(
                'task_start',
                session_id=session_id,
                execution_id=execution_id,
                task_id=task_id,
                task_info=task_info,
                user_input=task,
                task_level=task_info.get("level", "none")
        )
    
    async def execute_task(self, task, session_id, context=None):
        """
        执行任务（支持子代理）
        
        Args:
            task: 任务描述
            session_id: 会话 ID
            context: 上下文信息
        
        Returns:
            执行结果
        """
        # 检测是否需要子代理
        if self.subagent_scheduler and self._should_use_subagent(task, context):
            self.logger.info("检测到需要子代理，使用并行执行")
            return await self._execute_with_subagents(task, session_id, context)
        
        # 原有执行流程（降级为直接执行）
        return await self._execute_direct(task, session_id, context)
    
    async def _execute_with_subagents(self, task: str, session_id: str, context: dict):
        """
        使用子代理执行任务
        
        Args:
            task: 原始任务
            session_id: 会话 ID
            context: 上下文信息
        
        Returns:
            聚合后的结果
        """
        # 分解任务
        subtasks = self._decompose_task(task, context)
        
        self.logger.info(f"任务已分解为 {len(subtasks)} 个子任务")
        
        # 发布任务分解事件
        if self.event_publisher:
            self.event_publisher.publish(
                event_type="task_decomposed",
                session_id=session_id,
                original_task=task,
                subtasks=subtasks,
                subagent_count=len(subtasks)
            )
        
        # 并行执行子任务
        workspace_path = context.get("workspace_path") if context else None
        
        results = await self.subagent_scheduler.parallel_execute(
            tasks=subtasks,
            workspace_path=workspace_path,
            context=context
        )
        
        # 聚合结果
        aggregated_result = self._aggregate_subagent_results(results)
        
        # 发布聚合事件
        if self.event_publisher:
            self.event_publisher.publish(
                event_type="subagents_completed",
                session_id=session_id,
                results=[r.to_dict() if hasattr(r, 'to_dict') else r for r in results],
                aggregated_result=aggregated_result
            )
        
        return aggregated_result
    
    async def _execute_direct(self, task: str, session_id: str, context: dict = None):
        """
        直接执行任务（不使用子代理）
        
        Args:
            task: 任务描述
            session_id: 会话 ID
            context: 上下文信息
        
        Returns:
            执行结果
        """
        # 1. 检测是否需要搜索记忆
        if self.memory_search and self._should_search_memory(task):
            self.logger.info("检测到记忆搜索意图")
            memories = self.memory_search.search(task, top_k=3)
            if memories:
                context = context or {}
                context["retrieved_memories"] = [m.to_dict() if hasattr(m, 'to_dict') else m.__dict__ for m in memories]
                self.logger.info(f"检索到 {len(memories)} 条记忆")
        
        # 2. 创建 TaskContext 对象
        task_info = context.get("task_info", {"level": "simple"}) if context else {"level": "simple"}
        session_history = context.get("session_history", []) if context else []
        stream = context.get("stream", False) if context else False
        workspace_path = context.get("workspace_path") if context else None
        
        task_context = TaskContext(
            user_input=task,
            task_info=task_info,
            session_id=session_id,
            session_history=session_history,
            stream=stream,
            workspace_path=workspace_path
        )
        
        # 3. 执行任务
        result = ""
        for chunk in self._execute_task_stream(task_context):
            if chunk.get("type") == "task_finish":
                result = chunk.get("result", "")
                break
        
        # 4. 检测是否需要手动保存记忆
        if self._should_extract_memory(task) and self.session_manager:
            self.logger.info("检测到记忆保存意图")
            # 从任务描述中提取
            session = self.session_manager.get_session(session_id) if hasattr(self.session_manager, 'get_session') else None
            if session and hasattr(session, 'history') and session.history:
                # 添加当前任务到历史
                session.history.append({"role": "user", "content": task})
                
                # 提取记忆
                memories = self.session_manager.memory_extractor.extract_from_session(
                    session.history[-5:],  # 最近 5 条
                    auto_save=True
                )
                self.logger.info(f"手动保存了 {len(memories)} 条记忆")
        
        return result

