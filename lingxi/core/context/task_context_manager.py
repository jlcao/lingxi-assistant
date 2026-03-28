import asyncio
import logging
from typing import Dict, List, Optional
from lingxi.core.context.task_context import TaskContext

logger = logging.getLogger(__name__)


class TaskContextManager:
    """任务上下文管理器 - 管理正在执行的任务"""

    _instance = None

    def __new__(cls):
        """单例模式：确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # 防止重复初始化
        if hasattr(self, '_initialized'):
            return

        # 按 taskId 存储 TaskContext
        self.tasks_by_id: Dict[str, TaskContext] = {}
        # 按 sessionId 存储 taskId 列表，用于快速查找
        self.tasks_by_session: Dict[str, List[str]] = {}
        # 并发安全锁
        self.lock = asyncio.Lock()
        self._initialized = True
        logger.debug("初始化 TaskContextManager")

    async def register_task(self, task_context: TaskContext) -> str:
        """注册新任务

        Args:
            task_context: 任务上下文

        Returns:
            task_id
        """
        task_id = task_context.task_id
        session_id = task_context.session_id

        async with self.lock:
            self.tasks_by_id[task_id] = task_context
            if session_id not in self.tasks_by_session:
                self.tasks_by_session[session_id] = []
            self.tasks_by_session[session_id].append(task_id)

        logger.debug(f"注册任务: task_id={task_id}, session_id={session_id}")
        return task_id

    async def unregister_task(self, task_id: str):
        """注销任务

        Args:
            task_id: 任务 ID
        """
        async with self.lock:
            if task_id not in self.tasks_by_id:
                return

            task_context = self.tasks_by_id[task_id]
            session_id = task_context.session_id

            del self.tasks_by_id[task_id]

            if session_id in self.tasks_by_session:
                self.tasks_by_session[session_id].remove(task_id)
                if not self.tasks_by_session[session_id]:
                    del self.tasks_by_session[session_id]

        logger.debug(f"注销任务: task_id={task_id}")

    async def get_task(self, task_id: str) -> Optional[TaskContext]:
        """获取任务上下文

        Args:
            task_id: 任务 ID

        Returns:
            TaskContext 或 None
        """
        async with self.lock:
            return self.tasks_by_id.get(task_id)

    async def get_session_tasks(self, session_id: str) -> List[TaskContext]:
        """获取会话的所有任务

        Args:
            session_id: 会话 ID

        Returns:
            任务上下文列表
        """
        async with self.lock:
            task_ids = self.tasks_by_session.get(session_id, [])
            return [self.tasks_by_id[task_id] for task_id in task_ids if task_id in self.tasks_by_id]

    async def stop_task(self, task_id: str) -> bool:
        """终止任务

        Args:
            task_id: 任务 ID

        Returns:
            是否成功终止
        """
        task_context = await self.get_task(task_id)
        if not task_context:
            logger.warning(f"任务不存在: task_id={task_id}")
            return False

        # 设置终止标志
        task_context.stop()
        logger.info(f"终止任务: task_id={task_id}")
        return True

    async def stop_session_tasks(self, session_id: str):
        """终止会话的所有任务

        Args:
            session_id: 会话 ID
        """
        task_contexts = await self.get_session_tasks(session_id)
        for task_context in task_contexts:
            task_context.stop()
        logger.info(f"终止会话所有任务: session_id={session_id}, count={len(task_contexts)}")

    async def cleanup_expired_tasks(self):
        """清理过期任务（可定期调用）"""
        pass
