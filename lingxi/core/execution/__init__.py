"""执行模式选择器模块

根据任务级别选择执行模式，通过依赖注入实现解耦
"""

import logging
from typing import Dict, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from lingxi.core.interfaces import ISkillCaller


class ExecutionModeSelector:
    """执行模式选择器，根据任务分级选择执行模式
    
    优化后统一使用 PlanReActEngine 处理 simple/complex 任务：
    - trivial: DirectEngine（直接回答问候、简单问答）
    - simple: PlanReActEngine（智能路由，直接执行 next_action）
    - complex: PlanReActEngine（智能路由，执行多步计划）
    """
    
    _instance = None  # 单例实例
    
    def __new__(cls, config: Dict[str, Any], skill_caller: Optional['ISkillCaller'] = None):
        """单例模式：确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config: Dict[str, Any], skill_caller: Optional['ISkillCaller'] = None):
        """初始化执行模式选择器

        Args:
            config: 系统配置
            skill_caller: 技能调用器（用于传递给引擎）
        """
        self.config = config
        self._skill_caller = skill_caller
        self.logger = logging.getLogger(__name__)

        execution_mode_config = config.get("execution_mode", {})

        self.trivial_mode = execution_mode_config.get("trivial", {}).get("name", "direct")
        self.simple_mode = execution_mode_config.get("simple", {}).get("name", "plan_react")
        self.complex_mode = execution_mode_config.get("complex", {}).get("name", "plan_react")

        self.logger.debug(f"初始化执行模式选择器")
        self.logger.debug(f"trivial模式: {self.trivial_mode}")
        self.logger.debug(f"simple模式: {self.simple_mode}")
        self.logger.debug(f"complex模式: {self.complex_mode}")
    
    def set_skill_caller(self, skill_caller: 'ISkillCaller') -> None:
        """设置技能调用器（依赖注入）
        
        Args:
            skill_caller: 技能调用器实例
        """
        self._skill_caller = skill_caller
        self.logger.debug("技能调用器已注入")
    
    @property
    def skill_caller(self) -> 'ISkillCaller':
        """获取技能调用器"""
        if self._skill_caller is None:
            raise RuntimeError("技能调用器未设置，请先调用 set_skill_caller() 方法")
        return self._skill_caller

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

    def get_engine_factory(self, mode: str):
        """获取引擎工厂函数（延迟创建引擎实例）
        
        Args:
            mode: 执行模式名称
            
        Returns:
            引擎工厂函数
        """
        if mode == "direct":
            return self._create_direct_engine
        elif mode == "plan_react":
            return self._create_plan_react_engine
        else:
            self.logger.warning(f"未知执行模式: {mode}，使用默认引擎 PlanReActEngine")
            return self._create_plan_react_engine
    
    def _create_direct_engine(self, session_manager=None):
        """创建 DirectEngine 实例
        
        Args:
            session_manager: 会话管理器
            
        Returns:
            DirectEngine 实例
        """
        from lingxi.core.engine.direct import DirectEngine
        return DirectEngine(self.config, self.skill_caller, session_manager)
    
    def _create_plan_react_engine(self, session_manager=None):
        """创建 PlanReActEngine 实例
        
        Args:
            session_manager: 会话管理器
            
        Returns:
            PlanReActEngine 实例
        """
        from lingxi.core.engine.plan_react import PlanReActEngine
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
