"""异步灵犀智能助手主类

完全异步化的助手类，解决 WebSocket 阻塞问题
"""

import sys
import logging
import asyncio
from typing import Optional, Union, Any, Dict, List
from collections.abc import AsyncGenerator
from lingxi.utils.config import load_config
from lingxi.utils.logging import setup_logging
from lingxi.core.session import SessionManager
from lingxi.core.classifier import TaskClassifier
from lingxi.core.mode_selector import ExecutionModeSelector
from lingxi.core.skill_caller import SkillCaller
from lingxi.core.event.console_subscriber import ConsoleSubscriber
from lingxi.core.event.SessionStore_subscriber import SessionStoreSubscriber
from lingxi.core.context import TaskContext
from lingxi.core.engine.async_plan_react import AsyncPlanReActEngine


class AsyncLingxiAssistant:
    """异步灵犀智能助手主类"""

    def __init__(self, config_path_or_obj: Union[str, Dict[str, Any]] = "config.yaml"):
        """初始化异步灵犀助手

        Args:
            config_path_or_obj: 配置文件路径或配置对象
        """
        if isinstance(config_path_or_obj, dict):
            self.config = config_path_or_obj
        else:
            self.config = load_config(config_path_or_obj)
        setup_logging(self.config)
        self.logger = logging.getLogger(__name__)

        self.logger.info(f"启动{self.config.get('system', {}).get('name', '灵犀')}智能助手")
        self.logger.info(f"版本: {self.config.get('system', {}).get('version', '0.2.0')}")

        self.session_manager = SessionManager(self.config)
        self.classifier = TaskClassifier(self.config)
        self.skill_caller = SkillCaller(self.config)
        self.mode_selector = ExecutionModeSelector(self.config, self.skill_caller)
        self.console_subscriber = ConsoleSubscriber()
        self.session_store_subscriber = SessionStoreSubscriber(self.session_manager)

    async def process_input(self, user_input: str, session_id: str = "default", stream: bool = False):
        """异步处理用户输入

        Args:
            user_input: 用户输入
            session_id: 会话ID
            stream: 是否启用流式输出

        Returns:
            系统响应（非流式）或异步流式响应生成器（流式）
        """
        self.logger.debug(f"异步处理用户输入: {user_input}")

        try:
            # 先检查是否是安装技能的请求
            install_result = self._check_install_skill_intent(user_input)
            if install_result:
                skill_path, skill_name = install_result
                success = await self.install_skill_async(skill_path, skill_name)
                if success:
                    response = f"技能安装成功: {skill_path}"
                else:
                    response = f"技能安装失败: {skill_path}"
                return response

            history = self.session_manager.get_history(session_id)

            # 使用异步引擎
            engine = AsyncPlanReActEngine(self.config, self.skill_caller, self.session_manager)

            context = TaskContext(
                user_input=user_input,
                task_info={"level": "complex"},
                session_id=session_id,
                session_history=history,
                stream=stream
            )

            response = await engine.process(context)

            return response

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            self.logger.error(f"异步处理失败: {e}\n{traceback.format_exc()}")
            error_response = f"抱歉，处理您的请求时出现错误：{str(e)}\n\n堆栈信息:\n{error_trace}"
            if stream:
                async def error_generator():
                    yield {"type": "error", "message": error_response}
                return error_generator()
            return error_response

    async def stream_process_input(self, user_input: str, session_id: str = "default"):
        """异步流式处理用户输入

        Args:
            user_input: 用户输入
            session_id: 会话 ID

        Returns:
            异步流式响应生成器
        """
        result = await self.process_input(user_input, session_id, stream=True)
        async for chunk in result:
            yield chunk

    def _check_install_skill_intent(self, user_input: str) -> Optional[tuple]:
        """检查是否是安装技能的请求

        Args:
            user_input: 用户输入

        Returns:
            如果是安装请求，返回 (skill_path, skill_name)，否则返回 None
        """
        import re
        from pathlib import Path

        user_input_lower = user_input.lower()

        # 检查是否包含安装技能的关键词
        install_keywords = ['安装技能', 'install skill', '添加技能']
        has_install_keyword = any(kw in user_input_lower for kw in install_keywords)
        
        if not has_install_keyword:
            return None

        # 提取路径和名称
        skill_path = None
        skill_name = None

        # 尝试匹配带名称的格式
        name_patterns = [
            r'安装技能\s+(.+?)\s*(?:名称为|name\s+is|as)\s+(.+)',
            r'install\s+skill\s+(.+?)\s*(?:name\s+is|as)\s+(.+)',
            r'添加技能\s+(.+?)\s*(?:名称为|name\s+is|as)\s+(.+)',
        ]
        for pattern in name_patterns:
            match = re.match(pattern, user_input_lower)
            if match:
                skill_path = match.group(1).strip()
                skill_name = match.group(2).strip()
                break

        # 如果没有匹配到带名称的格式，尝试匹配不带名称的格式
        if not skill_path:
            install_patterns = [
                r'安装技能\s+(.+)',
                r'install\s+skill\s+(.+)',
                r'添加技能\s+(.+)',
            ]
            for pattern in install_patterns:
                match = re.match(pattern, user_input_lower)
                if match:
                    skill_path = match.group(1).strip()
                    break

        if not skill_path:
            return None

        # 检查路径是否存在
        if not Path(skill_path).exists():
            self.logger.warning(f"技能路径不存在: {skill_path}")
            return None

        self.logger.debug(f"检测到安装技能请求: {skill_path}, 新名称: {skill_name}")
        return (skill_path, skill_name)

    async def install_skill_async(self, skill_path: str, skill_name: str = None, overwrite: bool = False) -> bool:
        """异步安装技能

        Args:
            skill_path: 技能路径
            skill_name: 技能名称
            overwrite: 是否覆盖已存在的技能

        Returns:
            是否安装成功
        """
        try:
            # 在线程池中执行同步的技能安装
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self.install_skill,
                skill_path,
                skill_name,
                overwrite
            )
        except Exception as e:
            self.logger.error(f"异步安装技能失败: {e}", exc_info=True)
            return False

    def install_skill(self, skill_path: str, skill_name: str = None, overwrite: bool = False) -> bool:
        """安装技能（同步版本）

        Args:
            skill_path: 技能路径
            skill_name: 技能名称
            overwrite: 是否覆盖已存在的技能

        Returns:
            是否安装成功
        """
        from lingxi.skills.installer import SkillInstaller
        installer = SkillInstaller(self.config)
        return installer.install(skill_path, skill_name, overwrite)

    async def cleanup_checkpoints(self, ttl_hours: int = 24) -> int:
        """清理过期检查点

        Args:
            ttl_hours: 生存时间（小时）

        Returns:
            清理的检查点数量
        """
        # 在线程池中执行同步操作
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.session_manager.cleanup_expired_checkpoints,
            ttl_hours
        )

    async def list_checkpoints(self):
        """列出所有活跃检查点"""
        # 在线程池中执行同步操作
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.session_manager.list_active_checkpoints
        )