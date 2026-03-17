#!/usr/bin/env python3
"""子代理调度器 - 复用 SessionManager 多会话架构"""

import asyncio
import uuid
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
import time

from lingxi.core.event.publisher import EventPublisher

logger = logging.getLogger(__name__)


@dataclass
class SubAgentTask:
    """子代理任务"""
    id: str
    task: str
    session_id: str
    status: str  # pending, running, completed, failed, timeout
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    duration: float = 0.0
    workspace_path: Optional[str] = None
    progress: int = 0  # 进度百分比
    current_step: str = ""  # 当前步骤
    total_steps: int = 0  # 总步骤数
    completed_steps: int = 0  # 已完成步骤数
    logs: List[str] = field(default_factory=list)  # 日志
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "id": self.id,
            "task": self.task,
            "session_id": self.session_id,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "created_at": datetime.fromtimestamp(self.created_at).isoformat(),
            "started_at": datetime.fromtimestamp(self.started_at).isoformat() if self.started_at else None,
            "ended_at": datetime.fromtimestamp(self.ended_at).isoformat() if self.ended_at else None,
            "duration": f"{self.duration:.2f}s",
            "workspace_path": self.workspace_path,
            "progress": self.progress,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "logs": self.logs[-5:]  # 最近 5 条日志
        }


