"""全局状态管理模块，避免循环导入"""
from typing import Optional
from lingxi.__main__ import LingxiAssistant


assistant: Optional[LingxiAssistant] = None


def set_assistant(asst: LingxiAssistant):
    """设置助手实例

    Args:
        asst: 灵犀助手实例
    """
    global assistant
    assistant = asst


def get_assistant() -> Optional[LingxiAssistant]:
    """获取助手实例

    Returns:
        灵犀助手实例
    """
    return assistant
