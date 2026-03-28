import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
from lingxi.core.context.task_context import TaskContext
from lingxi.core.event import global_event_publisher
from lingxi.web import websocket


class WebSocketSubscriber:
    """WebSocket 事件订阅者"""
    _instance = None  # 单例实例

    def __new__(cls, websocket_manager: websocket.WebSocketManager = None):
        """单例模式：确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, websocket_manager: websocket.WebSocketManager = None):
        """初始化 WebSocket 订阅者

        Args:
            websocket_manager: WebSocket 管理器实例（可选）
        """
        self.websocket_manager = websocket_manager 
        self.logger = logging.getLogger(__name__)
        
        if websocket_manager:
            self._subscribe_to_events()
        else:
            self.logger.debug("WebSocket 管理器未提供，跳过事件订阅")
        self._initialized = True

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
        global_event_publisher.subscribe('task_stopped', self.handle_task_end)

        self.logger.info("WebSocket 订阅者已初始化，开始监听事件")

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
        global_event_publisher.unsubscribe('task_stopped', self.handle_task_end)

        self.logger.info("WebSocket订阅者已停止监听事件")

    def _convert_datetime_to_str(self, data):
        """转换数据中的 datetime 对象为字符串

        Args:
            data: 数据对象

        Returns:
            转换后的数据
        """
        if isinstance(data, dict):
            return {key: self._convert_datetime_to_str(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._convert_datetime_to_str(item) for item in data]
        elif hasattr(data, '__dict__'):
            return self._convert_datetime_to_str(data.__dict__)
        elif isinstance(data, datetime):
            return data.isoformat()
        else:
            return data

    async def _safe_send_event(self, session_id: str, event_type: str, execution_id: str,task_id: str,step_index: int, data: dict):
        """安全发送事件

        Args:
            session_id: 会话ID
            event_type: 事件类型
            execution_id: 执行ID
            data: 事件数据
        """
        try:
            if self.websocket_manager:
                # 转换数据中的 datetime 对象为字符串
                converted_data = self._convert_datetime_to_str(data)
                await self.websocket_manager.send_event(
                    session_id=session_id,
                    event_type=event_type,
                    execution_id=execution_id,
                    task_id=task_id,
                    step_index=step_index,
                    data=converted_data
                )
        except Exception as e:
            self.logger.debug(f"发送事件失败: {e}")

    def handle_think_start(self, context: TaskContext, step_index: int, **kwargs):
        """处理思考开始事件

        Args:
            context: 任务上下文
            **kwargs: 其他参数
        """
        step_info = None
        task_info = None
        if step_index == 0:
            task_info ={
                "taskId": context.task_info.task_id,
                "userInput": context.task_info.user_input,
                "plan": context.task_info.plan,
                "result": context.task_info.result,
                "taskType": context.task_info.task_type,
                "status": context.task_info.status,
                "errorInfo": context.task_info.error_info,
                "inputTokens": context.task_info.input_tokens,
                "outputTokens": context.task_info.output_tokens,
            }
        else:
            step_info ={
                "stepIndex": step_index,
                "stepType": context.steps[-1].step_type,
                "status": context.steps[-1].status,
                "thought": context.steps[-1].thought,
                "result": context.steps[-1].result,
                "skillCall": context.steps[-1].skill_call,
                "description": context.steps[-1].description,
                "resultDescription": context.steps[-1].result_description,
            }      
        asyncio.create_task(self._safe_send_event(
            session_id=context.session_id,
            event_type='think_start',
            execution_id=context.execution_id,
            task_id=context.task_id,
            step_index=step_index,
            data={**kwargs,"taskInfo":task_info or {},"stepInfo":step_info or {}}
        ))

    def handle_think_stream(self, context: TaskContext, step_index: int, content: str, **kwargs):
        """处理思考块流式渲染事件

        Args:
            context: 任务上下文
            content: 思考内容
            **kwargs: 其他参数
        """
        asyncio.create_task(self._safe_send_event(
            session_id=context.session_id,
            event_type='think_stream',
            execution_id=context.execution_id,
            task_id=context.task_id,
            step_index=step_index,
            data={"content": content, **kwargs}
        ))

    def handle_think_final(self, context: TaskContext, content: str, **kwargs):
        """处理思考结束事件

        Args:
            context: 任务上下文
            content: 思考内容
            **kwargs: 其他参数
        """
        step_index = kwargs.get("step_index", 0)
        task_info = None
        step_info = None

        if step_index == 0:
            task_info ={
                "taskId": context.task_info.task_id,
                "userInput": context.task_info.user_input,
                "plan": context.task_info.plan,
                "result": context.task_info.result,
                "taskType": context.task_info.task_type,
                "status": context.task_info.status,
                "errorInfo": context.task_info.error_info,
                "inputTokens": context.task_info.input_tokens,
                "outputTokens": context.task_info.output_tokens,
            }
        else:
            step_info ={
                "stepIndex": step_index,
                "stepType": context.steps[-1].step_type,
                "status": context.steps[-1].status,
                "thought": context.steps[-1].thought,
                "result": context.steps[-1].result,
                "skillCall": context.steps[-1].skill_call,
                "description": context.steps[-1].description,
                "resultDescription": context.steps[-1].result_description,
            }    
            

        asyncio.create_task(self._safe_send_event(
            session_id=context.session_id,
            event_type='think_final',
            execution_id=context.execution_id,
            task_id=context.task_id,
            step_index=step_index,
            data={"content": content, **kwargs,"taskInfo":task_info or {},"stepInfo":step_info or {}}
        ))

    def handle_plan_start(self, context: TaskContext, **kwargs):
        """处理任务规划开始事件

        Args:
            context: 任务上下文
            **kwargs: 其他参数
        """
        asyncio.create_task(self._safe_send_event(
            session_id=context.session_id,
            event_type='plan_start',
            execution_id=context.execution_id,
            task_id=context.task_id,
            step_index=0,
            data={**kwargs,"title":context.description or ""}
        ))

    def handle_plan_final(self, context: TaskContext, plan: list, **kwargs):
        """处理任务规划完成事件

        Args:
            context: 任务上下文
            plan: 任务计划（包含每个步骤）
            **kwargs: 其他参数
        """
        asyncio.create_task(self._safe_send_event(
            session_id=context.session_id,
            event_type='plan_final',
            execution_id=context.execution_id,
            task_id=context.task_id,
            step_index=0,
            data={"plan": plan, **kwargs}
        ))

    def handle_step_start(self, context: TaskContext, step_index: int, **kwargs):
        """处理步骤开始事件

        Args:
            context: 任务上下文
            step_index: 步骤索引
            **kwargs: 其他参数
        """
        step_info ={
            "stepIndex": step_index,
            "stepType": context.steps[-1].step_type,
            "status": context.steps[-1].status,
            "thought": context.steps[-1].thought,
            "result": context.steps[-1].result,
            "skillCall": context.steps[-1].skill_call,
            "description": context.steps[-1].description,
            "resultDescription": context.steps[-1].result_description,
        }
        asyncio.create_task(self._safe_send_event(
            session_id=context.session_id,
            event_type='step_start',
            execution_id=context.execution_id,
            task_id=context.task_id,
            step_index=step_index,
            data={"stepInfo": step_info, **kwargs}
        ))

    def handle_step_end(self, context: TaskContext, step_index: int, **kwargs):
        """处理步骤执行结束事件

        Args:
            context: 任务上下文
            step_index: 步骤索引
            **kwargs: 其他参数

             session_id: str
    step_id: str
    task_id: str  # 任务ID
    step_index: int = 0  # 步骤索引
    step_type: str = "thinking"  # call 或 finish
    description: str = ""  # 步骤描述
    status: str = "completed"  # 步骤状态 completed 或 thinking 或 failed
    thought: str = ""  # 思考内容 
    result: str = ""  # 步骤结果
    skill_call: str = ""  # 调用的技能
    result_description: str = ""  # 步骤结果描述
    created_at: datetime = datetime.now()  # 创建时间
    updated_at: datetime = datetime.now()  # 更新时间
        """
        step_info ={
            "stepIndex": step_index,
            "stepType": context.steps[-1].step_type,
            "status": context.steps[-1].status,
            "thought": context.steps[-1].thought,
            "result": context.steps[-1].result,
            "skillCall": context.steps[-1].skill_call,
            "description": context.steps[-1].description,
            "resultDescription": context.steps[-1].result_description,
        }
        asyncio.create_task(self._safe_send_event(
            session_id=context.session_id,
            event_type='step_end',
            execution_id=context.execution_id,
            task_id=context.task_id,
            step_index=step_index,
            data={"stepInfo": step_info, **kwargs}
        ))

    def handle_task_start(self, context: TaskContext, **kwargs):
        """处理任务处理开始事件

        Args:
            context: 任务上下文
            **kwargs: 其他参数

         task_id: str
    session_id: str
    task_type: str = "simple"  # 任务类型 simple 或 complex
    plan: str = "[]"  # 计划步骤
    user_input: str = ""  # 用户输入
    result: str = ""  # 任务结果
    status: str = "running" #执行中 running ,完成 completed ,手动中断 interrupted
    current_step_idx: int = 0  # 当前步骤索引
    replan_count: int = 0  # 重新计划次数
    error_info: str = ""  # 错误信息
    input_tokens: int = 0  # 输入token数
    output_tokens: int = 0  # 输出token数
    steps: List[Step] = field(default_factory=list)  # 任务步骤列表
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
        """
        task_info ={
            "taskId": context.task_info.task_id,
            "userInput": context.task_info.user_input,
            "plan": context.task_info.plan,
            "result": context.task_info.result,
            "taskType": context.task_info.task_type,
            "status": context.task_info.status,
            "errorInfo": context.task_info.error_info,
            "inputTokens": context.task_info.input_tokens,
            "outputTokens": context.task_info.output_tokens,
        }
        asyncio.create_task(self._safe_send_event(
            session_id=context.session_id,
            event_type='task_start',
            execution_id=context.execution_id,
            task_id=context.task_id,
            step_index=0,
            data={**kwargs,"userInput": context.user_input,"taskInfo": task_info}
        ))

    def handle_task_end(self, context: TaskContext, result: str, **kwargs):
        """处理任务处理最终结果输出事件

        Args:
            context: 任务上下文
            result: 最终结果
            **kwargs: 其他参数
        """
        task_info ={
            "taskId": context.task_info.task_id,
            "userInput": context.task_info.user_input,
            "plan": context.task_info.plan,
            "result": context.task_info.result,
            "taskType": context.task_info.task_type,
            "status": context.task_info.status,
            "errorInfo": context.task_info.error_info,
            "inputTokens": context.task_info.input_tokens,
            "outputTokens": context.task_info.output_tokens,
        }
        asyncio.create_task(self._safe_send_event(
            session_id=context.session_id,
            event_type='task_end',
            execution_id=context.execution_id,
            task_id=context.task_id,
            step_index=0,
            data={"result": result, **kwargs,"taskInfo": task_info}
        ))

    def __del__(self):
        """析构函数，清理订阅"""
        try:
            self._unsubscribe_from_events()
        except Exception:
            pass
