"""SOUL 注入系统 - 灵犀助手个性塑造模块

该模块提供 SOUL.md 文件的解析、缓存和提示词注入功能，
让灵犀助手能够读取并遵循 SOUL.md 来塑造个性。
"""

from .soul_injector import SoulInjector
from .soul_parser import SoulParser
from .soul_cache import SoulCache

__all__ = ['SoulInjector', 'SoulParser', 'SoulCache']
