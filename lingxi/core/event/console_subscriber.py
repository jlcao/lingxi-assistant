import logging
import sys
from typing import Dict, Any
from lingxi.core.event import global_event_publisher


class ConsoleSubscriber:
    """控制台事件订阅者 - 统一处理控制台输出（单例模式）"""
    
    _instance = None  # 单例实例
    
    def __new__(cls):
        """单例模式：确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # 防止重复初始化
        if hasattr(self, '_initialized'):
            return
        self.logger = logging.getLogger(__name__)
        self._final_result: str = ""
        self._subscribe_to_events()
        self._initialized = True
    
    def _print(self, *args, **kwargs):
        """安全的打印方法，处理 stdout 关闭的情况"""
        if hasattr(sys, 'stdout') and sys.stdout and not sys.stdout.closed:
            print(*args, **kwargs)

    def _subscribe_to_events(self):
        global_event_publisher.subscribe('think_start', self.handle_think_start)
        global_event_publisher.subscribe('think_final', self.handle_think_final)
        global_event_publisher.subscribe('think_stream', self.handle_think_stream)
        global_event_publisher.subscribe('plan_start', self.handle_plan_start)
        global_event_publisher.subscribe('plan_final', self.handle_plan_final)
        global_event_publisher.subscribe('step_start', self.handle_step_start)
        global_event_publisher.subscribe('step_end', self.handle_step_end)
        global_event_publisher.subscribe('task_start', self.handle_task_start)
        global_event_publisher.subscribe('task_end', self.handle_task_end)

        self.logger.debug("控制台订阅者已初始化")

    def _unsubscribe_from_events(self):
        global_event_publisher.unsubscribe('think_start', self.handle_think_start)
        global_event_publisher.unsubscribe('think_final', self.handle_think_final)
        global_event_publisher.unsubscribe('think_stream', self.handle_think_stream)
        global_event_publisher.unsubscribe('plan_start', self.handle_plan_start)
        global_event_publisher.unsubscribe('plan_final', self.handle_plan_final)
        global_event_publisher.unsubscribe('step_start', self.handle_step_start)
        global_event_publisher.unsubscribe('step_end', self.handle_step_end)
        global_event_publisher.unsubscribe('task_start', self.handle_task_start)
        global_event_publisher.unsubscribe('task_end', self.handle_task_end)

    def handle_task_start(self, session_id: str, execution_id: str, **kwargs):
        self._print("\n🚀 任务开始处理...")

    def handle_think_start(self, session_id: str, execution_id: str, **kwargs):
        self._print("💭 思考中...")

    def handle_think_stream(self, session_id: str, execution_id: str, content: str, **kwargs):
        self._print(f"{content}", end="", flush=True)

    def handle_think_final(self, session_id: str, execution_id: str, content: str, **kwargs):
        self._print()

    def handle_plan_start(self, session_id: str, execution_id: str, **kwargs):
        pass

    def handle_plan_final(self, session_id: str, execution_id: str, plan: list, **kwargs):
        self._print("\n📋 任务规划:")
        for i, step in enumerate(plan, 1):
            desc = step if isinstance(step, str) else step.get('description', str(step))
            self._print(f"   {i}. {desc}")

    def handle_step_start(self, session_id: str, execution_id: str, step_index: int, **kwargs):
        # description 可能包含换行符
        description = kwargs.get('description', '')
        if description:
            formatted_desc = self._format_console_output(description)
            self._print(f"\n📍 执行步骤 {step_index + 1}: {formatted_desc}")
        else:
            self._print(f"\n📍 执行步骤 {step_index + 1}...")

    def handle_step_end(self, session_id: str, execution_id: str, step_index: int, result: str, **kwargs):
        # result 可能是字符串或字典
        if result:
            # 格式化输出，处理换行符和 Markdown 格式
            formatted_result = self._format_console_output(result)
            preview = formatted_result[:200] + '...' if len(formatted_result) > 200 else formatted_result
            self._print(f"\n   ✅ 完成：{preview}")

    def _format_console_output(self, text: str) -> str:
        """格式化控制台输出文本

        Args:
            text: 原始文本（可能包含 Markdown 格式和换行符）

        Returns:
            格式化后的文本
        """
        if not text:
            return ""
        
        # 如果是字典，提取 answer 字段
        if isinstance(text, dict):
            text = text.get('answer', str(text))
        
        # 确保是字符串
        text = str(text)
        
        # 处理换行符
        lines = text.split('\\n')
        
        # 移除 Markdown 加粗标记 **
        formatted_lines = [line.replace('**', '') for line in lines]
        
        # 重新组合
        return '\n'.join(formatted_lines)

    def handle_task_end(self, session_id: str, execution_id: str, result: str, **kwargs):
        self._final_result = result if isinstance(result, str) else str(result)
        # 格式化输出，处理换行符和 Markdown 格式
        formatted_result = self._format_console_output(result)
        self._print(f"\n✨ 最终结果:\n{formatted_result}")

    def get_final_result(self) -> str:
        return self._final_result

    def __del__(self):
        try:
            self._unsubscribe_from_events()
        except Exception:
            pass
