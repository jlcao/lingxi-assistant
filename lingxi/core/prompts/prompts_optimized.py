"""优化后的提示词模板管理模块

该模块集中管理所有LLM提示词模板，提供统一的模板渲染接口。
支持参数化模板、复用和扩展。

优化策略：
1. 压缩历史记录：只保留最近1-2个步骤的摘要
2. 智能技能列表：根据任务类型只展示相关技能
3. 系统信息优化：只在首次请求时包含完整信息
4. 示例和说明优化：移至系统提示词，避免重复
5. 去重：消除历史上下文和用户输入的重复
6. 观察结果压缩：保留关键信息，移除冗余输出
"""

import platform
import os
from typing import Dict, List, Any, Optional


class PromptTemplates:
    """优化后的提示词模板类，集中管理所有提示词模板"""

    # 系统提示词（只发送一次）
    SYSTEM_PROMPT = """你是灵犀智能助手，使用ReAct模式解决问题。

可用行动:
1. create_file - Create a new file with specified content
2. delete_file - Delete a file
3. execute_command - Execute Linux Shell or PowerShell commands
4. fetch_webpage - Fetch webpage content and save to file
5. modify_file - Modify file content by replacing old with new
6. read_file - Read text-based file content
7. search - Search for information on internet
8. docx - Work with .docx documents
9. pdf - Work with PDF documents
10. xlsx - Work with spreadsheets

输出格式:
思考: 你的思考过程
行动: 行动名称(参数)

重要提示:
- 当任务已经完成时，必须使用finish(answer)结束任务
- 不要在任务完成后继续执行其他行动
- finish(answer)中的answer应该是对用户的最终回答
"""

    @staticmethod
    def get_system_info() -> Dict[str, str]:
        """获取系统环境信息

        Returns:
            系统信息字典
        """
        from datetime import datetime
        system_info = platform.system()
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H:%M:%S")
        return {
            "system_info": system_info,
            "os_info": f"{system_info} {platform.release()}",
            "current_dir": os.getcwd(),
            "shell_type": "PowerShell" if system_info == "Windows" else "Bash",
            "current_date": current_date,
            "current_time": current_time
        }

    @staticmethod
    def format_skills_list(skills: List[Dict[str, str]], task_type: str = None) -> str:
        """格式化技能列表（优化版：根据任务类型只展示相关技能）

        Args:
            skills: 技能列表，每个技能包含name和description
            task_type: 任务类型，用于筛选相关技能

        Returns:
            格式化后的技能列表字符串
        """
        if not skills:
            return "无可用技能"

        # 根据任务类型筛选相关技能
        if task_type:
            relevant_skills = PromptTemplates._filter_relevant_skills(skills, task_type)
        else:
            relevant_skills = skills

        skills_list = ""
        for i, skill in enumerate(relevant_skills, 1):
            skill_name = skill.get('name', '')
            skill_desc = skill.get('description', '')
            # 只显示技能名称和简短描述（限制在50字符内）
            short_desc = skill_desc[:50] + "..." if len(skill_desc) > 50 else skill_desc
            skills_list += f"{i}. {skill_name} - {short_desc}\n"
        return skills_list

    @staticmethod
    def _filter_relevant_skills(skills: List[Dict[str, str]], task_type: str) -> List[Dict[str, str]]:
        """根据任务类型筛选相关技能

        Args:
            skills: 所有技能列表
            task_type: 任务类型

        Returns:
            相关技能列表
        """
        # 定义任务类型到技能的映射
        task_skill_map = {
            "file": ["create_file", "delete_file", "modify_file", "read_file"],
            "command": ["execute_command"],
            "web": ["fetch_webpage", "search"],
            "document": ["docx", "pdf", "xlsx"],
            "excel": ["xlsx"],
            "word": ["docx"],
            "pdf": ["pdf"],
        }

        # 根据任务关键词判断类型
        task_lower = task_type.lower() if task_type else ""
        relevant_skill_names = []

        for task_key, skill_names in task_skill_map.items():
            if task_key in task_lower:
                relevant_skill_names.extend(skill_names)

        # 如果没有匹配，返回所有技能
        if not relevant_skill_names:
            return skills

        # 筛选相关技能
        return [skill for skill in skills if skill.get('name') in relevant_skill_names]

    @staticmethod
    def format_history_context(session_history: List[Dict[str, str]], max_count: int = 3) -> str:
        """格式化历史上下文（优化版：减少历史数量）

        Args:
            session_history: 会话历史
            max_count: 最大历史消息数量（默认3条，原5条）

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
                # 压缩内容：只保留前100字符
                short_content = content[:100] + "..." if len(content) > 100 else content
                context += f"{role_name}: {short_content}\n"
        return context

    @staticmethod
    def format_executed_steps(steps: List[Dict[str, str]], include_thought: bool = False, max_steps: int = 2) -> str:
        """格式化已执行步骤（优化版：压缩历史记录）

        Args:
            steps: 执行步骤列表
            include_thought: 是否包含思考过程（默认False，原True）
            max_steps: 最多保留的步骤数（默认2步，原全部）

        Returns:
            格式化后的步骤字符串
        """
        if not steps:
            return "无已执行步骤"

        # 只保留最近的max_steps个步骤
        recent_steps = steps[-max_steps:]

        formatted = ""
        for i, step in enumerate(recent_steps):
            formatted += f"步骤 {len(steps) - len(recent_steps) + i + 1}:\n"
            if include_thought and step.get('thought'):
                # 压缩思考：只保留前50字符
                short_thought = step.get('thought')[:50] + "..." if len(step.get('thought', '')) > 50 else step.get('thought')
                formatted += f"思考: {short_thought}\n"
            formatted += f"行动: {step.get('action', '')} - {step.get('action_input', '')}\n"
            if step.get('observation'):
                # 压缩观察：只保留前100字符
                short_obs = step.get('observation')[:100] + "..." if len(step.get('observation', '')) > 100 else step.get('observation')
                obs_clean = short_obs.replace('\n', '\\n')
                formatted += f"观察：{obs_clean}\n"
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
            formatted += f"行动: {result.get('action', '')} - {result.get('action_input', '')}\n"
            if result.get('observation'):
                formatted += f"观察: {result.get('observation')}\n"
            formatted += "\n"
        return formatted

    @staticmethod
    def build_react_prompt(
        user_input: str,
        task_info: Dict[str, Any],
        history_context: str,
        skills_list: str,
        steps: List[Dict[str, str]],
        system_info: Optional[Dict[str, str]] = None,
        is_first_step: bool = True
    ) -> str:
        """构建ReAct模式提示词（优化版）

        Args:
            user_input: 用户输入
            task_info: 任务信息
            history_context: 历史上下文
            skills_list: 可用技能列表
            steps: 已执行步骤
            system_info: 系统信息（可选）
            is_first_step: 是否是第一步（默认True）

        Returns:
            ReAct提示词
        """
        if system_info is None:
            system_info = PromptTemplates.get_system_info()

        # 只在第一步包含完整系统信息
        if is_first_step:
            system_section = f"""系统环境: {system_info['os_info']}
