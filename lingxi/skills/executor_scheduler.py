#!/usr/bin/env python3
"""执行调度器 - 管理技能执行的线程池和进程池

根据设计文档要求：
- 系统技能池（线程池，高优）
- 第三方池（进程池，低优）
- L2 隔离池（独立 venv 进程）
- 统一异常转译
"""

import logging
import asyncio
import traceback
import sys
from typing import Any, Dict, Optional, Callable, Union
from concurrent.futures import (
    ThreadPoolExecutor,
    ProcessPoolExecutor,
    Future,
    TimeoutError
)
from dataclasses import dataclass, field
from enum import Enum

from .skill_response import SkillResponse, ResponseCode
from .execution_context import ExecutionContext, TrustLevel


class ExecutorType(str, Enum):
    """执行器类型"""
    THREAD = "thread"
    PROCESS = "process"


class SkillPriority(str, Enum):
    """技能优先级"""
    HIGH = "high"
    LOW = "low"


@dataclass
class ExecutionMetrics:
    """执行指标"""
    total_calls: int = 0
    success_count: int = 0
    failure_count: int = 0
    timeout_count: int = 0
    total_cost_ms: float = 0.0
    avg_cost_ms: float = 0.0


class ExceptionTranslator:
    """异常转译器 - 不暴露原生堆栈"""

    _logger = logging.getLogger(__name__)

    @classmethod
    def translate(cls, exc: Exception, skill_id: Optional[str] = None) -> str:
        """转译异常为友好消息

        Args:
            exc: 原始异常
            skill_id: 技能ID

        Returns:
            友好的错误消息
        """
        cls._logger.error(f"技能执行异常: {skill_id or 'unknown'}", exc_info=exc)

        if isinstance(exc, TimeoutError):
            return "技能执行超时，请稍后重试"
        elif isinstance(exc, MemoryError):
            return "内存不足，请稍后重试"
        elif isinstance(exc, (IOError, OSError)):
            return "文件操作失败，请检查文件权限或路径"
        elif isinstance(exc, ImportError):
            return "技能依赖缺失，请联系管理员"
        elif isinstance(exc, SyntaxError):
            return "技能代码语法错误，请联系管理员"
        else:
            return f"技能执行失败，请稍后重试"

    @classmethod
    def to_response(
        cls,
        exc: Exception,
        skill_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> SkillResponse:
        """转译异常为 SkillResponse

        Args:
            exc: 原始异常
            skill_id: 技能ID
            trace_id: 追踪ID

        Returns:
            SkillResponse 实例
        """
        message = cls.translate(exc, skill_id)
        return SkillResponse.error(
            message=message,
            code=ResponseCode.INTERNAL_ERROR,
            skill_id=skill_id,
            trace_id=trace_id
        )


class ExecutorScheduler:
    """执行调度器"""

    _instance = None
    _initialized = False

    def __new__(cls, config: Optional[Dict[str, Any]] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        if self._initialized:
            return

        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        executor_config = self.config.get("executor", {})

        self._thread_pool_high = ThreadPoolExecutor(
            max_workers=executor_config.get("thread_pool_high_workers", 10),
            thread_name_prefix="skill-exec-high"
        )

        self._thread_pool_low = ThreadPoolExecutor(
            max_workers=executor_config.get("thread_pool_low_workers", 5),
            thread_name_prefix="skill-exec-low"
        )

        self._process_pool = ProcessPoolExecutor(
            max_workers=executor_config.get("process_pool_workers", 4)
        )

        self._metrics: Dict[str, ExecutionMetrics] = {}
        self._global_metrics = ExecutionMetrics()

        self._initialized = True
        self.logger.info("执行调度器已初始化")

    def submit(
        self,
        func: Callable,
        *args,
        skill_id: Optional[str] = None,
        context: Optional[ExecutionContext] = None,
        priority: SkillPriority = SkillPriority.HIGH,
        executor_type: ExecutorType = ExecutorType.THREAD,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Future:
        """提交任务到执行池

        Args:
            func: 要执行的函数
            *args: 位置参数
            skill_id: 技能ID
            context: 执行上下文
            priority: 优先级（HIGH/LOW）
            executor_type: 执行器类型（THREAD/PROCESS）
            timeout: 超时时间（秒）
            **kwargs: 关键字参数

        Returns:
            Future 对象
        """
        if skill_id:
            if skill_id not in self._metrics:
                self._metrics[skill_id] = ExecutionMetrics()

        def wrapped_func():
            return self._execute_wrapper(
                func,
                skill_id,
                context,
                timeout,
                *args,
                **kwargs
            )

        if executor_type == ExecutorType.PROCESS:
            return self._process_pool.submit(wrapped_func)
        else:
            if priority == SkillPriority.HIGH:
                return self._thread_pool_high.submit(wrapped_func)
            else:
                return self._thread_pool_low.submit(wrapped_func)

    def _execute_wrapper(
        self,
        func: Callable,
        skill_id: Optional[str],
        context: Optional[ExecutionContext],
        timeout: Optional[float],
        *args,
        **kwargs
    ) -> SkillResponse:
        """执行包装器 - 处理异常和指标

        Args:
            func: 要执行的函数
            skill_id: 技能ID
            context: 执行上下文
            timeout: 超时时间
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            SkillResponse 实例
        """
        import time

        trace_id = context.trace_id if context else None
        start_time = time.time()

        try:
            result = func(*args, **kwargs)

            if isinstance(result, SkillResponse):
                response = result
            else:
                response = SkillResponse.success(
                    data=result,
                    skill_id=skill_id,
                    trace_id=trace_id
                )

            cost_ms = (time.time() - start_time) * 1000
            response.meta["cost_ms"] = cost_ms

            self._record_success(skill_id, cost_ms)
            return response

        except Exception as e:
            cost_ms = (time.time() - start_time) * 1000
            self._record_failure(skill_id, cost_ms)
            return ExceptionTranslator.to_response(e, skill_id, trace_id)

    def _record_success(self, skill_id: Optional[str], cost_ms: float):
        """记录成功执行"""
        self._global_metrics.total_calls += 1
        self._global_metrics.success_count += 1
        self._global_metrics.total_cost_ms += cost_ms
        self._update_avg(self._global_metrics)

        if skill_id and skill_id in self._metrics:
            m = self._metrics[skill_id]
            m.total_calls += 1
            m.success_count += 1
            m.total_cost_ms += cost_ms
            self._update_avg(m)

    def _record_failure(self, skill_id: Optional[str], cost_ms: float):
        """记录失败执行"""
        self._global_metrics.total_calls += 1
        self._global_metrics.failure_count += 1
        self._global_metrics.total_cost_ms += cost_ms
        self._update_avg(self._global_metrics)

        if skill_id and skill_id in self._metrics:
            m = self._metrics[skill_id]
            m.total_calls += 1
            m.failure_count += 1
            m.total_cost_ms += cost_ms
            self._update_avg(m)

    def _update_avg(self, metrics: ExecutionMetrics):
        """更新平均耗时"""
        if metrics.total_calls > 0:
            metrics.avg_cost_ms = metrics.total_cost_ms / metrics.total_calls

    def get_metrics(self, skill_id: Optional[str] = None) -> Dict[str, Any]:
        """获取执行指标

        Args:
            skill_id: 技能ID（None 表示全局指标）

        Returns:
            指标字典
        """
        if skill_id:
            m = self._metrics.get(skill_id, ExecutionMetrics())
        else:
            m = self._global_metrics

        return {
            "total_calls": m.total_calls,
            "success_count": m.success_count,
            "failure_count": m.failure_count,
            "timeout_count": m.timeout_count,
            "total_cost_ms": m.total_cost_ms,
            "avg_cost_ms": m.avg_cost_ms
        }

    def get_all_metrics(self) -> Dict[str, Any]:
        """获取所有指标

        Returns:
            包含全局和各技能指标的字典
        """
        return {
            "global": self.get_metrics(),
            "skills": {
                skill_id: self.get_metrics(skill_id)
                for skill_id in self._metrics
            }
        }

    def shutdown(self, wait: bool = True):
        """关闭所有执行池

        Args:
            wait: 是否等待任务完成
        """
        self.logger.info("关闭执行调度器...")

        self._thread_pool_high.shutdown(wait=wait)
        self._thread_pool_low.shutdown(wait=wait)
        self._process_pool.shutdown(wait=wait)

        self._initialized = False
        self.logger.info("执行调度器已关闭")

    async def submit_async(
        self,
        func: Callable,
        *args,
        skill_id: Optional[str] = None,
        context: Optional[ExecutionContext] = None,
        priority: SkillPriority = SkillPriority.HIGH,
        executor_type: ExecutorType = ExecutorType.THREAD,
        timeout: Optional[float] = None,
        **kwargs
    ) -> SkillResponse:
        """异步提交并等待结果

        Args:
            func: 要执行的函数
            *args: 位置参数
            skill_id: 技能ID
            context: 执行上下文
            priority: 优先级
            executor_type: 执行器类型
            timeout: 超时时间
            **kwargs: 关键字参数

        Returns:
            SkillResponse 实例
        """
        future = self.submit(
            func,
            *args,
            skill_id=skill_id,
            context=context,
            priority=priority,
            executor_type=executor_type,
            timeout=timeout,
            **kwargs
        )

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, future.result)

