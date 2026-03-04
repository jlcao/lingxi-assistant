import asyncio
import logging
import concurrent.futures
from typing import Dict, Any, TYPE_CHECKING
from lingxi.core.event import global_event_publisher

if TYPE_CHECKING:
    from lingxi.web.websocket import WebSocketManager


class WebSocketSubscriber:
    """WebSocket 事件订阅者"""

    def __init__(self, websocket_manager: 'WebSocketManager'):
        """初始化 WebSocket 订阅者

        Args:
            websocket_manager: WebSocket 管理器实例
        """
        self.websocket_manager = websocket_manager 
        self.logger = logging.getLogger(__name__)
        self._loop = asyncio.new_event_loop()
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self._subscribe_to_events()

    def _subscribe_to_events(self):
        """订阅事件"""
        global_event_publisher.subscribe('think_start', self.handle_think_start)
        global_event_publisher.subscribe('think_final', self.handle_think_final)
        global_event_publisher.subscribe('think_stream', self.handle_think_stream)
        global_event_publisher.subscribe('plan_start', self.handle_plan_start)
        global_event_publisher.subscribe('plan_final', self.handle_plan_final)
        global_event_publisher.subscribe('step_start', self.handle_step_start)
        global_event_publisher.subscribe('step_end', self.handle_step_end)
        global_event_publisher.subscribe('task_start', self.handle_task_start)
        global_event_publisher.subscribe('task_end', self.handle_task_end)

        self.logger.info("WebSocket订阅者已初始化，开始监听事件")

    def _unsubscribe_from_events(self):
        """取消订阅事件"""
        global_event_publisher.unsubscribe('think_start', self.handle_think_start)
        global_event_publisher.unsubscribe('think_final', self.handle_think_final)
        global_event_publisher.unsubscribe('think_stream', self.handle_think_stream)
        global_event_publisher.unsubscribe('plan_start', self.handle_plan_start)
        global_event_publisher.unsubscribe('plan_final', self.handle_plan_final)
        global_event_publisher.unsubscribe('step_start', self.handle_step_start)
        global_event_publisher.unsubscribe('step_end', self.handle_step_end)
        global_event_publisher.unsubscribe('task_start', self.handle_task_start)
        global_event_publisher.unsubscribe('task_end', self.handle_task_end)

        self.logger.info("WebSocket订阅者已停止监听事件")

    def _send_event_async(self, session_id: str, event_type: str, execution_id: str, data: dict):
        """异步发送事件（使用线程池避免阻塞）
        
        Args:
            session_id: 会话 ID
            event_type: 事件类型
            execution_id: 执行 ID
            data: 事件数据
        """
        def send_event():
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(self.websocket_manager.send_event(
                    session_id=session_id,
                    event_type=event_type,
                    execution_id=execution_id,
                    data=data
                ))
            finally:
                loop.close()
        self._executor.submit(send_event)

    def handle_think_start(self, session_id: str, execution_id: str, **kwargs):
        """处理思考开始事件

        Args:
            session_id: 会话 ID
            execution_id: 执行 ID
            **kwargs: 其他参数
        """
        if self.websocket_manager:
            self._send_event_async(session_id, 'think_start', execution_id, kwargs)

    def handle_think_stream(self, session_id: str, execution_id: str, content: str, **kwargs):
        """处理思考块流式渲染事件

        Args:
            session_id: 会话 ID
            execution_id: 执行 ID
            content: 思考内容
            **kwargs: 其他参数
        """
        self.logger.debug(f"Received think_stream event: session_id={session_id}, execution_id={execution_id}, content={content}, kwargs={kwargs}")
        if self.websocket_manager:
            self._send_event_async(session_id, 'think_stream', execution_id, {"content": content, **kwargs})
        else:
            self.logger.warning("websocket_manager is None, cannot send think_stream event")

    def handle_think_final(self, session_id: str, execution_id: str, content: str, **kwargs):
        """处理思考结束事件

        Args:
            session_id: 会话 ID
            execution_id: 执行 ID
            content: 思考内容
            **kwargs: 其他参数
        """
        if self.websocket_manager:
            self._send_event_async(session_id, 'think_final', execution_id, {"content": content, **kwargs})

    def handle_plan_start(self, session_id: str, execution_id: str, **kwargs):
        """处理任务规划开始事件

        Args:
            session_id: 会话 ID
            execution_id: 执行 ID
            **kwargs: 其他参数
        """
        if self.websocket_manager:
            self._send_event_async(session_id, 'plan_start', execution_id, kwargs)

    def handle_plan_final(self, session_id: str, execution_id: str, plan: list, **kwargs):
        """处理任务规划完成事件

        Args:
            session_id: 会话 ID
            execution_id: 执行 ID
            plan: 任务计划（包含每个步骤）
            **kwargs: 其他参数
        """
        if self.websocket_manager:
            self._send_event_async(session_id, 'plan_final', execution_id, {"plan": plan, **kwargs})

    def handle_step_start(self, session_id: str, execution_id: str, step_index: int, **kwargs):
        """处理步骤开始事件

        Args:
            session_id: 会话 ID
            execution_id: 执行 ID
            step_index: 步骤索引
            **kwargs: 其他参数
        """
        if self.websocket_manager:
            self._send_event_async(session_id, 'step_start', execution_id, {"step_index": step_index, **kwargs})

    def handle_step_end(self, session_id: str, execution_id: str, step_index: int, result: str, **kwargs):
        """处理步骤执行结束事件

        Args:
            session_id: 会话 ID
            execution_id: 执行 ID
            step_index: 步骤索引
            result: 步骤执行结果（包含观察和执行）
            **kwargs: 其他参数
        """
        if self.websocket_manager:
            self._send_event_async(session_id, 'step_end', execution_id, {"step_index": step_index, "result": result, **kwargs})

    def handle_task_start(self, session_id: str, execution_id: str, **kwargs):
        """处理任务处理开始事件

        Args:
            session_id: 会话 ID
            execution_id: 执行 ID
            **kwargs: 其他参数
        """
        if self.websocket_manager:
            self._send_event_async(session_id, 'task_start', execution_id, kwargs)

    def handle_task_end(self, session_id: str, execution_id: str, result: str, **kwargs):
        """处理任务处理最终结果输出事件

        Args:
            session_id: 会话 ID
            execution_id: 执行 ID
            result: 最终结果
            **kwargs: 其他参数
        """
        if self.websocket_manager:
            self._send_event_async(session_id, 'task_end', execution_id, {"result": result, **kwargs})

    def __del__(self):
        """析构函数，清理订阅"""
        try:
            self._unsubscribe_from_events()
        except Exception:
            pass
        try:
            if hasattr(self, '_executor'):
                self._executor.shutdown(wait=False)
            if hasattr(self, '_loop'):
                self._loop.close()
        except Exception:
            pass
