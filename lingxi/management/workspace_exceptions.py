"""Workspace 异常模块"""

class WorkspaceError(Exception):
    """工作目录异常基类"""
    pass


class WorkspaceNotFoundError(WorkspaceError):
    """工作目录不存在"""
    pass


class WorkspaceInitError(WorkspaceError):
    """工作目录初始化失败"""
    pass


class WorkspaceSwitchError(WorkspaceError):
    """工作目录切换失败"""
    pass
