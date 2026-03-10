"""Workspace 模块 - 兼容性封装

为保持向后兼容，将异常类和管理器重新导出到同一命名空间
"""

from .workspace_exceptions import WorkspaceError, WorkspaceNotFoundError, WorkspaceInitError, WorkspaceSwitchError
from .workspace_manager import WorkspaceManager, get_workspace_manager, reset_workspace_manager

__all__ = [
    "WorkspaceError",
    "WorkspaceNotFoundError",
    "WorkspaceInitError",
    "WorkspaceSwitchError",
    "WorkspaceManager",
    "get_workspace_manager",
    "reset_workspace_manager",
]
