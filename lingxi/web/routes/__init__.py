"""API 路由模块"""
from lingxi.web.routes import tasks, checkpoints, skills, config, sessions, workspace

try:
    from lingxi.web.routes import resources
except ImportError:
    resources = None

__all__ = [
    "tasks",
    "checkpoints",
    "skills",
    "resources",
    "config",
    "sessions",
    "workspace"
]