class SubAgentScheduler:
    """子代理调度器 - 复用 SessionManager"""
    
    def __init__(
        self,
        session_manager,
        skill_caller,
        config: Dict[str, Any]
    ):
        """
        初始化子代理调度器
        
        Args:
            session_manager: SessionManager 实例（复用现有）
            skill_caller: SkillCaller 实例（复用现有）
            config: 系统配置
        """
        self.session_manager = session_manager
        self.skill_caller = skill_caller
        self.config = config
        self.active_tasks: Dict[str, SubAgentTask] = {}
        self.max_concurrent = config.get("max_concurrent", 5)
        self.default_timeout = config.get("default_timeout", 300)
        
        # 复用现有事件发布器
        self.event_publisher = EventPublisher()
        logger.debug("事件发布器已初始化")
        
        logger.info(f"子代理调度器已初始化，最大并发：{self.max_concurrent}")
    
    async def spawn(
        self,
        task: str,
        workspace_path: str = None,
        timeout: int = None,
        context: Dict[str, Any] = None,
        callback: Callable = None
    ) -> str:
        """
        Spawn 子代理（创建独立会话执行任务）
        
        Args:
            task: 任务描述
            workspace_path: 工作目录（可选）
            timeout: 超时时间（秒）
            context: 额外上下文
            callback: 完成回调函数
        
        Returns:
            任务 ID（也是 session_id）
        """
        task_id = str(uuid.uuid4())
        timeout = timeout or self.default_timeout
        
        # 创建独立会话（复用现有 SessionManager）
        try:
            session = self.session_manager.create_session(
                session_id=task_id,
                workspace_path=workspace_path
            )
            logger.debug(f"创建子代理会话：{session.id}")
        except Exception as e:
            logger.error(f"创建会话失败：{e}")
            # 降级：使用任务 ID 作为 session_id，不实际创建会话
            session = type('Session', (), {'id': task_id})()
        
        # 记录任务
        sub_task = SubAgentTask(
            id=task_id,
            task=task,
            session_id=session.id,
            status="pending",
            workspace_path=workspace_path
        )
        self.active_tasks[task_id] = sub_task
        
        # 异步执行
        asyncio.create_task(
            self._execute_task(task_id, task, session, timeout, context, callback)
        )
        
        logger.info(f"子代理已 spawn: {task_id}")
        return task_id
    
    async def _execute_task(
        self,
        task_id: str,
        task: str,
        session,
        timeout: int,
        context: Dict[str, Any],
        callback: Callable
    ):
        """执行任务（复用事件机制）"""
        sub_task = self.active_tasks[task_id]
        
        try:
            # 更新状态
            sub_task.status = "running"
            sub_task.started_at = time.time()
            
            # 发布任务开始事件
            self.event_publisher.publish(
                event_type="task_start",
                task_id=task_id,
                session_id=session.id,
                task=task,
                workspace_path=sub_task.workspace_path,
                timestamp=sub_task.started_at
            )
            
            # 获取或创建引擎（复用现有）
            from lingxi.core.engine.direct import DirectEngine
            
            engine = DirectEngine(
                config=self.config
            )
            
            # 执行任务（引擎会自动发布步骤事件）
            result = await asyncio.wait_for(
                engine.execute_task(
                    task=task,
                    session_id=session.id,
                    context=context
                ),
                timeout=timeout
            )
            
            # 记录结果
            sub_task.status = "completed"
            sub_task.result = result
            sub_task.ended_at = time.time()
            sub_task.duration = sub_task.ended_at - sub_task.started_at
            
            # 发布任务完成事件
            self.event_publisher.publish(
                event_type="task_end",
                task_id=task_id,
                session_id=session.id,
                result=result,
                duration=sub_task.duration,
                timestamp=sub_task.ended_at
            )
            
            logger.info(f"子代理完成：{task_id} (耗时：{sub_task.duration:.2f}s)")
            
        except asyncio.TimeoutError:
            sub_task.status = "timeout"
            sub_task.result = "任务超时"
            sub_task.ended_at = time.time()
            sub_task.duration = sub_task.ended_at - sub_task.started_at
            
            # 发布超时事件
            self.event_publisher.publish(
                event_type="task_timeout",
                task_id=task_id,
                session_id=session.id,
                timeout=timeout,
                timestamp=sub_task.ended_at
            )
            
            logger.warning(f"子代理超时：{task_id}")
        
        except Exception as e:
            sub_task.status = "failed"
            sub_task.error = str(e)
            sub_task.result = None
            sub_task.ended_at = time.time()
            sub_task.duration = sub_task.ended_at - sub_task.started_at
            
            # 发布失败事件
            self.event_publisher.publish(
                event_type="task_failed",
                task_id=task_id,
                session_id=session.id,
                error=str(e),
                timestamp=sub_task.ended_at
            )
            
            logger.error(f"子代理失败：{task_id} - {e}")
        
        finally:
            # 回调
            if callback:
                try:
                    callback(sub_task)
                except Exception as e:
                    logger.error(f"回调执行失败：{e}")
    
    def list_tasks(self, status: str = None) -> List[SubAgentTask]:
        """
        列出所有任务
        
        Args:
            status: 按状态过滤（可选）
        
        Returns:
            任务列表
        """
        tasks = list(self.active_tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks
    
    def get_task(self, task_id: str) -> Optional[SubAgentTask]:
        """获取任务状态"""
        return self.active_tasks.get(task_id)
    
    def get_task_status(self, task_id: str) -> Optional[str]:
        """获取任务状态（简化版）"""
        task = self.active_tasks.get(task_id)
        return task.status if task else None
    
    def get_task_progress(self, task_id: str) -> dict:
        """
        获取任务进度（从步骤管理器）
        
        Args:
            task_id: 任务 ID
        
        Returns:
            进度信息字典
        """
        task = self.get_task(task_id)
        if not task:
            return None
        
        # 从 SessionManager 的 StepManager 获取步骤
        steps = []
        if hasattr(self.session_manager, 'step_manager') and hasattr(self.session_manager.step_manager, 'get_steps'):
            try:
                steps = self.session_manager.step_manager.get_steps(task_id)
            except Exception as e:
                logger.debug(f"获取步骤失败：{e}")
        
        # 分析步骤
        total_steps = len(steps)
        completed_steps = len([s for s in steps if s.get("status") == "completed"])
        
        # 获取当前步骤
        current_step = ""
        if steps:
            last_step = steps[-1]
            current_step = last_step.get("description", last_step.get("step_type", ""))
        
        # 更新任务进度
        if total_steps > 0:
            task.progress = int((completed_steps / total_steps) * 100)
            task.current_step = current_step
            task.total_steps = total_steps
            task.completed_steps = completed_steps
        
        # 生成日志
        logs = []
        for step in steps[-5:]:
            step_desc = step.get("description", step.get("step_type", ""))
            step_status = step.get("status", "")
            logs.append(f"{step_status}: {step_desc}")
        
        return {
            "task_id": task_id,
            "status": task.status,
            "progress": task.progress,
            "current_step": current_step,
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "logs": logs
        }
    
    def _subscribe_to_events(self):
        """订阅子代理事件（用于实时监控）"""
        # 这里可以添加事件订阅逻辑
        # 目前通过 get_task_progress 轮询即可
        pass
    
    async def wait_for_task(
        self,
        task_id: str,
        timeout: int = None
    ) -> Optional[SubAgentTask]:
        """
        等待任务完成
        
        Args:
            task_id: 任务 ID
            timeout: 等待超时时间
        
        Returns:
            任务结果
        """
        timeout = timeout or self.default_timeout
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            task = self.get_task(task_id)
            if task and task.status in ["completed", "failed", "timeout"]:
                return task
            await asyncio.sleep(0.5)
        
        return None
    
    async def parallel_execute(
        self,
        tasks: List[str],
        workspace_path: str = None,
        timeout: int = None,
        context: Dict[str, Any] = None
    ) -> List[SubAgentTask]:
        """
        并行执行多个任务
        
        Args:
            tasks: 任务描述列表
            workspace_path: 工作目录
            timeout: 超时时间
            context: 共享上下文
        
        Returns:
            任务结果列表
        """
        # 批量创建任务
        task_ids = []
        for task_desc in tasks:
            task_id = await self.spawn(
                task=task_desc,
                workspace_path=workspace_path,
                timeout=timeout,
                context=context
            )
            task_ids.append(task_id)
        
        logger.info(f"并行执行 {len(tasks)} 个子任务：{task_ids}")
        
        # 等待所有完成
        results = []
        for task_id in task_ids:
            result = await self.wait_for_task(task_id, timeout)
            results.append(result)
        
        return results
    
    def cleanup_completed(self, max_age: int = 3600):
        """
        清理已完成的任务
        
        Args:
            max_age: 保留时间（秒），默认 1 小时
        """
        current_time = time.time()
        to_remove = []
        
        for task_id, task in self.active_tasks.items():
            if task.status in ["completed", "failed", "timeout"]:
                if task.ended_at and (current_time - task.ended_at) > max_age:
                    to_remove.append(task_id)
        
        for task_id in to_remove:
            del self.active_tasks[task_id]
        
        if to_remove:
            logger.info(f"清理了 {len(to_remove)} 个已完成的任务")
        
        return len(to_remove)
