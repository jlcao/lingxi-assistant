import logging
from typing import Dict, Any, List, Callable, Optional
import traceback
import functools


class EventPublisher:
    """事件发布者"""

    def __init__(self):
        """初始化事件发布者"""
        self._subscribers: Dict[str, List[Callable]] = {}
        self._error_handlers: List[Callable] = []
        self.logger = logging.getLogger(__name__)

    def subscribe(self, event_type: str, callback: Callable):
        """订阅事件

        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        self.logger.debug(f"订阅事件: {event_type}, 回调: {self._get_callback_name(callback)}")

    def unsubscribe(self, event_type: str, callback: Callable):
        """取消订阅

        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
                self.logger.debug(f"取消订阅事件: {event_type}, 回调: {self._get_callback_name(callback)}")
            except ValueError:
                pass

    def add_error_handler(self, handler: Callable[[str, Callable, Exception], None]):
        """添加全局错误处理器

        Args:
            handler: 错误处理器，接收 (event_type, callback, exception)
        """
        self._error_handlers.append(handler)
        self.logger.debug(f"添加错误处理器: {self._get_callback_name(handler)}")

    def remove_error_handler(self, handler: Callable):
        """移除全局错误处理器

        Args:
            handler: 错误处理器
        """
        try:
            self._error_handlers.remove(handler)
            self.logger.debug(f"移除错误处理器: {self._get_callback_name(handler)}")
        except ValueError:
            pass

    def publish(self, event_type: str, **kwargs):
        """发布事件

        Args:
            event_type: 事件类型
            **kwargs: 事件参数
        """
        # 记录事件发布日志，无论是否有订阅者
        if event_type != "think_stream":
            self.logger.debug(f"发布事件: {event_type}，参数: {kwargs}")

        if event_type in self._subscribers:
            failed_callbacks = []
            for callback in self._subscribers[event_type]:
                try:
                    callback(**kwargs)
                except Exception as e:
                    callback_name = self._get_callback_name(callback)
                    error_msg = f"处理事件 {event_type} 时回调 {callback_name} 发生错误: {e}"
                    self.logger.error(error_msg)
                    self.logger.debug(f"错误堆栈:\n{traceback.format_exc()}")
                    
                    # 调用错误处理器
                    for error_handler in self._error_handlers:
                        try:
                            error_handler(event_type, callback, e)
                        except Exception as handler_error:
                            self.logger.error(f"错误处理器 {self._get_callback_name(error_handler)} 自身发生错误: {handler_error}")
                    
                    failed_callbacks.append(callback)
            
            # 移除失败的回调（可选，根据需求决定是否移除）
            # for failed_callback in failed_callbacks:
            #     self.unsubscribe(event_type, failed_callback)

    def _get_callback_name(self, callback: Callable) -> str:
        """获取回调函数名称

        Args:
            callback: 回调函数

        Returns:
            回调函数名称
        """
        if hasattr(callback, '__name__'):
            return callback.__name__
        elif hasattr(callback, '__class__'):
            return f"{callback.__class__.__name__} instance"
        else:
            return str(callback)

    def get_subscriber_count(self, event_type: Optional[str] = None) -> int:
        """获取订阅者数量

        Args:
            event_type: 事件类型，None表示所有事件

        Returns:
            订阅者数量
        """
        if event_type:
            return len(self._subscribers.get(event_type, []))
        return sum(len(subscribers) for subscribers in self._subscribers.values())

    def clear_subscribers(self, event_type: Optional[str] = None):
        """清除订阅者

        Args:
            event_type: 事件类型，None表示清除所有订阅者
        """
        if event_type:
            if event_type in self._subscribers:
                count = len(self._subscribers[event_type])
                self._subscribers[event_type].clear()
                self.logger.debug(f"清除事件 {event_type} 的 {count} 个订阅者")
        else:
            total_count = sum(len(subscribers) for subscribers in self._subscribers.values())
            self._subscribers.clear()
            self.logger.debug(f"清除所有 {total_count} 个订阅者")


# 全局事件发布者实例
global_event_publisher = EventPublisher()
