"""提示词模板管理模块

该模块集中管理所有LLM提示词模板，提供统一的模板渲染接口。
支持参数化模板、复用和扩展。
支持上下文缓存（Context Cache）功能。
"""

import platform
import os
from re import I
from typing import Dict, List, Any, Optional, Union


class PromptTemplates:
    """提示词模板类，集中管理所有提示词模板"""

    @staticmethod
    def get_system_info() -> Dict[str, str]:
        """获取系统环境信息

        Returns:
            系统信息字典
        """
        system_info = platform.system()
        return {
            "system_info": system_info,
            "os_info": f"{system_info} {platform.release()}",
            "current_dir": os.getcwd(),
            "shell_type": "PowerShell" if system_info == "Windows" else "Bash"
        }

    @staticmethod
    def format_skills_list(skills: List[Dict[str, str]]) -> str:
        """格式化技能列表

        Args:
            skills: 技能列表，每个技能包含name和description

        Returns:
            格式化后的技能列表字符串
        """
        if not skills:
            return "无可用技能"

        skills_list = ""
        for i, skill in enumerate(skills, 1):
            skill_name = skill.get('name', '')
            skill_desc = skill.get('description', '')
            skills_list += f"{i}. {skill_name} - {skill_desc}\n"
        return skills_list

    @staticmethod
    def format_history_context(session_history: List[Dict[str, str]], max_count: int = 5) -> str:
        """格式化历史上下文

        Args:
            session_history: 会话历史
            max_count: 最大历史消息数量

        Returns:
            格式化后的历史上下文字符串
        """
        if not session_history:
            return "无历史对话"

        context = ""
        for msg in session_history[-max_count:]:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role and content:
                role_name = "用户" if role == "user" else "助手"
                context += f"{role_name}: {content}\n"
        return context

    @staticmethod
    def format_executed_steps(steps: List[Dict[str, str]], include_thought: bool = True, max_prev_length: int = 50) -> str:
        """格式化已执行步骤

        Args:
            steps: 执行步骤列表
            include_thought: 是否包含思考过程
            max_prev_length: 之前步骤内容最大长度（字符数）

        Returns:
            格式化后的步骤字符串
        """
        if not steps:
            return "无已执行步骤"

        formatted = ""
        total_steps = len(steps)
        
        for i, step in enumerate(steps):
            formatted += f"步骤 {i + 1}:\n"
            
            # 判断是否为最后一步
            is_last_step = (i == total_steps - 1)
            
            if include_thought and step.get('thought'):
                thought = step.get('thought', '')
                if not is_last_step:
                    thought = thought[:max_prev_length] + ('...' if len(thought) > max_prev_length else '')
                else:
                    thought = thought.replace('\n', '\\n')
                formatted += f"思考: {thought}\n"
            
            # 处理 action_input，可能是字符串或字典
            action_input = step.get('action_input', '')
            if isinstance(action_input, dict):
                if is_last_step:
                    # 最后一步完整显示
                    params_str = ', '.join([f"{k}={v}" for k, v in action_input.items()])
                    formatted += f"行动: {step.get('action', '')} - {params_str.replace('\n', '\\n')}\n"
                else:
                    # 之前步骤截断显示
                    params_str = ', '.join([f"{k}={v}" for k, v in action_input.items()])
                    if len(params_str) > max_prev_length:
                        params_str = params_str[:max_prev_length] + '...'
                    formatted += f"行动: {step.get('action', '')} - {params_str.replace('\n', '\\n')}\n"
            else:
                if is_last_step:
                    # 最后一步完整显示
                    action_input_str = str(action_input).replace('\n', '\\n')
                    formatted += f"行动: {step.get('action', '')} - {action_input_str}\n"
                else:
                    # 之前步骤截断显示
                    action_input_str = str(action_input).replace('\n', '\\n')
                    if len(action_input_str) > max_prev_length:
                        action_input_str = action_input_str[:max_prev_length] + '...'
                    formatted += f"行动: {step.get('action', '')} - {action_input_str}\n"
            
            if step.get('observation'):
                observation = step.get('observation', '')
                if not is_last_step:
                    observation = observation[:max_prev_length] + ('...' if len(observation) > max_prev_length else '')
                else:
                    observation = observation
                formatted += f"观察: {observation.replace('\n', '\\n')}\n"
            formatted += "\n"
        return formatted

    @staticmethod
    def format_plan_results(results: List[Dict[str, Any]]) -> str:
        """格式化规划执行结果

        Args:
            results: 执行结果列表

        Returns:
            格式化后的结果字符串
        """
        if not results:
            return "无执行结果"

        formatted = ""
        for i, result in enumerate(results):
            formatted += f"步骤 {i + 1}:\n"
            
            # 处理 action_input，可能是字符串或字典
            action_input = result.get('action_input', '')
            if isinstance(action_input, dict):
                # 如果是字典，格式化为 key=value 形式
                params_str = ', '.join([f"{k}={v}" for k, v in action_input.items()])
                formatted += f"行动: {result.get('action', '')} - {params_str.replace('\n', '\\n')}\n"
            else:
                # 如果是字符串，替换换行符
                action_input_str = str(action_input).replace('\n', '\\n')
                formatted += f"行动: {result.get('action', '')} - {action_input_str}\n"
            
            if result.get('observation'):
                observation = result.get('observation', '').replace('\n', '\\n')
                formatted += f"观察: {observation.replace('\n', '\\n')}\n"
            formatted += "\n"
        return formatted

    @staticmethod
    def build_react_prompt(
        user_input: str,
        task_info: Dict[str, Any],
        history_context: str,
        skills_list: str,
        steps: List[Dict[str, str]],
        system_info: Optional[Dict[str, str]] = None
    ) -> str:
        """构建ReAct模式提示词

        Args:
            user_input: 用户输入
            task_info: 任务信息
            history_context: 历史上下文
            skills_list: 可用技能列表
            steps: 已执行步骤
            system_info: 系统信息（可选）

        Returns:
            ReAct提示词
        """
        if system_info is None:
            system_info = PromptTemplates.get_system_info()

        executed_steps = PromptTemplates.format_executed_steps(steps, include_thought=False, max_prev_length=5000)

        prompt = f"""
        你是灵犀智能助手，使用ReAct模式解决问题。

        系统环境: {system_info['os_info']}
        当前工作目录: {system_info['current_dir']}
        Shell类型: {system_info['shell_type']}

        任务类型: {task_info.get('task_type', '未知')}
        任务描述: {task_info.get('description', '无')}

        历史上下文:
        {history_context}

        用户输入:
        {user_input}

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

        已执行步骤:
        {executed_steps}
        现在请输出下一步:
        """
        return prompt

    @staticmethod
    def build_plan_react_prompt(
        task: str,
        task_info: Dict[str, Any],
        history_context: str,
        current_step: str,
        skills_list: str,
        previous_results: List[Dict[str, Any]],
        system_info: Optional[Dict[str, str]] = None
    ) -> str:
        """构建Plan-ReAct模式步骤提示词

        Args:
            task: 任务文本
            task_info: 任务信息
            history_context: 历史上下文
            current_step: 当前步骤描述
            skills_list: 可用技能列表
            previous_results: 之前步骤的结果
            system_info: 系统信息（可选）

        Returns:
            Plan-ReAct步骤提示词
        """
        if system_info is None:
            system_info = PromptTemplates.get_system_info()

        results_str = PromptTemplates.format_executed_steps(previous_results, include_thought=True, max_prev_length=5000)

        prompt = f'''你是灵犀智能助手，使用Plan-ReAct模式解决问题。

系统环境: {system_info['os_info']}
当前工作目录: {system_info['current_dir']}
Shell类型: {system_info['shell_type']}

任务类型: {task_info.get('level', '未知')}
任务描述: {task_info.get('reason', '无')}

历史上下文:
{history_context}

用户输入:
{task}

当前执行步骤:
{current_step}

工具列表:
{skills_list}
finish(answer) - 完成任务并返回答案

【重要】必须严格按照以下JSON格式输出，不要包含任何其他文字：
{{"thought": "你的思考过程", "action": "行动名称", "action_input": {{"参数名": "参数值"}}}}

注意事项：
- 当任务已经完成时，必须使用finish行动结束任务
- finish的action_input应该是对用户的最终回答（字符串）
- 不要在任务完成后继续执行其他行动
- 必须返回有效的JSON格式，不要包含任何其他文字或说明
- action_input是参数对象，不是字符串
- 参数值如果是字符串，必须用双引号包裹
- 参数值可以包含换行符等特殊字符
- 在处理长文本本文件时，使用read_file技能搜索读取文件内容，不要直接加载整个文件内容

之前步骤的结果:
{results_str}
现在请输出下一步:
'''
        return prompt

    @staticmethod
    def build_task_planning_prompt(
        task: str,
        task_info: Dict[str, Any],
        history_context: str
    ) -> str:
        """构建任务规划提示词

        Args:
            task: 任务文本
            task_info: 任务信息
            history_context: 历史上下文

        Returns:
            任务规划提示词
        """
        prompt = f"""请为用户输入生成详细的任务规划，包括具体的步骤。

任务类型: {task_info.get('level', '未知')}
任务描述: {task_info.get('reason', '无')}

历史上下文:
{history_context}

用户输入:
{task}

【重要】必须严格按照以下格式输出，不要包含任何其他内容：
1. 第一步的具体描述
2. 第二步的具体描述
3. 第三步的具体描述
...

要求：
- 每个步骤一行，以数字开头
- 步骤描述要具体、可执行
- 不要使用Markdown格式
- 不要添加任何解释、标题、分隔线或其他格式
"""
        return prompt

    @staticmethod
    def build_final_response_prompt(
        user_input: str,
        steps: List[Dict[str, str]],
        include_thought: bool = False
    ) -> str:
        """构建最终响应提示词

        Args:
            user_input: 用户输入
            steps: 执行步骤
            include_thought: 是否包含思考过程

        Returns:
            最终响应提示词
        """
        if include_thought:
            steps_str = PromptTemplates.format_executed_steps(steps, include_thought=True, max_prev_length=5000)
        else:
            steps_str = PromptTemplates.format_executed_steps(steps,include_thought=False,max_prev_length=5000)

        prompt = f"""
        请根据以下执行步骤，为用户输入生成最终响应:

        用户输入:
        {user_input}

        执行步骤:
        {steps_str}
        请生成简洁、友好的最终响应:
        """
        return prompt

    @staticmethod
    def build_cached_text_content(text: str, enable_cache: bool = True) -> Dict[str, Any]:
        """构建带缓存标记的文本内容

        Args:
            text: 文本内容
            enable_cache: 是否启用缓存

        Returns:
            结构化内容字典
        """
        if enable_cache:
            return {
                "type": "text",
                "text": text,
                "cache_control": {"type": "ephemeral"}
            }
        else:
            return {
                "type": "text",
                "text": text
            }

    @staticmethod
    def build_react_messages_with_cache(
        user_input: str,
        task_info: Dict[str, Any],
        history_context: str,
        skills_list: str,
        steps: List[Dict[str, str]],
        system_info: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """构建ReAct模式消息列表（支持上下文缓存）

        将静态上下文标记为可缓存，动态内容不标记缓存。
        缓存策略：
        - 系统信息、任务信息、技能列表等静态内容标记为缓存
        - 已执行步骤的动态内容不标记缓存

        Args:
            user_input: 用户输入
            task_info: 任务信息
            history_context: 历史上下文
            skills_list: 可用技能列表
            steps: 已执行步骤
            system_info: 系统信息（可选）

        Returns:
            消息列表，支持 cache_control 标记
        """
        if system_info is None:
            system_info = PromptTemplates.get_system_info()

        executed_steps = PromptTemplates.format_executed_steps(steps, include_thought=False, max_prev_length=5000)

        system_prompt = f"""你是灵犀智能助手，使用ReAct模式解决问题。

系统环境: {system_info['os_info']}
当前工作目录: {system_info['current_dir']}
Shell类型: {system_info['shell_type']}

任务类型: {task_info.get('task_type', '未知')}
任务描述: {task_info.get('description', '无')}

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
"""

        history_part = f"""历史上下文:
{history_context}"""

        user_input_part = f"""用户输入:
{user_input}"""

        steps_part = f"""已执行步骤:
{executed_steps}
现在请输出下一步:"""

        messages = [
            {
                "role": "system",
                "content": [PromptTemplates.build_cached_text_content(system_prompt, enable_cache=True)]
            },
            {
                "role": "user",
                "content": [
                    PromptTemplates.build_cached_text_content(history_part, enable_cache=True),
                    PromptTemplates.build_cached_text_content(user_input_part, enable_cache=True),
                    PromptTemplates.build_cached_text_content(steps_part, enable_cache=False)
                ]
            }
        ]

        return messages

    @staticmethod
    def build_plan_react_messages_with_cache(
        task: str,
        task_info: Dict[str, Any],
        history_context: str,
        current_step: str,
        skills_list: str,
        previous_results: List[Dict[str, Any]],
        system_info: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """构建Plan-ReAct模式步骤消息列表（支持上下文缓存）

        将静态上下文标记为可缓存，动态内容不标记缓存。
        缓存策略：
        - 系统信息、任务信息、技能列表等静态内容标记为缓存
        - 当前步骤、之前步骤结果等动态内容不标记缓存

        Args:
            task: 任务文本
            task_info: 任务信息
            history_context: 历史上下文
            current_step: 当前步骤描述
            skills_list: 可用技能列表
            previous_results: 之前步骤的结果
            system_info: 系统信息（可选）

        Returns:
            消息列表，支持 cache_control 标记
        """
        if system_info is None:
            system_info = PromptTemplates.get_system_info()

        results_str = PromptTemplates.format_executed_steps(previous_results, include_thought=True, max_prev_length=5000)

        system_prompt = f"""你是灵犀智能助手，使用Plan-ReAct模式解决问题。

系统环境: {system_info['os_info']}
当前工作目录: {system_info['current_dir']}
Shell类型: {system_info['shell_type']}

任务类型: {task_info.get('level', '未知')}
任务描述: {task_info.get('reason', '无')}

工具列表:
{skills_list}
finish(answer) - 完成任务并返回答案

【重要】必须严格按照以下JSON格式输出，不要包含任何其他文字：
{{"thought": "你的思考过程", "action": "行动名称", "action_input": {{"参数名": "参数值"}}}}

注意事项：
- 当任务已经完成时，必须使用finish行动结束任务
- finish的action_input应该是对用户的最终回答（字符串）
- 不要在任务完成后继续执行其他行动
- 必须返回有效的JSON格式，不要包含任何其他文字或说明
- action_input是参数对象，不是字符串
- 参数值如果是字符串，必须用双引号包裹
- 参数值可以包含换行符等特殊字符
- 在处理长文本本文件时，使用read_file技能搜索读取文件内容，不要直接加载整个文件内容
"""

        history_part = f"""历史上下文:
{history_context}"""

        user_input_part = f"""用户输入:
{task}"""

        current_step_part = f"""当前执行步骤:
{current_step}"""

        # 将之前步骤的结果拆分为多个部分，为工具使用说明添加缓存
        results_content = []
        results_content.append(PromptTemplates.build_cached_text_content("之前步骤的结果:", enable_cache=False))
        
        for i, step in enumerate(previous_results):
            step_header = f"步骤 {i + 1}:"
            results_content.append(PromptTemplates.build_cached_text_content(step_header, enable_cache=False))
            
            if step.get('thought'):
                thought = f"思考: {step.get('thought', '').replace('\n', '\\n')}"
                results_content.append(PromptTemplates.build_cached_text_content(thought, enable_cache=False))
            
            if step.get('action'):
                action_input = step.get('action_input', '')
                if isinstance(action_input, dict):
                    params_str = ', '.join([f"{k}={v}" for k, v in action_input.items()])
                    action = f"行动: {step.get('action', '')} - {params_str.replace('\n', '\\n')}"
                else:
                    action = f"行动: {step.get('action', '')} - {str(action_input).replace('\n', '\\n')}"
                results_content.append(PromptTemplates.build_cached_text_content(action, enable_cache=False))
            
            if step.get('observation'):
                observation = step.get('observation', '')
                is_tool_guide = 'Skill Usage Guide' in observation or '技能使用说明' in observation or 'XLSX技能使用说明' in observation
                if is_tool_guide:
                    results_content.append(PromptTemplates.build_cached_text_content(f"观察: {observation.replace('\n', '\\n')}", enable_cache=True))
                else:
                    results_content.append(PromptTemplates.build_cached_text_content(f"观察: {observation.replace('\n', '\\n')}", enable_cache=False))
            
            results_content.append(PromptTemplates.build_cached_text_content("", enable_cache=False))
        
        results_content.append(PromptTemplates.build_cached_text_content("现在请输出下一步:", enable_cache=False))

        messages = [
            {
                "role": "system",
                "content": [PromptTemplates.build_cached_text_content(system_prompt, enable_cache=True)]
            },
            {
                "role": "user",
                "content": [
                    PromptTemplates.build_cached_text_content(history_part, enable_cache=True),
                    PromptTemplates.build_cached_text_content(user_input_part, enable_cache=True),
                    PromptTemplates.build_cached_text_content(current_step_part, enable_cache=False)
                ]
            }
        ]
        
        # 将之前步骤的结果添加到用户消息中
        messages[1]["content"].extend(results_content)

        return messages

    @staticmethod
    def build_task_planning_messages_with_cache(
        task: str,
        task_info: Dict[str, Any],
        history_context: str,
        system_info: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """构建任务规划消息列表（支持上下文缓存）

        Args:
            task: 任务文本
            task_info: 任务信息
            history_context: 历史上下文
            system_info: 系统信息（可选）

        Returns:
            消息列表，支持 cache_control 标记
        """
        if system_info is None:
            system_info = PromptTemplates.get_system_info()

        system_prompt = f"""请为用户输入生成详细的任务规划，包括具体的步骤。

要求：
- 每个步骤一行，以数字开头
- 步骤描述要具体、可执行
- 不要使用Markdown格式
- 不要添加任何解释、标题、分隔线或其他格式
"""

        history_part = f"""任务类型: {task_info.get('level', '未知')}
任务描述: {task_info.get('reason', '无')}

历史上下文:
{history_context}"""

        user_input_part = f"""用户输入:
{task}

【重要】必须严格按照以下格式输出，不要包含任何其他内容：
1. 第一步的具体描述
2. 第二步的具体描述
3. 第三步的具体描述
..."""

        messages = [
            {
                "role": "system",
                "content": [PromptTemplates.build_cached_text_content(system_prompt, enable_cache=True)]
            },
            {
                "role": "user",
                "content": [
                    PromptTemplates.build_cached_text_content(history_part, enable_cache=True),
                    PromptTemplates.build_cached_text_content(user_input_part, enable_cache=True)
                ]
            }
        ]

        return messages
