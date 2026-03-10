import asyncio
import logging
import json
from typing import Dict, Any, TYPE_CHECKING

from starlette.middleware import P
from lingxi.core.event import global_event_publisher

if TYPE_CHECKING:
    from lingxi.core.session.session_manager import SessionManager


class SessionStoreSubscriber:
    """会话存储事件订阅者（单例模式）"""
    
    _instance = None  # 单例实例
    
    def __new__(cls, sessionManage: 'SessionManager' = None):
        """单例模式：确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, sessionManage: 'SessionManager' = None):
        # 防止重复初始化
        if hasattr(self, '_initialized'):
            return
        # 如果首次初始化时传入了 sessionManage，则保存
        if sessionManage:
            self.sessionManage = sessionManage
        self.logger = logging.getLogger(__name__)
        self._subscribe_to_events()
        self._initialized = True

    def _subscribe_to_events(self):
        """订阅事件"""
        global_event_publisher.subscribe('task_start', self.handle_task_start)
        global_event_publisher.subscribe('plan_start', self.handle_plan_start)
        global_event_publisher.subscribe('plan_final', self.handle_plan_final)
        global_event_publisher.subscribe('step_end', self.handle_step_end)
        global_event_publisher.subscribe('task_failed', self.handle_task_failed)
        global_event_publisher.subscribe('task_end', self.handle_task_end)

        self.logger.info("会话存储订阅者已初始化，开始监听事件")

    def _unsubscribe_from_events(self):
        """取消订阅事件"""
        global_event_publisher.unsubscribe('plan_start', self.handle_plan_start)
        global_event_publisher.unsubscribe('plan_final', self.handle_plan_final)
        global_event_publisher.unsubscribe('step_end', self.handle_step_end)
        global_event_publisher.unsubscribe('task_end', self.handle_task_end)
        global_event_publisher.unsubscribe('task_failed', self.handle_task_failed)

        self.logger.info("会话存储订阅者已停止监听事件")



    def handle_task_start(self, session_id: str, execution_id: str, **kwargs):
        """处理任务处理开始事件

        Args:
            session_id: 会话 ID
            execution_id: 执行 ID
            **kwargs: 其他参数
        """
        task_id = kwargs.get('task_id')
        user_input = kwargs.get('user_input', '')
        task_level = kwargs.get('task_level', 'none')
        self.logger.debug(f"收到 task_start 事件：session={session_id}, task_id={task_id}")
        if not task_id:
            self.logger.warning(f"处理 task_start 事件时缺少 task_id: {session_id}, kwargs={kwargs}")
            return
            
        if self.sessionManage:
            session_info = self.sessionManage.get_session_info(session_id)
            if not session_info:
                self.logger.debug(f"会话不存在，创建新会话：session={session_id}")
                self.sessionManage.create_session_by_id(session_id=session_id)
            
            existing_task = self.sessionManage.get_task(session_id, task_id)
            if existing_task:
                self.logger.debug(f"任务已存在，跳过创建：session={session_id}, task={task_id}")
                return
            
            self.sessionManage.create_task(
                session_id=session_id,
                task_id=task_id,
                task_type='task',
                user_input=user_input,
                task_level=task_level
            )
        else:
            self.logger.warning("sessionManage 未初始化")

    def handle_plan_start(self, session_id: str, execution_id: str, **kwargs):
        """处理任务规划开始事件

        Args:
            session_id: 会话 ID
            execution_id: 执行 ID
            **kwargs: 其他参数
        """
        task_id = kwargs.get('task_id')
        task_input = kwargs.get('task_info', {}).get('description', '')
        task_level = kwargs.get('task_level', 'none')
        self.logger.debug(f"收到 plan_start 事件：session={session_id}, task_id={task_id}")
        if not task_id:
            self.logger.warning(f"处理 plan_start 事件时缺少 task_id: {session_id}, kwargs={kwargs}")
            return
            
        if self.sessionManage:
            # 检查会话是否存在，不存在则创建
            session_info = self.sessionManage.get_session_info(session_id)
            if not session_info:
                self.sessionManage.create_session_by_id(session_id=session_id)
            else:
                self.logger.debug(f"会话已存在：session={session_id}")
            
            # 检查任务是否已存在，避免重复创建
            existing_task = self.sessionManage.get_task(session_id, task_id)
            if existing_task:
                self.logger.debug(f"任务已存在，跳过创建：session={session_id}, task={task_id}")
                return
            
            # 创建任务
            self.sessionManage.create_task(
                session_id=session_id,
                task_id=task_id,
                task_type='plan',
                user_input=task_input,
                task_level=task_level
            )
        else:
            self.logger.warning("sessionManage 未初始化")
    def handle_task_failed(self, session_id: str, execution_id: str, **kwargs):
        task_id = kwargs.get('task_id')
        self.logger.debug(f"收到 task_failed 事件：session={session_id}, task_id={task_id}")
        if not task_id:
            self.logger.warning(f"处理 task_failed 事件时缺少 task_id: {session_id}, kwargs={kwargs}")
            return
            
        if self.sessionManage:
            self.sessionManage.set_task_result(
                session_id=session_id,
                task_id=task_id,
                result=kwargs.get('error', ''),
                user_input=kwargs.get('task_input', ''),
                status='failed'
            )
        else:
            self.logger.warning("sessionManage 未初始化")

    def handle_plan_final(self, session_id: str, execution_id: str, plan: list, **kwargs):
        """处理任务规划完成事件

        Args:
            session_id: 会话ID
            execution_id: 执行ID
            plan: 任务计划（包含每个步骤）
            **kwargs: 其他参数
        """
        task_id = kwargs.get('task_id')
        self.logger.debug(f"当前任务ID：{task_id}")
        if not task_id:
            self.logger.warning(f"处理 plan_final 事件时缺少 task_id: {session_id}")
            return
            
        if self.sessionManage:
            self.sessionManage.save_plan(
                session_id=session_id,
                task_id=task_id,
                plan=json.dumps(plan)
            )


    def handle_step_end(self, session_id: str, execution_id: str, step_index: int, result: Any, **kwargs):
        """处理步骤执行结束事件

        Args:
            session_id: 会话 ID
            execution_id: 执行 ID
            step_index: 步骤索引
            result: 步骤执行结果（字符串或字典格式）
            **kwargs: 其他参数
        """
        task_id = kwargs.get('task_id')
        self.logger.debug(f"收到 step_end 事件：session={session_id}, task_id={task_id}, step={step_index}")
        if not task_id:
            self.logger.warning(f"处理 step_end 事件时缺少 task_id: {session_id}, kwargs={kwargs}")
            return
        
        # 如果 result 是字典，转换为 JSON 字符串
        if isinstance(result, dict):
            result = json.dumps(result, ensure_ascii=False)
            
        if self.sessionManage:
            self.sessionManage.add_step(
                session_id=session_id,
                task_id=task_id,
                step_index=step_index,
                result=result,
                status=kwargs.get('status', ''),
                thought=kwargs.get('thought', ''),
                action=kwargs.get('action', ''),
                action_input=kwargs.get('action_input', ''),
                description=kwargs.get('description', '')
            )
        else:
            self.logger.warning("sessionManage 未初始化")

    def handle_task_end(self, session_id: str, execution_id: str, result: Any, **kwargs):
        """处理任务处理最终结果输出事件

        Args:
            session_id: 会话 ID
            execution_id: 执行 ID
            result: 最终结果（字符串或字典格式）
            **kwargs: 其他参数
        """
        task_id = kwargs.get('task_id')
        self.logger.debug(f"收到 task_end 事件：session={session_id}, task_id={task_id}")
        if not task_id:
            self.logger.warning(f"处理 task_end 事件时缺少 task_id: {session_id}, kwargs={kwargs}")
            return
        
        if isinstance(result, dict):
            result = json.dumps(result, ensure_ascii=False)
            
        if self.sessionManage:
            self.sessionManage.set_task_result(
                session_id=session_id,
                task_id=task_id,
                result=result,
                user_input=kwargs.get('task_input', ''),
                status='completed'
            )
            
            input_tokens = kwargs.get('input_tokens', 0)
            output_tokens = kwargs.get('output_tokens', 0)
            if input_tokens or output_tokens:
                self.sessionManage.update_task_tokens(task_id, input_tokens, output_tokens)
                self.sessionManage.update_session_tokens(session_id, input_tokens, output_tokens)
                self.logger.debug(f"任务 Token 总计：input={input_tokens}, output={output_tokens}")
            
        else:
            self.logger.warning("sessionManage 未初始化")

    def __del__(self):
        """析构函数，清理订阅"""
        try:
            self._unsubscribe_from_events()
        except Exception:
            pass