当前工作目录: {system_info['current_dir']}
Shell类型: {system_info['shell_type']}
当前日期: {system_info['current_date']}
当前时间: {system_info['current_time']}

任务类型: {task_info.get('task_type', '未知')}
任务描述: {task_info.get('description', '无')}
"""
        else:
            system_section = ""

        # 去重：如果历史上下文已经包含用户输入，就不重复
        if user_input in history_context:
            user_section = ""
        else:
            user_section = f"""用户输入:
{user_input}
"""

        # 只在第一步包含完整技能列表
        if is_first_step:
            skills_section = f"""可用行动:
{skills_list}
"""
        else:
            skills_section = ""

        # 压缩已执行步骤
        executed_steps = PromptTemplates.format_executed_steps(steps, include_thought=False, max_steps=2)

        prompt = f"""{system_section}历史上下文:
{history_context}
{user_section}{skills_section}已执行步骤:
{executed_steps}现在请输出下一步:
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
        """构建Plan-ReAct模式步骤提示词（优化版）

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

        results_str = PromptTemplates.format_plan_results(previous_results)

        prompt = f"""系统环境: {system_info['os_info']}
当前工作目录: {system_info['current_dir']}
Shell类型: {system_info['shell_type']}
当前日期: {system_info['current_date']}
当前时间: {system_info['current_time']}

任务类型: {task_info.get('level', '未知')}
任务描述: {task_info.get('reason', '无')}

历史上下文:
{history_context}

用户输入:
{task}

当前执行步骤:
{current_step}

可用行动:
{skills_list}
finish(answer) - 完成任务并返回答案

请按照以下格式输出:
思考: 你的思考过程
行动: 行动名称(参数)

重要提示:
- 当任务已经完成时，必须使用finish(answer)结束任务
- finish(answer)中的answer应该是对用户的最终回答
- 不要在任务完成后继续执行其他行动

之前步骤的结果:
{results_str}
现在请输出下一步:
"""
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
        prompt = f"""请为用户输入生成详细的任务规划，包括具体的步骤和预期结果。

任务类型: {task_info.get('level', '未知')}
任务描述: {task_info.get('reason', '无')}

历史上下文:
{history_context}

用户输入:
{task}

请以列表形式输出规划步骤，每个步骤描述具体要做什么：
1. 步骤1
2. 步骤2
3. 步骤3
...
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
            steps_str = PromptTemplates.format_executed_steps(steps, include_thought=True)
        else:
            steps_str = PromptTemplates.format_plan_results(steps)

        prompt = f"""
        请根据以下执行步骤，为用户输入生成最终响应:

        用户输入:
        {user_input}

        执行步骤:
        {steps_str}
        请生成简洁、友好的最终响应:
        """
        return prompt
