#!/usr/bin/env python3
"""技能基类 - 提供可选的基类和辅助工具

现有技能实现模式：
- 元数据从 SKILL.md 或 skill.json 加载
- 技能代码只需要提供 execute 函数/方法

本模块提供：
1. BaseSkill：可选的抽象基类（用于需要强类型约束的场景）
2. SimpleSkill：简单的基类实现（可直接使用）
3. 元数据访问工具函数
"""

import abc
from typing import Any, Dict, Optional, Callable, Union
from .execution_context import ExecutionContext
from .skill_response import SkillResponse


class BaseSkill(abc.ABC):
    """技能抽象基类（可选使用）

    对于需要强类型约束和统一接口的场景，可以继承此类。
    对于现有技能，不需要强制继承，保持灵活性。
    """

    def __init__(
        self,
        manifest: Optional[Dict[str, Any]] = None,
        context: Optional[ExecutionContext] = None
    ):
        self.manifest = manifest or {}
        self.context = context or ExecutionContext()

    @abc.abstractmethod
    async def execute(self, params: Dict[str, Any]) -> SkillResponse:
        pass

    def sync_execute(self, params: Dict[str, Any]) -> SkillResponse:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.execute(params))


class SimpleSkill(BaseSkill):
    """简单技能实现（可直接使用）

    包装现有的 execute 函数，适配新的接口。
    """

    def __init__(
        self,
        execute_func: Callable,
        manifest: Optional[Dict[str, Any]] = None,
        context: Optional[ExecutionContext] = None
    ):
        super().__init__(manifest, context)
        self._execute_func = execute_func

    async def execute(self, params: Dict[str, Any]) -> SkillResponse:
        result = self._execute_func(params)
        
        if isinstance(result, SkillResponse):
            return result
        
        if isinstance(result, dict):
            if "success" in result:
                return SkillResponse.from_dict(result)
            return SkillResponse.success(data=result)
        
        if isinstance(result, str):
            if result.startswith("错误") or result.startswith("error"):
                return SkillResponse.error(message=result)
            return SkillResponse.success(data=result)
        
        return SkillResponse.success(data=result)


def wrap_execute_function(
    execute_func: Callable,
    manifest: Optional[Dict[str, Any]] = None,
    context: Optional[ExecutionContext] = None
) -> SimpleSkill:
    """包装现有的 execute 函数为 Skill 对象

    Args:
        execute_func: 原有的 execute 函数
        manifest: 技能清单
        context: 执行上下文

    Returns:
        SimpleSkill 实例
    """
    return SimpleSkill(execute_func, manifest, context)


def get_skill_id(manifest: Dict[str, Any]) -> Optional[str]:
    """从清单获取技能ID"""
    return manifest.get("skill_id") or manifest.get("name")


def get_version(manifest: Dict[str, Any]) -> str:
    """从清单获取版本号"""
    return manifest.get("version", "1.0.0")


def get_description(manifest: Dict[str, Any]) -> str:
    """从清单获取描述"""
    return manifest.get("description", "")


def get_author(manifest: Dict[str, Any]) -> str:
    """从清单获取作者"""
    return manifest.get("author", "")


def get_trust_level(manifest: Dict[str, Any]) -> str:
    """从清单获取信任等级"""
    return manifest.get("trust_level", "L1")


def is_isolated_env(manifest: Dict[str, Any]) -> bool:
    """从清单判断是否使用独立环境"""
    return manifest.get("isolated_env", False)


def get_permissions(manifest: Dict[str, Any]) -> list:
    """从清单获取权限列表"""
    return manifest.get("permissions", [])


def get_risks(manifest: Dict[str, Any]) -> list:
    """从清单获取风险列表"""
    return manifest.get("risks", [])

