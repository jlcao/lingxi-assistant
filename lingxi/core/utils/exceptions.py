"""自定义异常类定义"""


class LingxiException(Exception):
    """灵犀助手基础异常类"""

    def __init__(self, message: str, error_code: str = "UNKNOWN", recoverable: bool = True):
        """初始化异常

        Args:
            message: 错误信息
            error_code: 错误码
            recoverable: 是否可恢复
        """
        super().__init__(message)
        self.error_code = error_code
        self.recoverable = recoverable


class LLMException(LingxiException):
    """LLM相关异常基类"""

    def __init__(self, message: str, error_code: str = "LLM_ERROR", recoverable: bool = True):
        super().__init__(message, error_code, recoverable)


class LLMRateLimitError(LLMException):
    """LLM API限流错误"""

    def __init__(self, message: str = "LLM API调用频率超限"):
        super().__init__(message, "LLM_RATE_LIMIT", recoverable=True)


class LLMTimeoutError(LLMException):
    """LLM API超时错误"""

    def __init__(self, message: str = "LLM API请求超时"):
        super().__init__(message, "LLM_TIMEOUT", recoverable=True)


class LLMConnectionError(LLMException):
    """LLM API连接错误"""

    def __init__(self, message: str = "LLM API连接失败"):
        super().__init__(message, "LLM_CONNECTION", recoverable=True)


class LLMResponseError(LLMException):
    """LLM API响应错误"""

    def __init__(self, message: str = "LLM API响应无效"):
        super().__init__(message, "LLM_RESPONSE", recoverable=True)


class LLMTokenLimitError(LLMException):
    """LLM Token超限错误"""

    def __init__(self, message: str = "LLM Token使用超限"):
        super().__init__(message, "LLM_TOKEN_LIMIT", recoverable=False)


class SkillException(LingxiException):
    """技能相关异常基类"""

    def __init__(self, message: str, error_code: str = "SKILL_ERROR", recoverable: bool = True):
        super().__init__(message, error_code, recoverable)


class SkillExecutionError(SkillException):
    """技能执行错误"""

    def __init__(self, message: str = "技能执行失败"):
        super().__init__(message, "SKILL_EXECUTION", recoverable=True)


class SkillNotFoundError(SkillException):
    """技能未找到错误"""

    def __init__(self, message: str = "技能不存在"):
        super().__init__(message, "SKILL_NOT_FOUND", recoverable=False)


class SkillLoadError(SkillException):
    """技能加载错误"""

    def __init__(self, message: str = "技能加载失败"):
        super().__init__(message, "SKILL_LOAD", recoverable=False)


class SkillDependencyError(SkillException):
    """技能依赖错误"""

    def __init__(self, message: str = "技能依赖缺失"):
        super().__init__(message, "SKILL_DEPENDENCY", recoverable=False)


class DatabaseException(LingxiException):
    """数据库相关异常基类"""

    def __init__(self, message: str, error_code: str = "DATABASE_ERROR", recoverable: bool = True):
        super().__init__(message, error_code, recoverable)


class DatabaseLockedError(DatabaseException):
    """数据库锁错误"""

    def __init__(self, message: str = "数据库繁忙，请稍后重试"):
        super().__init__(message, "DATABASE_LOCKED", recoverable=True)


class DatabaseConnectionError(DatabaseException):
    """数据库连接错误"""

    def __init__(self, message: str = "数据库连接失败"):
        super().__init__(message, "DATABASE_CONNECTION", recoverable=True)


class DatabaseQueryError(DatabaseException):
    """数据库查询错误"""

    def __init__(self, message: str = "数据库查询失败"):
        super().__init__(message, "DATABASE_QUERY", recoverable=True)


class TaskException(LingxiException):
    """任务相关异常基类"""

    def __init__(self, message: str, error_code: str = "TASK_ERROR", recoverable: bool = True):
        super().__init__(message, error_code, recoverable)


class TaskTimeoutError(TaskException):
    """任务超时错误"""

    def __init__(self, message: str = "任务执行超时"):
        super().__init__(message, "TASK_TIMEOUT", recoverable=True)


class TaskCancelledError(TaskException):
    """任务取消错误"""

    def __init__(self, message: str = "任务已取消"):
        super().__init__(message, "TASK_CANCELLED", recoverable=True)


class TaskValidationError(TaskException):
    """任务验证错误"""

    def __init__(self, message: str = "任务参数无效"):
        super().__init__(message, "TASK_VALIDATION", recoverable=False)


class ResourceException(LingxiException):
    """资源相关异常基类"""

    def __init__(self, message: str, error_code: str = "RESOURCE_ERROR", recoverable: bool = True):
        super().__init__(message, error_code, recoverable)


class ResourceLimitError(ResourceException):
    """资源限制错误"""

    def __init__(self, message: str = "资源使用超限"):
        super().__init__(message, "RESOURCE_LIMIT", recoverable=False)


class MemoryLimitError(ResourceException):
    """内存限制错误"""

    def __init__(self, message: str = "内存使用超限"):
        super().__init__(message, "MEMORY_LIMIT", recoverable=False)


def map_exception_to_error_code(exception: Exception) -> tuple:
    """将异常映射到错误码和可恢复性

    Args:
        exception: 异常对象

    Returns:
        (错误码, 可恢复性)
    """
    from .ToolException import ToolException
    
    if isinstance(exception, LLMException):
        return exception.error_code, exception.recoverable
    elif isinstance(exception, SkillException):
        return exception.error_code, exception.recoverable
    elif isinstance(exception, DatabaseException):
        return exception.error_code, exception.recoverable
    elif isinstance(exception, TaskException):
        return exception.error_code, exception.recoverable
    elif isinstance(exception, ResourceException):
        return exception.error_code, exception.recoverable
    elif isinstance(exception, ToolException):
        return exception.error_code, exception.recoverable
    elif isinstance(exception, TimeoutError):
        return "TIMEOUT", True
    elif isinstance(exception, ConnectionError):
        return "CONNECTION_ERROR", True
    elif isinstance(exception, ValueError):
        return "INVALID_INPUT", False
    elif isinstance(exception, KeyError):
        return "MISSING_KEY", False
    else:
        return "UNKNOWN", True
