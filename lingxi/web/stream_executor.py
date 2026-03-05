import asyncio
import logging
from typing import Dict, Any, Optional, Generator, Callable
from lingxi.core.event import global_event_publisher
from lingxi.core.engine.base import BaseEngine
from lingxi.core.exceptions import map_exception_to_error_code


class StreamEventCollector:
    """流式事件收集器 - 将事件发布转换为流式生成器"""

    def __init__(self, session_id: str, execution_id: str):
        """初始化事件收集器

        Args:
            session_id: 会话ID
            execution_id: 执行ID
        """
        self.session_id = session_id
        self.execution_id = execution_id
        self.logger = logging.getLogger(__name__)
        self._event_queue: asyncio.Queue = None
        self._subscribed = False

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self._event_queue = asyncio.Queue()
        self._subscribe_to_events()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        self._unsubscribe_from_events()
        if self._event_queue:
            await self._event_queue.put(("done", None))

    def _subscribe_to_events(self):
        """订阅事件"""
        if self._subscribed:
            return

        global_event_publisher.subscribe('think_start', self._handle_think_start)
        global_event_publisher.subscribe('think_final', self._handle_think_final)
        global_event_publisher.subscribe('think_stream', self._handle_think_stream)
        global_event_publisher.subscribe('plan_start', self._handle_plan_start)
        global_event_publisher.subscribe('plan_final', self._handle_plan_final)
        global_event_publisher.subscribe('step_start', self._handle_step_start)
        global_event_publisher.subscribe('step_end', self._handle_step_end)
        global_event_publisher.subscribe('task_start', self._handle_task_start)
        global_event_publisher.subscribe('task_end', self._handle_task_end)
        global_event_publisher.subscribe('task_failed', self._handle_task_failed)

        self._subscribed = True
        self.logger.debug(f"事件收集器已订阅: session_id={self.session_id}, execution_id={self.execution_id}")

    def _unsubscribe_from_events(self):
        """取消订阅事件"""
        if not self._subscribed:
            return

        global_event_publisher.unsubscribe('think_start', self._handle_think_start)
        global_event_publisher.unsubscribe('think_final', self._handle_think_final)
        global_event_publisher.unsubscribe('think_stream', self._handle_think_stream)
        global_event_publisher.unsubscribe('plan_start', self._handle_plan_start)
        global_event_publisher.unsubscribe('plan_final', self._handle_plan_final)
        global_event_publisher.unsubscribe('step_start', self._handle_step_start)
        global_event_publisher.unsubscribe('step_end', self._handle_step_end)
        global_event_publisher.unsubscribe('task_start', self._handle_task_start)
        global_event_publisher.unsubscribe('task_end', self._handle_task_end)
        global_event_publisher.unsubscribe('task_failed', self._handle_task_failed)

        self._subscribed = False
        self.logger.debug(f"事件收集器已取消订阅: session_id={self.session_id}, execution_id={self.execution_id}")

    def _filter_event(self, session_id: str, execution_id: str) -> bool:
        """过滤事件，只处理匹配的事件

        Args:
            session_id: 事件的会话ID
            execution_id: 事件的执行ID

        Returns:
            是否匹配
        """
        return session_id == self.session_id and execution_id == self.execution_id

    async def _put_event(self, event_type: str, data: Dict[str, Any]):
        """将事件放入队列

        Args:
            event_type: 事件类型
            data: 事件数据
        """
        if self._event_queue:
            await self._event_queue.put((event_type, data))

    def _handle_think_start(self, session_id: str, execution_id: str, **kwargs):
        """处理思考开始事件"""
        if self._filter_event(session_id, execution_id):
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._put_event("think_start", kwargs))
            except RuntimeError:
                if self._event_queue:
                    self._event_queue.put_nowait(("think_start", kwargs))

    def _handle_think_final(self, session_id: str, execution_id: str, content: str, **kwargs):
        """处理思考完成事件"""
        if self._filter_event(session_id, execution_id):
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._put_event("think_final", {"content": content, **kwargs}))
            except RuntimeError:
                if self._event_queue:
                    self._event_queue.put_nowait(("think_final", {"content": content, **kwargs}))

    def _handle_think_stream(self, session_id: str, execution_id: str, content: str, **kwargs):
        """处理思考流式事件"""
        if self._filter_event(session_id, execution_id):
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._put_event("think_stream", {"content": content, **kwargs}))
            except RuntimeError:
                if self._event_queue:
                    self._event_queue.put_nowait(("think_stream", {"content": content, **kwargs}))

    def _handle_plan_start(self, session_id: str, execution_id: str, **kwargs):
        """处理计划开始事件"""
        if self._filter_event(session_id, execution_id):
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._put_event("plan_start", kwargs))
            except RuntimeError:
                if self._event_queue:
                    self._event_queue.put_nowait(("plan_start", kwargs))

    def _handle_plan_final(self, session_id: str, execution_id: str, plan: list, **kwargs):
        """处理计划完成事件"""
        if self._filter_event(session_id, execution_id):
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._put_event("plan_final", {"plan": plan, **kwargs}))
            except RuntimeError:
                if self._event_queue:
                    self._event_queue.put_nowait(("plan_final", {"plan": plan, **kwargs}))

    def _handle_step_start(self, session_id: str, execution_id: str, step_index: int, **kwargs):
        """处理步骤开始事件"""
        if self._filter_event(session_id, execution_id):
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._put_event("step_start", {"step_index": step_index, **kwargs}))
            except RuntimeError:
                if self._event_queue:
                    self._event_queue.put_nowait(("step_start", {"step_index": step_index, **kwargs}))

    def _handle_step_end(self, session_id: str, execution_id: str, step_index: int, result: str, **kwargs):
        """处理步骤结束事件"""
        if self._filter_event(session_id, execution_id):
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._put_event("step_end", {"step_index": step_index, "result": result, **kwargs}))
            except RuntimeError:
                if self._event_queue:
                    self._event_queue.put_nowait(("step_end", {"step_index": step_index, "result": result, **kwargs}))

    def _handle_task_start(self, session_id: str, execution_id: str, **kwargs):
        """处理任务开始事件"""
        if self._filter_event(session_id, execution_id):
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._put_event("task_start", kwargs))
            except RuntimeError:
                if self._event_queue:
                    self._event_queue.put_nowait(("task_start", kwargs))

    def _handle_task_end(self, session_id: str, execution_id: str, result: str, **kwargs):
        """处理任务结束事件"""
        if self._filter_event(session_id, execution_id):
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._put_event("task_end", {"result": result, **kwargs}))
            except RuntimeError:
                if self._event_queue:
                    self._event_queue.put_nowait(("task_end", {"result": result, **kwargs}))

    def _handle_task_failed(self, session_id: str, execution_id: str, error: str, **kwargs):
        """处理任务失败事件"""
        if self._filter_event(session_id, execution_id):
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(self._put_event("task_failed", {"error": error, **kwargs}))
            except RuntimeError:
                if self._event_queue:
                    self._event_queue.put_nowait(("task_failed", {"error": error, **kwargs}))

    async def events(self) -> Generator[Dict[str, Any], None, None]:
        """生成事件流

        Yields:
            事件字典
        """
        while True:
            event_type, event_data = await self._event_queue.get()
            
            if event_type == "done":
                break
            
            yield {
                "type": event_type,
                **event_data
            }


