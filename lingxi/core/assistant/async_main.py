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
from lingxi.core.session.session_models import Task
from lingxi.utils.config import get_workspace_path
from lingxi.core.event import global_event_publisher


class AsyncLingxiAssistant(BaseAssistant):
    """异步灵犀智能助手"""

    async def process_input(self, user_input: str, session_id: str = "default", task_id: str = None, stream: bool = False, thinking_mode: bool = False):
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

        from lingxi.core.context.task_context_manager import TaskContextManager
        from lingxi.core.context.task_context import TaskStoppedException
        
        task_context_manager = TaskContextManager()

        try:
            # 根据配置决定是否启用历史压缩
            history = self.session_manager.get_history(session_id)
            engine = AsyncPlanReActEngine(self.config, self.action_caller, self.session_manager)
            session_context = self.context_manager.get_session_context(session_id)
            # 添加历史会话到上下文管理器
            session_context.add_history(history)
            context = TaskContext(
                user_input=user_input,
                session_id=session_id,
                task_id=task_id,
                session_history=history,
                stream=stream,
                workspace_path=get_workspace_path(),
                thinking_mode=thinking_mode,
                session_context=session_context
            )
            #注入SOUL和记忆上下文
            self.context_manager._build_soul_and_memory(context)
            self.context_manager._build_memory_context(context)
            
            # 注册任务
            await task_context_manager.register_task(context)
            
            if stream:
                # 流式模式：返回异步生成器
                async def stream_generator():
                    try:
                        # engine.process() 是协程，需要先 await 获取异步生成器
                        response = await engine.process(context)
                        async for chunk in response:
                            yield chunk
                    except TaskStoppedException:
                        # 任务被终止
                        self.logger.info(f"任务被终止: task_id={context.task_id}")
                        self._publish_task_stop(context=context,result="任务被终止")
                        yield {
                            "type": "task_stopped",
                            "result": "任务已被用户终止",
                            "task_id": context.task_id
                        }
                    except Exception as e:
                        import traceback
                        error_trace = traceback.format_exc()
                        self.logger.error(f"流式处理失败：{e}\n{error_trace}")
                        self._publish_task_failed(context=context,error=str(e))
                        yield {"type": "error", "message": f"处理失败：{str(e)}"}
                    finally:
                        # 注销任务
                        await task_context_manager.unregister_task(context.task_id)
                return stream_generator()
            else:
                # 非流式模式：直接等待结果
                try:
                    response = await engine.process(context)
                    return context.task_info
                finally:
                    # 注销任务
                    await task_context_manager.unregister_task(context.task_id)
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

    async def stream_process_input(self, user_input: str, session_id: str = "default", task_id: str = None, thinking_mode: bool = False):
        """异步流式处理用户输入

        Args:
            user_input: 用户输入
            session_id: 会话 ID
            thinking_mode: 是否开启思考模式

        Returns:
            异步流式响应生成器
        """
        from lingxi.core.context.task_context_manager import TaskContextManager
        from lingxi.core.context.task_context import TaskStoppedException
        
        task_context_manager = TaskContextManager()
        
        # 获取 TaskContext
        history = self.session_manager.get_history(session_id)
        engine = AsyncPlanReActEngine(self.config, self.action_caller, self.session_manager)
        session_context = self.context_manager.get_session_context(session_id)
        session_context.add_history(history)
        context = TaskContext(
            user_input=user_input,
            session_id=session_id,
            task_id=task_id,
            session_history=history,
            stream=True,
            workspace_path=get_workspace_path(),
            thinking_mode=thinking_mode,
            session_context=session_context,
            model_name=self.config.get("llm",{}).get("model",""),
        )
        self.context_manager._build_soul_and_memory(context)
        self.context_manager._build_memory_context(context)
        
        # 注册任务
        await task_context_manager.register_task(context)
        
        try:
            # 调用执行引擎
            response = await engine.process(context)
            async for chunk in response:
                yield chunk 
        except TaskStoppedException:
            # 任务被终止
            self.logger.info(f"任务被终止: task_id={context.task_id}")
            self._publish_task_stop(context=context,result="任务被终止")
            # 发送终止响应
            yield {
                "type": "task_stopped",
                "result": "任务已被用户终止",
                "task_id": context.task_id
            }
        except Exception as e:
            # 处理其他异常
            self.logger.error(f"任务执行失败: {e}", exc_info=True)
            self._publish_task_failed(context=context,error=str(e))
            raise
        finally:
            # 注销任务
            await task_context_manager.unregister_task(context.task_id)

    def _publish_task_failed(self, context: TaskContext, error: str):
        """发布任务失败事件

        Args:
            context: 任务上下文
            error: 错误信息
            task_id: 任务 ID
        """
        global_event_publisher.publish(
            'task_failed',
            context=context,
            error=error
        )

    
    def _publish_task_stop(self, context: TaskContext, result: str):
        """发布任务失败事件

        Args:
            context: 任务上下文
            error: 错误信息
            task_id: 任务 ID
        """
        context.task_info.result = result
        context.task_info.status = "interrupted"
        global_event_publisher.publish(
            'task_end',
            context=context,
            result=result,
            input_tokens=context.input_tokens,
            output_tokens=context.output_tokens
        )


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
