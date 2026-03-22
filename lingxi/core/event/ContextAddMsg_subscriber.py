import asyncio
import logging
import json
from typing import Dict, Any, TYPE_CHECKING

from starlette.middleware import P
from lingxi.core.context.task_context import TaskContext
from lingxi.core.event import global_event_publisher
from lingxi.core.context.session_context import ContentType
from lingxi.core.context.context_manager import ContextManager

if TYPE_CHECKING:
    from lingxi.core.session.session_manager import SessionManager
from lingxi.core.session.task_manager import TaskManager


class ContextAddMsgSubscriber:
    """上下文添加消息事件订阅者（单例模式）"""
    
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
        # 如果首次初始化时传入了 sessionManage，则保存
        self.logger = logging.getLogger(__name__)
        self._subscribe_to_events()
        self.context_manager = ContextManager()
        
        self._initialized = True

    def _subscribe_to_events(self):
        """订阅事件"""
        global_event_publisher.subscribe('task_start', self.handle_task_start)
        global_event_publisher.subscribe('plan_final', self.handle_plan_final)
        global_event_publisher.subscribe('step_end', self.handle_step_end)
        global_event_publisher.subscribe('task_failed', self.handle_task_failed)
        global_event_publisher.subscribe('task_end', self.handle_task_end)

        self.logger.info("会话存储订阅者已初始化，开始监听事件")

    def _unsubscribe_from_events(self):
        """取消订阅事件"""
        global_event_publisher.unsubscribe('task_start', self.handle_task_start)
        global_event_publisher.unsubscribe('plan_final', self.handle_plan_final)
        global_event_publisher.unsubscribe('step_end', self.handle_step_end)
        global_event_publisher.unsubscribe('task_end', self.handle_task_end)
        global_event_publisher.unsubscribe('task_failed', self.handle_task_failed)

        self.logger.info("会话存储订阅者已停止监听事件")



    def handle_task_start(self, context: TaskContext, **kwargs):
        """处理任务处理开始事件

        Args:
            context: 任务上下文
            **kwargs: 其他参数
        """
        task_id = context.task_id
        user_input = context.user_input
        #context.session_context.add_message(role='assistant', content=f"当前对话 task_id:{task_id} 开始",content_type=ContentType.USER_INPUT,task_id=task_id)
        #context.session_context.add_message(role='user', content=user_input,content_type=ContentType.USER_INPUT,task_id=task_id)

    def handle_plan_final(self, context: TaskContext, **kwargs):
        """处理任务规划开始事件

        Args:
            context: 任务上下文
            **kwargs: 其他参数
        """
        task_id = context.task_id
        context.session_context.add_message(role='assistant', content=f"任务规划：{context.task_info.plan}",content_type=ContentType.SYSTEM_MESSAGE,task_id=task_id)
        
    def handle_task_failed(self, context: TaskContext, **kwargs):
        """处理任务处理失败事件

        Args:
            context: 任务上下文
            **kwargs: 其他参数
        """
         #session会话结束，释放上下文
        self.context_manager.release_session_context(context.session_id)

    def handle_step_end(self, context: TaskContext, **kwargs):
        """处理步骤执行结束事件

        Args:
            context: 任务上下文
            step_index: 步骤索引
            result: 步骤执行结果（字符串或字典格式）
            **kwargs: 其他参数
        """
        task_id = context.task_id
        step = context.steps[-1]
        #if step.status == 'completed':
            #context.session_context.add_message(role='assistant', content=step.thought,content_type=ContentType.THINKING,task_id=task_id)
            #context.session_context.add_message(role='assistant', content=step.skill_call,content_type=ContentType.TOOL_CALL,task_id=task_id)
        context.session_context.add_message(role='assistant', content=f"step {step.step_index}, 工具调用:{step.skill_call},结果:{step.result}",content_type=ContentType.TOOL_RESULT,task_id=task_id)    
        

    def handle_task_end(self, context: TaskContext, **kwargs):
        """处理任务处理最终结果输出事件

        Args:
            context: 任务上下文
            **kwargs: 其他参数
        """
        task_info = context.task_info
        #session会话结束，释放上下文
        self.context_manager.release_session_context(context.session_id)
    def __del__(self):
        """析构函数，清理订阅"""
        try:
            self._unsubscribe_from_events()
        except Exception:
            pass