async def execute_with_stream_events(
    engine: BaseEngine,
    task: str,
    task_info: Dict[str, Any],
    history: list,
    session_id: str,
    execution_id: str,
    stream: bool = True
) -> Generator[Dict[str, Any], None, None]:
    """执行引擎并收集流式事件

    Args:
        engine: 执行引擎实例
        task: 任务文本
        task_info: 任务信息
        history: 会话历史
        session_id: 会话 ID
        execution_id: 执行 ID
        stream: 是否流式输出

    Yields:
        事件字典
    """
    # 生成 task_id
    task_id = f"task_{session_id}_{execution_id[:8]}" if len(execution_id) > 8 else f"task_{session_id}_{execution_id}"
    
    # 在线程函数内部设置 local_context（因为 threading.local 是线程隔离的）
    def run_engine():
        from lingxi.core.context import set_ids
        # 设置当前线程的上下文 ID
        set_ids(session_id, task_id, execution_id, task)
        # 执行引擎
        return engine.process(task, task_info, history, session_id, stream)
    
    async with StreamEventCollector(session_id, execution_id) as collector:
        task_executor = asyncio.create_task(
            asyncio.to_thread(run_engine)
        )

        async for event in collector.events():
            yield event

        try:
            await task_executor
        except Exception as e:
            import traceback
            error_code, recoverable = map_exception_to_error_code(e)
            yield {
                "type": "error",
                "message": str(e),
                "error_code": error_code,
                "recoverable": recoverable,
                "traceback": traceback.format_exc()
            }
