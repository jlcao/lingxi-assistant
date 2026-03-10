"""Prompts 提示词模块

提供各种提示词模板和优化版本
"""

from .prompts import PromptTemplates
from .prompts_optimized import PromptTemplates as OptimizedPromptTemplates

__all__ = [
    "PromptTemplates",
    "OptimizedPromptTemplates",
]
