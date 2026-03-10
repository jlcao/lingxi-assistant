import logging
from typing import Dict, Optional, Any
from lingxi.core.llm.llm_client import LLMClient
from lingxi.core.engine.direct import DirectEngine
from lingxi.core.engine.plan_react import PlanReActEngine
from lingxi.core.skill_caller import SkillCaller


class ExecutionModeSelector:
    """执行模式选择器，根据任务分级选择执行模式
    
    优化后统一使用 PlanReActEngine 处理 simple/complex 任务：
    - trivial: DirectEngine（直接回答问候、简单问答）
    - simple: PlanReActEngine（智能路由，直接执行 next_action）
    - complex: PlanReActEngine（智能路由，执行多步计划）
    """
    
    _instance = None  # 单例实例
    
    def __new__(cls, config: Dict[str, Any], skill_caller: SkillCaller = None):
        """单例模式：确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config: Dict[str, Any], skill_caller: SkillCaller = None):
        """初始化执行模式选择器

        Args:
            config: 系统配置
            skill_caller: 技能调用器（用于传递给引擎）
        """
        self.config = config
        self.skill_caller = skill_caller
        self.logger = logging.getLogger(__name__)

        execution_mode_config = config.get("execution_mode", {})

        self.trivial_mode = execution_mode_config.get("trivial", {}).get("name", "direct")
        self.simple_mode = execution_mode_config.get("simple", {}).get("name", "plan_react")
        self.complex_mode = execution_mode_config.get("complex", {}).get("name", "plan_react")

        self.logger.debug(f"初始化执行模式选择器")
        self.logger.debug(f"trivial模式: {self.trivial_mode}")
        self.logger.debug(f"simple模式: {self.simple_mode}")
        self.logger.debug(f"complex模式: {self.complex_mode}")
        self._initialized = True

    def select_mode(self, task_level: str) -> str:
        """根据任务级别选择执行模式

        Args:
            task_level: 任务级别（trivial/simple/complex）

        Returns:
            执行模式名称
        """
        if task_level == "trivial":
            return self.trivial_mode
        elif task_level == "simple":
            return self.simple_mode
        elif task_level == "complex":
            return self.complex_mode
        else:
            self.logger.warning(f"未知任务级别: {task_level}，使用默认模式plan_react")
            return "plan_react"

    def get_engine(self, mode: str, session_manager=None):
        """获取执行引擎实例

        Args:
            mode: 执行模式名称
            session_manager: 会话管理器（PlanReActEngine需要）
            websocket_manager: WebSocket管理器（已弃用，使用事件系统）

        Returns:
            执行引擎实例
        """
        return PlanReActEngine(self.config, self.skill_caller, session_manager)

    def get_mode_config(self, task_level: str) -> Dict[str, Any]:
        """获取任务级别对应的配置

        Args:
            task_level: 任务级别

        Returns:
            配置字典
        """
        execution_mode_config = self.config.get("execution_mode", {})

        if task_level == "trivial":
            return execution_mode_config.get("trivial", {})
        elif task_level == "simple":
            return execution_mode_config.get("simple", {})
        elif task_level == "complex":
            return execution_mode_config.get("complex", {})
        else:
            return {}
