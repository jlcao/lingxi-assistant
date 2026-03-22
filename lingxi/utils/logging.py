import os
import logging
import logging.handlers
from typing import Dict, Any
from lingxi.utils.log_filters import WebSocketDisconnectFilter, QuietExceptionFilter

# 跟踪日志系统是否已经初始化
_logging_initialized = False


def setup_logging(config: Dict[str, Any] = None):
    """设置日志
    
    Args:
        config: 系统配置
    """
    global _logging_initialized
    
    # 如果已经初始化过，直接返回
    if _logging_initialized:
        return
    
    if not config:
        from lingxi.utils.config import get_config
        config = get_config()
    
    # 获取日志配置
    log_config = config.get("logging", {})
    log_level = log_config.get("level", "INFO")
    log_file = log_config.get("file", "logs/assistant.log")
    log_format = log_config.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # 确保日志目录存在
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
            root_logger.debug(f"创建日志目录: {log_dir}")
        except Exception as e:
            root_logger.warning(f"创建日志目录失败: {e}")
    
    # 创建日志格式化器
    formatter = logging.Formatter(log_format)
    
    # 创建根日志记录器，设置为 DEBUG 级别以捕获所有日志
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # 清除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        # 不要关闭 StreamHandler，因为它可能使用 sys.stdout 或 sys.stderr
        if not isinstance(handler, logging.StreamHandler):
            handler.close()
    
    # 创建自定义过滤器
    quiet_exception_filter = QuietExceptionFilter()
    
    # 创建控制台处理器（只输出 INFO 及以上级别）
    import sys
    try:
        # 尝试创建 UTF-8 编码的流
        import io
        stream = None
        
        # 检查 sys.stdout 是否可用
        if sys.stdout and not getattr(sys.stdout, 'closed', False):
            if hasattr(sys.stdout, 'buffer'):
                stream = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            else:
                stream = sys.stdout
        elif sys.stderr and not getattr(sys.stderr, 'closed', False):
            if hasattr(sys.stderr, 'buffer'):
                stream = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
            else:
                stream = sys.stderr
        
        if stream:
            console_handler = logging.StreamHandler(stream)
            console_handler.setLevel(log_level)
            console_handler.setFormatter(formatter)
            console_handler.addFilter(quiet_exception_filter)
            root_logger.addHandler(console_handler)
    except Exception as e:
        # 如果控制台处理器创建失败，只使用文件处理器
        print(f"创建控制台处理器失败: {e}", file=sys.stderr)
    
    # 创建主日志文件处理器（只输出 INFO 及以上级别）
    try:
        rotation_type = log_config.get("rotation_type", "size")  # size 或 time
        backup_count = log_config.get("backup_count", 5)
        
        if rotation_type == "time":
            # 基于时间的轮转
            when = log_config.get("rotation_when", "D")  # 轮转时间单位: S, M, H, D, W0-W6, midnight
            interval = log_config.get("rotation_interval", 1)  # 轮转间隔
            utc = log_config.get("rotation_utc", False)  # 是否使用 UTC 时间
            
            file_handler = logging.handlers.TimedRotatingFileHandler(
                log_file,
                when=when,
                interval=interval,
                backupCount=backup_count,
                encoding='utf-8',
                utc=utc
            )
        else:
            # 基于大小的轮转
            max_file_size = log_config.get("max_file_size_mb", 10) * 1024 * 1024
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
        
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(quiet_exception_filter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        # 如果创建文件处理器失败，只使用控制台处理器
        root_logger.warning(f"创建日志文件处理器失败: {e}")
    
    # 创建 DEBUG 日志文件处理器（只输出 DEBUG 级别）
    try:
        debug_log_file = os.path.join(os.path.dirname(log_file), "debug.log")
        rotation_type = log_config.get("rotation_type", "size")
        backup_count = log_config.get("backup_count", 5)
        
        if rotation_type == "time":
            when = log_config.get("rotation_when", "D")
            interval = log_config.get("rotation_interval", 1)
            utc = log_config.get("rotation_utc", False)
            
            debug_file_handler = logging.handlers.TimedRotatingFileHandler(
                debug_log_file,
                when=when,
                interval=interval,
                backupCount=backup_count,
                encoding='utf-8',
                utc=utc
            )
        else:
            max_file_size = log_config.get("max_file_size_mb", 10) * 1024 * 1024
            
            debug_file_handler = logging.handlers.RotatingFileHandler(
                debug_log_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
        
        debug_file_handler.setLevel(logging.DEBUG)
        debug_file_handler.setFormatter(formatter)
        root_logger.addHandler(debug_file_handler)
    except Exception as e:
        root_logger.warning(f"创建 DEBUG 日志文件处理器失败: {e}")
    
    # 配置第三方库日志
    _configure_third_party_logs(config)
    
    root_logger.info("日志系统初始化完成")
    root_logger.info(f"日志级别: {log_level}")
    root_logger.info(f"日志文件: {log_file}")
    root_logger.info(f"日志轮转类型: {rotation_type}")
    if rotation_type == "time":
        root_logger.info(f"轮转时间单位: {when}")
        root_logger.info(f"轮转间隔: {interval}")
    else:
        root_logger.info(f"最大文件大小: {log_config.get('max_file_size_mb', 10)}MB")
    root_logger.info(f"备份文件数量: {backup_count}")
    root_logger.debug(f"DEBUG 日志文件: {os.path.join(os.path.dirname(log_file), 'debug.log')}")
    
    # 标记日志系统已经初始化
    _logging_initialized = True

def _configure_third_party_logs(config: Dict[str, Any]):
    """配置第三方库日志
    
    Args:
        config: 系统配置
    """
    # 配置requests库日志
    requests_logger = logging.getLogger("requests")
    requests_logger.setLevel(logging.WARNING)
    
    # 配置urllib3库日志
    urllib3_logger = logging.getLogger("urllib3")
    urllib3_logger.setLevel(logging.WARNING)
    
    # 配置openai库日志
    openai_logger = logging.getLogger("openai")
    openai_logger.setLevel(logging.WARNING)
    
    # 配置flask库日志
    flask_logger = logging.getLogger("flask")
    flask_logger.setLevel(logging.WARNING)
    
    # 配置sqlalchemy库日志
    sqlalchemy_logger = logging.getLogger("sqlalchemy")
    sqlalchemy_logger.setLevel(logging.WARNING)
    
    # 配置httpcore库日志（关闭HTTP连接的debug日志）
    httpcore_logger = logging.getLogger("httpcore")
    httpcore_logger.setLevel(logging.WARNING)
    
    # 配置httpx库日志
    httpx_logger = logging.getLogger("httpx")
    httpx_logger.setLevel(logging.WARNING)
    
    # 配置事件发布系统日志（开启debug日志）
    event_logger = logging.getLogger("lingxi.core.event")
    event_logger.setLevel(logging.DEBUG)
    
    # 配置事件发布者日志
    publisher_logger = logging.getLogger("lingxi.core.event.publisher")
    publisher_logger.setLevel(logging.DEBUG)

def get_logger(name: str = None) -> logging.Logger:
    """获取日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        日志记录器实例
    """
    return logging.getLogger(name)

def set_log_level(level: str):
    """设置日志级别
    
    Args:
        level: 日志级别
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    for handler in root_logger.handlers:
        handler.setLevel(level)

def add_file_handler(log_file: str, level: str = "INFO", max_bytes: int = 10 * 1024 * 1024, backup_count: int = 5):
    """添加文件处理器
    
    Args:
        log_file: 日志文件路径
        level: 日志级别
        max_bytes: 最大文件大小
        backup_count: 备份文件数量
    """
    # 确保日志目录存在
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
            root_logger.debug(f"创建日志目录: {log_dir}")
        except Exception as e:
            root_logger.warning(f"创建日志目录失败: {e}")
    
    # 创建文件处理器
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    
    # 设置日志级别和格式化器
    file_handler.setLevel(level)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    
    # 添加到根日志记录器
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)

def remove_file_handler(log_file: str):
    """移除文件处理器
    
    Args:
        log_file: 日志文件路径
    """
    root_logger = logging.getLogger()
    
    for handler in root_logger.handlers[:]:
        if hasattr(handler, "baseFilename") and handler.baseFilename == os.path.abspath(log_file):
            root_logger.removeHandler(handler)
            handler.close()
            break

if __name__ == "__main__":
    # 测试日志设置
    from lingxi.utils.config import load_config
    
    config = load_config()
    setup_logging(config)
    
    logger = get_logger(__name__)
    logger.debug("调试信息")
    logger.info("信息")
    logger.warning("警告")
    logger.error("错误")
    logger.critical("严重错误")
    
    print("日志测试完成")