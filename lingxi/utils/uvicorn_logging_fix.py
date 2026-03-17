"""Uvicorn 日志修复模块

修复 Uvicorn 日志格式化器在 stdout 关闭时的错误
"""

import sys


class SafeColourizedFormatter:
    """安全的彩色日志格式化器，处理 stdout 关闭的情况"""
    
    def __init__(self, *args, **kwargs):
        """初始化格式化器"""
        # 直接实现一个简单的格式化器，避免依赖 sys.stdout
        self.use_colors = False
        # 忽略所有不认识的参数
        self._fmt = kwargs.get('fmt', '%(levelname)s: %(message)s')
        self._datefmt = kwargs.get('datefmt')
        self._style = kwargs.get('style', '%')
    
    def format(self, record):
        """格式化日志记录"""
        # 简单的格式化实现
        try:
            msg = self._fmt % record.__dict__
        except Exception:
            # 如果格式化失败，返回原始消息
            msg = str(record.msg)
        return msg


# 替换 Uvicorn 的 ColourizedFormatter
def patch_uvicorn_logging():
    """补丁 Uvicorn 日志系统"""
    try:
        # 直接修改 uvicorn.logging 模块
        import uvicorn.logging
        
        # 保存原始的 ColourizedFormatter
        original_formatter = uvicorn.logging.ColourizedFormatter
        
        # 替换为我们的安全版本
        uvicorn.logging.ColourizedFormatter = SafeColourizedFormatter
    except Exception as e:
        # 忽略补丁失败的情况
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Uvicorn 日志补丁应用失败: {e}")
