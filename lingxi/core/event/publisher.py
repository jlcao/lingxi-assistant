import logging
from typing import Dict, Any, List, Callable, Optional


class EventPublisher:
    """事件发布者"""

    def __init__(self):
        """初始化事件发布者"""
        self._subscribers: Dict[str, List[Callable]] = {}
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
        self.logger.debug(f"订阅事件: {event_type}")

    def unsubscribe(self, event_type: str, callback: Callable):
        """取消订阅

        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(callback)
                self.logger.debug(f"取消订阅事件: {event_type}")
            except ValueError:
                pass

    def publish(self, event_type: str, **kwargs):
        """发布事件

        Args:
            event_type: 事件类型
            **kwargs: 事件参数
        """
        # 记录事件发布日志，无论是否有订阅者
        if(event_type !="think_stream"):
            self.logger.debug(f"发布事件: {event_type}，参数: {kwargs}")

        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                try:
                    callback(**kwargs)
                except Exception as e:
                    import traceback
                    self.logger.error(f"处理事件 {event_type} 时发生错误: {e}")
                    traceback.print_exc()

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


# 全局事件发布者实例
global_event_publisher = EventPublisher()
