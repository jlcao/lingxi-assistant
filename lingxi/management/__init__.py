"""管理模块

提供工作目录管理、配置管理等管理功能
"""

from lingxi.management.workspace import (
    WorkspaceManager,
    WorkspaceError,
    WorkspaceNotFoundError,
    WorkspaceInitError,
    WorkspaceSwitchError,
    get_workspace_manager,
)

__all__ = [
    "WorkspaceManager",
    "WorkspaceError",
    "WorkspaceNotFoundError",
    "WorkspaceInitError",
    "WorkspaceSwitchError",
    "get_workspace_manager",
]
