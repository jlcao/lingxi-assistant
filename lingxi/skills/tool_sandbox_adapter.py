#!/usr/bin/env python3
"""工具沙盒适配器 - 将现有工具与沙盒集成

提供适配器，让现有工具（ToolBase 系列）可以在分级沙盒中运行。
"""

import logging
from typing import Dict, Any, Optional, Callable
from functools import partial

from lingxi.core.utils.Tool import Tool

from .sandbox import SandboxManager, TrustLevel
from .execution_context import ExecutionContext
from .skill_response import ToolResponse
from .executor_scheduler import ExecutorScheduler, ExecutorType, SkillPriority


class ToolSandboxAdapter:
    """工具沙盒适配器

    将现有 ToolBase 系列工具包装为可在沙盒中运行的函数。
    """

    def __init__(
        self,
        sandbox_manager: Optional[SandboxManager] = None,
        executor_scheduler: Optional[ExecutorScheduler] = None,
        default_trust_level: TrustLevel = TrustLevel.L1
    ):
        """初始化适配器

        Args:
            sandbox_manager: 沙盒管理器（如果为 None 则创建新的）
            executor_scheduler: 执行调度器（如果为 None 则创建新的）
            default_trust_level: 默认信任等级
        """
        self.logger = logging.getLogger(__name__)
        self.sandbox_manager = sandbox_manager or SandboxManager()
        self.executor_scheduler = executor_scheduler or ExecutorScheduler()
        self.default_trust_level = default_trust_level
        self._tool_trust_levels: Dict[str, TrustLevel] = {}

        self.logger.info("工具沙盒适配器已初始化")

    def set_tool_trust_level(self, tool_name: str, trust_level: TrustLevel):
        """设置特定工具的信任等级

        Args:
            tool_name: 工具名称
            trust_level: 信任等级
        """
        self._tool_trust_levels[tool_name] = trust_level
        self.logger.debug(f"工具 {tool_name} 信任等级设置为 {trust_level}")

    def get_tool_trust_level(self, tool_name: str) -> TrustLevel:
        """获取工具的信任等级

        Args:
            tool_name: 工具名称

        Returns:
            信任等级
        """
        return self._tool_trust_levels.get(tool_name, self.default_trust_level)

    def wrap_tool_execute(
        self,
        tool_execute: Callable,
        tool_name: str,
        context: Optional[ExecutionContext] = None,
        trust_level: Optional[TrustLevel] = None
    ) -> Callable:
        """包装工具的 execute 方法为沙盒可执行函数

        Args:
            tool_execute: 工具的 execute 方法
            tool_name: 工具名称
            context: 执行上下文
            trust_level: 信任等级（如果为 None 则使用工具的默认值）

        Returns:
            包装后的可执行函数
        """
        trust_level = trust_level or self.get_tool_trust_level(tool_name)
        context = context or ExecutionContext()
        context = context.with_skill(tool_name, trust_level)

        def wrapped(parameters: Dict[str, Any]) -> ToolResponse:
            """包装后的执行函数

            Args:
                parameters: 工具参数

            Returns:
                SkillResponse 实例
            """
            try:
                tool_result = tool_execute(parameters)
                if isinstance(tool_result, ToolResponse):
                    return tool_result
                return ToolResponse.success(
                        data=tool_result,
                        skill_id=tool_name,
                        trace_id=context.trace_id
                )
            except Exception as e:
                self.logger.error(f"工具 {tool_name} 执行异常: {str(e)}")
                return ToolResponse.error(
                    message=f"工具执行异常: {str(e)}",
                    skill_id=tool_name,
                    trace_id=context.trace_id
                )
        return wrapped

    def execute_tool_in_sandbox(
        self,
        tool:Tool,
        parameters: Dict[str, Any],
        tool_name: str,
        context: Optional[ExecutionContext] = None,
        trust_level: Optional[TrustLevel] = None,
        timeout: Optional[float] = None
    ) -> ToolResponse:
        """在沙盒中执行工具

        Args:
            tool_execute: 工具的 execute 方法
            parameters: 工具参数
            tool_name: 工具名称
            context: 执行上下文
            trust_level: 信任等级
            timeout: 超时时间（秒）

        Returns:
            SkillResponse 实例
        """

        tool_execute = tool.tools[tool_name].execute
        wrapped_func = self.wrap_tool_execute(
            tool_execute,
            tool_name,
            context,
            trust_level
        )

        trust_level = trust_level or self.get_tool_trust_level(tool_name)

        def execute_task():
            """在沙盒中执行任务"""
            return self.sandbox_manager.run(
                wrapped_func,
                parameters,
                skill_id=tool_name,
                context=context,
                trust_level=trust_level,
                timeout=timeout
            )

        # 根据信任等级选择执行器类型和优先级
        # 全部使用线程池避免 ProcessPoolExecutor 序列化嵌套函数的问题
        executor_type = ExecutorType.THREAD
        priority = SkillPriority.HIGH

        # 使用执行调度器执行任务
        future = self.executor_scheduler.submit(
            execute_task,
            skill_id=tool_name,
            context=context,
            priority=priority,
            executor_type=executor_type,
            timeout=timeout
        )

        # 等待执行结果
        result = future.result()
        return result

    def shutdown(self, wait: bool = True):
        """关闭沙盒和执行调度器"""
        self.sandbox_manager.shutdown(wait=wait)
        self.executor_scheduler.shutdown(wait=wait)
        self.logger.info("工具沙盒适配器已关闭")


def adapt_tool_manager(
    tool_manager,
    sandbox_manager: Optional[SandboxManager] = None,
    executor_scheduler: Optional[ExecutorScheduler] = None,
    default_trust_level: TrustLevel = TrustLevel.L1
) -> ToolSandboxAdapter:
    """适配现有的 Tool 管理器

    Args:
        tool_manager: 现有的 Tool 管理器实例
        sandbox_manager: 沙盒管理器
        executor_scheduler: 执行调度器
        default_trust_level: 默认信任等级

    Returns:
        ToolSandboxAdapter 实例
    """
    adapter = ToolSandboxAdapter(sandbox_manager, executor_scheduler, default_trust_level)

    for tool_name in tool_manager.tools:
        if tool_name in ["file", "command"]:
            adapter.set_tool_trust_level(tool_name, TrustLevel.L2)
        else:
            adapter.set_tool_trust_level(tool_name, TrustLevel.L1)

    return adapter

