#!/usr/bin/env python3
# 测试日志系统

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath('.'))

from lingxi.utils.logging import setup_logging, get_logger
from lingxi.utils.config import load_config

# 加载配置
config = load_config()

# 配置日志系统
setup_logging(config)

# 获取日志记录器
logger = get_logger(__name__)

# 测试不同级别的日志
print("测试日志系统...")
logger.debug("这是一条 DEBUG 级别的日志")
logger.info("这是一条 INFO 级别的日志")
logger.warning("这是一条 WARNING 级别的日志")
logger.error("这是一条 ERROR 级别的日志")
logger.critical("这是一条 CRITICAL 级别的日志")

print("日志测试完成")
