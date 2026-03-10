__version__ = "0.1.0"

# 灵犀智能任务处理系统
# "灵犀"源自中国古代传说，象征着心灵相通、智慧敏锐

from lingxi.__main__ import LingxiAssistant
from lingxi.core.assistant.async_main import AsyncLingxiAssistant

__all__ = [
    "LingxiAssistant",
    "AsyncLingxiAssistant",
]