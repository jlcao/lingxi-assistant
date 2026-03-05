import logging
import time
from typing import Dict, List, Optional, Any, Union, Generator
from lingxi.core.engine.base import BaseEngine
from lingxi.core.prompts import PromptTemplates
from lingxi.core.event import global_event_publisher


class ReActCore(BaseEngine):
    """ReAct 引擎核心逻辑"""

    def __init__(self, config: Dict[str, Any], skill_caller=None, session_manager=None, websocket_manager=None):
        """初始化 ReAct 核心

        Args:
            config: 系统配置
            skill_caller: 技能调用器
            session_manager: 会话管理器
            websocket_manager: WebSocket管理器（已弃用）
        """
        super().__init__(config, skill_caller, session_manager, websocket_manager)

        self.max_steps = int(config.get("engine", {}).get("max_steps", 10))
        self.timeout = int(config.get("engine", {}).get("timeout", 60))

        self.logger.debug("初始化ReAct推理引擎核心")

    def _build_static_context(self, task_info: Dict[str, Any]) -> str:
        """构建静态上下文

        Args:
            task_info: 任务信息

        Returns:
            静态上下文字符串
        """
        available_skills = self.skill_caller.list_available_skills(enabled_only=True) if self.skill_caller else []
        skills_list = PromptTemplates.format_skills_list(available_skills)

        system_info = PromptTemplates.get_system_info()

        return '''你是灵犀智能助手，使用ReAct模式解决问题。

系统环境: {os_info}
当前工作目录: {current_dir}
Shell类型: {shell_type}

任务类型: {task_type}
任务描述: {description}

可用行动:
{skills_list}
finish(answer) - 完成任务并返回答案

【重要】必须严格按照以下JSON格式输出，不要包含任何其他文字：
{{"thought": "你的思考过程", "action": "行动名称", "action_input": {{"参数名": "参数值"}}}}

示例：
{{"thought": "用户要求创建test.txt文件并写入内容", "action": "create_file", "action_input": {{"file_path": "test.txt", "content": "hello world!!!"}}}}

{{"thought": "用户要求读取data.txt文件", "action": "read_file", "action_input": {{"file_path": "data.txt"}}}}

{{"thought": "用户要求分析Excel文件", "action": "xlsx", "action_input": {{"file_path": "data.xlsx"}}}}

{{"thought": "任务已完成，返回最终答案", "action": "finish", "action_input": "任务已成功完成"}}

注意事项：
- 当任务已经完成时，必须使用finish行动结束任务
- finish的action_input应该是对用户的最终回答（字符串）
- 不要在任务完成后继续执行其他行动
- 必须返回有效的JSON格式，不要包含任何其他文字或说明
- action_input是参数对象，不是字符串
- 参数值如果是字符串，必须用双引号包裹
- 参数值可以包含换行符等特殊字符
- 在处理长文本本文件时，使用read_file技能搜索读取文件内容，不要直接加载整个文件内容
- 请先详细输出thought字段，然后再输出action字段
'''.format(
            os_info=system_info['os_info'],
            current_dir=system_info['current_dir'],
            shell_type=system_info['shell_type'],
            task_type=task_info.get('level', task_info.get('task_type', '未知')),
            description=task_info.get('reason', task_info.get('description', '无')),
            skills_list=skills_list
        )

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

    def _execute_step(self, step: int, messages: List[Dict[str, Any]], task_level: str,
                      session_id: str, execution_id: str, steps: List[Dict[str, Any]],
                      stream: bool = True) -> Dict[str, Any]:
        """执行单个步骤

        Args:
            step: 步骤索引
            messages: 消息列表
            task_level: 任务级别
            session_id: 会话ID
            execution_id: 执行ID
            steps: 已执行步骤
            stream: 是否流式输出

        Returns:
            包含解析结果和 Token 使用信息的字典
        """
        self._build_step_messages(messages, steps)
        self.logger.debug(f"生成思考和行动（stream={stream}")

        full_response = ""
        usage = None
        for response_chunk in self._process_llm_response(messages, task_level, stream):
            if response_chunk["type"] == "thought_chunk":
                content = response_chunk["content"]
                self._publish_think_stream(session_id, execution_id, step, content)
            elif response_chunk["type"] == "complete":
                full_response = response_chunk["response"]
                usage = response_chunk.get("usage")
                break

        parsed = self._parse_response(full_response)

        if not parsed:
            self.logger.warning("无法解析响应，结束循环")
            self._publish_step_end(session_id, execution_id, step, "failed", None, "无法解析LLM响应",
                                   parsed.get("thought", ""), parsed.get("description", ""))
            self._publish_task_failed(session_id, execution_id, "无法解析LLM响应")
            return {"parsed": parsed, "usage": usage}

        if parsed.get("action") == "finish":
            final_answer = parsed.get("action_input", "")
            self._publish_step_end(session_id, execution_id, step, "completed", None, final_answer,
                                   parsed.get("thought"), parsed.get("description"))
            # 注意：task_end 事件由调用方 _execute_task_stream 统一发布，这里不再重复发布

            self._handle_finish_action(parsed, steps)
            return {"parsed": parsed, "usage": usage}

        chunk = self._handle_step_complete(parsed, step)
        observation = chunk.get("observation", "")
        self._publish_step_end(session_id, execution_id, step, "completed", None, observation, parsed.get("thought"),
                               parsed.get("description"))
        return {"parsed": parsed, "usage": usage}

    def _execute_task_stream(self, user_input: str, task_plan: List[str], task_info: Dict[str, Any], history: List[Dict[str, str]],
                             session_id: str, execution_id: str, stream: bool) -> Generator[Dict[str, Any], None, None]:
        """执行任务（流式）

        Args:
            user_input: 用户输入
            task_plan: 任务计划列表
            task_info: 任务信息
            history: 会话历史
            session_id: 会话ID
            execution_id: 执行ID
            stream: 是否启用流式输出

        Yields:
            流式响应块
        """
        self.logger.debug(f"ReAct处理任务: {task_info.get('task_type')} (stream={stream})")
        self.logger.debug(f"用户输入: {user_input}")

        task_level = task_info.get("level", "simple")

        history_context = self._build_history_context(history)

        messages = self._build_initial_messages(user_input, task_plan, task_info, history_context)
        steps = []
        
        # Token 统计
        total_input_tokens = 0
        total_output_tokens = 0

        for step in range(self.max_steps):
            self.logger.debug(f"步骤 {step + 1}/{self.max_steps}")
            self._publish_step_start(session_id, execution_id, step, self.max_steps)
            step_result = self._execute_step(step, messages, task_level, session_id, execution_id, steps, stream=stream)
            
            # 收集 Token 使用信息
            if step_result and "usage" in step_result:
                usage = step_result["usage"]
                if usage:
                    input_tokens = getattr(usage, "prompt_tokens", 0)
                    output_tokens = getattr(usage, "completion_tokens", 0)
                    total_input_tokens += input_tokens
                    total_output_tokens += output_tokens
                    self.logger.debug(f"步骤 {step + 1} Token 使用: input={input_tokens}, output={output_tokens}")
            
            # 提取 parsed 结果
            res = step_result.get("parsed") if step_result else None
            steps.append(res)

            # 如果已经执行了finish动作，结束循环
            if res and res.get("action") == "finish":
                self.logger.debug("检测到finish动作，结束任务执行")
                self._publish_task_end(session_id, execution_id, res.get("action_input", ""))
                
                # 更新 Token 统计
                task_id = task_info.get("task_id")
                if task_id:
                    self.session_manager.update_task_tokens(task_id, total_input_tokens, total_output_tokens)
                    self.session_manager.update_session_tokens(session_id, total_input_tokens, total_output_tokens)
                    self.logger.debug(f"任务 Token 总计: input={total_input_tokens}, output={total_output_tokens}")
                
                yield {"type": "task_end", "result": res.get("action_input", "")}
                return    
      

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
        return self._execute_new_task(user_input, task_info, session_history, session_id, stream)
