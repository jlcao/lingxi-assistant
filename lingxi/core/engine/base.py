import logging
import time
import json
import uuid
import threading
import asyncio
from typing import Dict, List, Optional, Any, Union, Generator, TYPE_CHECKING
from lingxi.core.skill_caller import SkillCaller
from lingxi.core.prompts.prompts import PromptTemplates
from lingxi.core.event import global_event_publisher
from lingxi.core.context.task_context import TaskContext
from lingxi.core.utils.security import SecurityError
from lingxi.core.confirmation.confirmation import ConfirmationManager, DangerousSkillChecker, RiskLevel
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
        # LLMClient 已废弃 - 子类应使用 AsyncLLMClient
        # self.llm_client = LLMClient(config)
        self.logger = logging.getLogger(__name__)
        
        # 初始化确认管理器（V4.0新增）
        security_config = config.get("security", {})
        self.confirmation_manager = ConfirmationManager(
            timeout=security_config.get("confirmation_timeout", 60),
            auto_reject_timeout=security_config.get("auto_reject_timeout", True)
        )

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

    def _execute_action(self, action: str, action_type: str, action_input: Any) -> str:
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
            return {"success": False, "error": "技能调用器未初始化", "result_description": f"{action} 执行失败，技能调用器未初始化"}

        try:
            # 如果 action_input 是字符串，尝试解析为参数字典
            if isinstance(action_input, str):
                parameters = self._parse_action_parameters(action_input)
                parameters = self._process_parameters(parameters)
            else:
                # action_input 已经是字典（对象）
                parameters = action_input if isinstance(action_input, dict) else {}
            
            # 处理高危操作确认
            confirmation_result = self._handle_dangerous_operation_with_confirmation(
                action,
                parameters
            )
            
            # 如果需要确认且用户拒绝，直接返回
            if confirmation_result:
                return {"success": False, "error": "用户拒绝执行高危操作", "result_description": f"{action} 执行失败，用户拒绝执行高危操作"}
            
            # 使用带安全检查的技能调用
            result = self.skill_caller.call_with_security_check(
                action,
                action_type,
                parameters,
                require_confirmation=False
            )

            return result
        except SecurityError as e:
            self.logger.error(f"安全检查失败: {e}")
            return {"success": False, "error": str(e), "result_description": f"{action} 安全检查失败"}
        except Exception as e:
            self.logger.error(f"执行行动失败: {e}")
            return {"success": False, "error": str(e), "result_description": f"{action} 执行失败"}

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





    def _handle_dangerous_operation_with_confirmation(self, action: str, parameters: Dict[str, Any]) -> Optional[str]:
        """处理高危操作，需要用户确认
        
        Args:
            action: 行动名称
            parameters: 行动参数
            
        Returns:
            如果需要确认且用户拒绝，返回拒绝信息；否则返回 None
        """
        # 检查操作风险级别
        skill_risk = DangerousSkillChecker.check_skill_risk(action)
        command_risk = RiskLevel.LOW
        
        # 检查命令风险（如果是 execute 操作）
        if action == "execute" and isinstance(parameters.get("command"), str):
            command_risk = DangerousSkillChecker.check_command_risk(parameters["command"])
        
        # 判断是否需要确认
        needs_confirmation = (
            skill_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL] or
            command_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        )
        
        if not needs_confirmation:
            # 低风险操作，直接返回 None（继续执行）
            self.logger.debug(f"低风险操作，无需确认：{action}")
            return None
        
        # 高风险操作，需要用户确认
        self.logger.info(f"检测到高危操作：{action}, 风险级别：{skill_risk.value if skill_risk != RiskLevel.LOW else command_risk.value}")
        
        # 创建确认请求
        request = self.confirmation_manager.create_request(
            operation=action,
            description=f"参数：{parameters}",
            risk_level=skill_risk if skill_risk != RiskLevel.LOW else command_risk,
            metadata={"parameters": parameters}
        )
        
        # 发送确认请求事件
        global_event_publisher.publish(
            "require_confirmation",
            request_id=request.request_id,
            operation=action,
            description=f"参数：{parameters}",
            risk_level=request.risk_level.value,
            timeout=request.timeout
        )
        
        # 等待用户确认
        try:
            confirmed = asyncio.run(self.confirmation_manager.wait_for_confirmation(request.request_id))
            
            if not confirmed:
                self.logger.warning(f"用户拒绝高危操作：{action}")
                return f"{action} 操作已被用户拒绝"
            
            self.logger.info(f"用户确认高危操作：{action}")
            return None  # 确认后返回 None，继续执行
        except Exception as e:
            self.logger.error(f"等待确认失败：{e}")
            return f"{action} 确认失败：{str(e)}"

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

    def _publish_step_end(self, session_id: str, execution_id: str, step_idx: int, status: str, error: str = None, result: str = "", thought: str = "",description:str="", task_id: str = None,result_description:str=""):
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
            description=description,
            result_description=result_description
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

    def _publish_plan_start(self, session_id: str, execution_id: str, task_id: str = None, task_level: str = "none", summary: str = None):
        """发布计划开始事件

        Args:
            session_id: 会话 ID
            execution_id: 执行 ID
            task_id: 任务 ID
            task_level: 任务级别
            summary: 任务摘要
        """
        global_event_publisher.publish(
            'plan_start',
            session_id=session_id,
            execution_id=execution_id,
            task_id=task_id,
            task_level=task_level,
            summary=summary
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
        import warnings
        warnings.warn("_process_llm_response 已废弃 - 子类应实现自己的版本", DeprecationWarning)
        
        # 添加调试日志
        self.logger.debug(f"处理LLM响应，消息数量: {len(messages)}")
        for i, msg in enumerate(messages):
            self.logger.debug(f"消息 {i}: role={msg['role']}, content={repr(str(msg['content'])[:200])}")
        
        # LLMClient 已废弃
        yield {
            "type": "complete",
            "response": "{\"thought\": \"处理中\", \"action\": \"finish\", \"action_input\": \"任务处理完成\"}"
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
        result = self._execute_action(parsed.get("action"),parsed.get("action_type"), parsed.get("action_input"))
        if result.get("success", False):
            parsed["observation"] = result.get("result", "")
        else:
            parsed["observation"] = result.get("error", "")

        self.logger.debug(f"思考: {parsed.get('thought')}")
        self.logger.debug(f"行动: {parsed.get('action')} - {parsed.get('action_input')}")
        observation_value = result.get("result", "")
        if isinstance(observation_value, str):
            self.logger.debug(f"观察: {observation_value.replace(chr(10), chr(92) + 'n')}")
        else:
            self.logger.debug(f"观察: {observation_value}")

        return {
            "type": "step_complete",
            "step": step,
            "thought": parsed.get('thought'),
            "action": parsed.get('action'),
            "action_input": parsed.get('action_input'),
            "observation": result.get("result", ""),
            "result_description": result.get("result_description", ""),
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