"""异步灵犀智能助手主类

完全异步化的助手类，解决 WebSocket 阻塞问题
"""

import asyncio
import logging
from typing import Optional, Union, Any, Dict
from collections.abc import AsyncGenerator
from lingxi.core.assistant.assistant_base import BaseAssistant
from lingxi.core.engine.async_plan_react import AsyncPlanReActEngine
from lingxi.core.context.task_context import TaskContext


class AsyncLingxiAssistant(BaseAssistant):
    """异步灵犀智能助手"""

    async def process_input(self, user_input: str, session_id: str = "default", stream: bool = False, thinking_mode: bool = False):
        """异步处理用户输入

        Args:
            user_input: 用户输入
            session_id: 会话 ID
            stream: 是否启用流式输出
            thinking_mode: 是否开启思考模式

        Returns:
            系统响应（非流式）或异步流式响应生成器（流式）
        """
        self.logger.debug(f"异步处理用户输入：{user_input}")

        try:
            install_result = self._check_install_skill_intent(user_input)
            if install_result:
                skill_path, skill_name = install_result
                success = await self.install_skill_async(skill_path, skill_name)
                if success:
                    response = f"技能安装成功：{skill_path}"
                else:
                    response = f"技能安装失败：{skill_path}"
                return response

            # 根据配置决定是否启用历史压缩
            compress_enabled = self.config.get("context_management", {}).get("compression", {}).get("enabled", False)
            history = self.session_manager.get_history(session_id, compress=compress_enabled)

            engine = AsyncPlanReActEngine(self.config, self.skill_caller, self.session_manager)

            session_context = self.context_manager.get_session_context(session_id)

            workspace_path = str(self.workspace_manager.current_workspace) if self.workspace_manager.current_workspace else None

            context = TaskContext(
                user_input=user_input,
                task_info={"level": "simple"},
                session_id=session_id,
                session_history=history,
                stream=stream,
                workspace_path=workspace_path,
                thinking_mode=thinking_mode,
                session_context=session_context
            )

            response = await engine.process(context)

            return response

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            self.logger.error(f"异步处理失败：{e}\n{traceback.format_exc()}")
            error_response = f"抱歉，处理您的请求时出现错误：{str(e)}\n\n堆栈信息:\n{error_trace}"
            if stream:
                async def error_generator():
                    yield {"type": "error", "message": error_response}
                return error_generator()
            return error_response

    async def stream_process_input(self, user_input: str, session_id: str = "default", thinking_mode: bool = False):
        """异步流式处理用户输入

        Args:
            user_input: 用户输入
            session_id: 会话 ID
            thinking_mode: 是否开启思考模式

        Returns:
            异步流式响应生成器
        """
        result = await self.process_input(user_input, session_id, stream=True, thinking_mode=thinking_mode)
        async for chunk in result:
            yield chunk

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
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self.install_skill,
                skill_path,
                skill_name,
                overwrite
            )
        except Exception as e:
            self.logger.error(f"异步安装技能失败：{e}", exc_info=True)
            return False

    async def cleanup_checkpoints(self, ttl_hours: int = 24) -> int:
        """异步清理过期检查点

        Args:
            ttl_hours: 生存时间（小时）

        Returns:
            清理的检查点数量
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.session_manager.cleanup_expired_checkpoints,
            ttl_hours
        )

    async def list_checkpoints(self):
        """异步列出活跃检查点"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.session_manager.list_active_checkpoints
        )
