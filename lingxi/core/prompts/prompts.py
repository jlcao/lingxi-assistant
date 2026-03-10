"""提示词模板管理模块

该模块集中管理所有LLM提示词模板，提供统一的模板渲染接口。
支持参数化模板、复用和扩展。
支持上下文缓存（Context Cache）功能。
"""

import platform
import os
from typing import Dict, List, Any, Optional


class PromptTemplates:
    """提示词模板类，集中管理所有提示词模板（单例模式）"""
    
    _instance = None  # 单例实例
    
    def __new__(cls):
        """单例模式：确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @staticmethod
    def get_system_info(workspace_path: Optional[str] = None) -> Dict[str, str]:
        """获取系统环境信息

        Args:
            workspace_path: 工作目录路径（可选，如果不提供则使用 os.getcwd()）

        Returns:
            系统信息字典
        """
        from datetime import datetime
        system_info = platform.system()
        current_dir = workspace_path if workspace_path else os.getcwd()
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H:%M:%S")
        return {
            "system_info": system_info,
            "os_info": f"{system_info} {platform.release()}",
            "current_dir": current_dir,
            "shell_type": "PowerShell" if system_info == "Windows" else "Bash",
            "current_date": current_date,
            "current_time": current_time
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
            context += f"用户:{msg.get("user_input", "")}\n助手:{msg.get("result", "")}\n"
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
        system_info: Optional[Dict[str, str]] = None,
        task_plan: str = None
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

        system_prompt = f"""你是万能的灵犀智能助手，使用ReAct模式解决问题。

系统环境: {system_info['os_info']}
当前工作目录: {system_info['current_dir']}
Shell类型: {system_info['shell_type']}
当前日期: {system_info['current_date']}
当前时间: {system_info['current_time']}

任务类型: {task_info.get('level', task_info.get('task_type', '未知'))}
任务描述: {task_info.get('reason', task_info.get('description', '无'))}
{task_plan if task_plan else ""}

可用行动:
{skills_list}
finish(answer) - 完成任务并返回答案

【重要】必须严格按照以下 JSON 格式输出，不要包含任何其他文字：
{{"thought": "你的思考过程", "description": "当前步骤的摘要", "action": "行动名称", "action_input": {{"参数名": "参数值"}}}}

正确示例：
{{"thought": "用户要求创建 test.txt 文件并写入内容", "description": "创建文件", "action": "create_file", "action_input": {{"file_path": "test.txt", "content": "hello world!!!"}}}}
{{"thought": "用户要求读取 data.txt 文件", "description": "读取文件", "action": "read_file", "action_input": {{"file_path": "data.txt"}}}}
{{"thought": "用户要求分析 Excel 文件", "description": "分析 Excel", "action": "xlsx", "action_input": {{"file_path": "data.xlsx", "operation": "read"}}}}
{{"thought": "任务已完成，返回最终答案", "description": "完成任务", "action": "finish", "action_input": "任务已成功完成"}}

错误示例（不要这样输出）：
Thought: 用户要求创建文件...
Action: create_file
Action Input: {{"file_path": "test.txt"}}

注意事项：
- 当任务已经完成时，必须使用finish行动结束任务
- finish的action_input应该是对用户的最终回答（字符串）
- 不要在任务完成后继续执行其他行动
- 必须返回有效的JSON格式，不要包含任何其他文字或说明
- action_input是参数对象，不是字符串
- 参数值如果是字符串，必须用双引号包裹
- 参数值可以包含换行符等特殊字符
- 在处理长文本文件时（如.txt, .py, .js, .md, .json, .yaml等），使用read_file技能搜索读取文件内容，不要直接加载整个文件内容
- 读取Excel文件（.xlsx, .xlsm）时，必须使用xlsx技能，不要使用read_file
- 【代码生成注意事项】：
  - 使用execute_command执行Python代码时，字符串中如果包含双引号，请使用转义(\")或使用单引号包裹字符串
  - 避免在字符串中使用未转义的特殊字符
  - 确保生成的Python代码语法正确，不会导致JSON解析错误

历史上下文:
{history_context}
用户输入:
{user_input}
"""

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
                    PromptTemplates.build_cached_text_content(steps_part, enable_cache=False)
                ]
            }
        ]

        return messages

    @staticmethod
    def build_task_analysis_messages_with_cache(
        task: str,
        history_context: str,
        skills_list: str,
        system_info: Optional[Dict[str, str]] = None,
        max_plan_steps: int = 8
    ) -> List[Dict[str, Any]]:
        """构建任务分析消息列表（支持上下文缓存）

        统一分析任务并输出处理方案，一次LLM调用完成分类+计划+行动。
        缓存策略：
        - 系统信息、工具列表等静态内容标记为缓存
        - 用户任务、历史上下文等动态内容不标记缓存

        Args:
            task: 用户任务
            history_context: 历史上下文
            skills_list: 可用技能列表
            system_info: 系统信息（可选）
            max_plan_steps: 最大计划步骤数

        Returns:
            消息列表，支持 cache_control 标记
        """
        if system_info is None:
            system_info = PromptTemplates.get_system_info()

        system_prompt = f"""你是灵犀智能助手，需要完成用户任务分类。
  
系统环境: {system_info['os_info']}
当前工作目录: {system_info['current_dir']}
Shell类型: {system_info['shell_type']}
当前日期: {system_info['current_date']}
当前时间: {system_info['current_time']}

可用工具:
{skills_list}

请严格按照以下JSON格式输出，不要包含任何其他文字：
{{
  "thought": "你的思考过程",
  "level": "direct|simple|complex",
  "confidence": 0.0-1.0,
  "reason": "分类理由",
  "direct_answer": "如果是简单问候或可直接回答的问题，在此给出答案",
  "plan": [
    {{"step": 1, "description": "步骤描述"}},
    {{"step": 2, "description": "步骤描述"}}
  ]
}}

分类标准：
- simple: 单一步骤、单工具调用、简单问答（如：查天气、翻译、读取文件、问候）
- complex: 多步骤、多工具调用、需要规划（如：旅行规划、数据分析、多文件处理）

注意事项：
- 如果是simple任务，plan字段可以为空数组
- 如果是complex任务，必须填写plan字段
- 如果是问候类或可直接回答的问题，level设为direct，direct_answer为回答内容
- 如果是complex任务，plan最多{max_plan_steps}个步骤，每个步骤描述要精炼，优先使用已有的技能处理
- 必须返回有效的JSON格式"""

        history_part = f"""历史上下文：
{history_context if history_context else "无"}"""

        user_input_part = f"""用户任务：{task}\n 请输出下一步："""

        messages = [
            {
                "role": "system",
                "content": [PromptTemplates.build_cached_text_content(system_prompt, enable_cache=True)]
            },
            {
                "role": "user",
                "content": [
                    PromptTemplates.build_cached_text_content(history_part, enable_cache=False),
                    PromptTemplates.build_cached_text_content(user_input_part, enable_cache=False)
                ]
            }
        ]

        return messages

    @staticmethod
    def format_task_plan(task_plan: List[str]) -> str:
        """格式化任务计划

        Args:
            task_plan: 原始任务计划字符串

        Returns:
            格式化后的任务计划字符串
        """
        res_str=''
        for index,step in enumerate(task_plan):
            res_str += f"{index+1}. {step.strip().replace("\n", " ")} "
        return f"任务计划: {res_str if len(task_plan) > 1 else ""}" 
