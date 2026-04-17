"""工具调用相关异常类定义"""

from .exceptions import LingxiException


class ToolException(LingxiException):
    """工具调用异常基类"""

    def __init__(self, message: str, error_code: str = "TOOL_ERROR", recoverable: bool = True):
        """初始化异常

        Args:
            message: 错误信息
            error_code: 错误码
            recoverable: 是否可恢复
        """
        super().__init__(message, error_code, recoverable)


class ToolExecutionError(ToolException):
    """工具执行错误"""

    def __init__(self, message: str = "工具执行失败"):
        super().__init__(message, "TOOL_EXECUTION", recoverable=True)


class ToolValidationError(ToolException):
    """工具参数验证错误"""

    def __init__(self, message: str = "工具参数无效"):
        super().__init__(message, "TOOL_VALIDATION", recoverable=False)


class ToolNotFoundError(ToolException):
    """工具未找到错误"""

    def __init__(self, message: str = "工具不存在"):
        super().__init__(message, "TOOL_NOT_FOUND", recoverable=False)


class ToolPermissionError(ToolException):
    """工具权限错误"""

    def __init__(self, message: str = "没有执行该工具的权限"):
        super().__init__(message, "TOOL_PERMISSION", recoverable=False)


class ToolTimeoutError(ToolException):
    """工具执行超时错误"""

    def __init__(self, message: str = "工具执行超时"):
        super().__init__(message, "TOOL_TIMEOUT", recoverable=True)


class ToolDependencyError(ToolException):
    """工具依赖错误"""

    def __init__(self, message: str = "工具依赖缺失"):
        super().__init__(message, "TOOL_DEPENDENCY", recoverable=False)


class ToolConfigurationError(ToolException):
    """工具配置错误"""

    def __init__(self, message: str = "工具配置无效"):
        super().__init__(message, "TOOL_CONFIGURATION", recoverable=False)
