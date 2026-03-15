#!/usr/bin/env python3
"""Create file skill - 增强版，支持追加模式"""

import logging
import os
from typing import Dict, Any


def execute(parameters: Dict[str, Any]) -> str:
    """Execute create file with enhanced features

    Args:
        parameters: Parameters dictionary
            - file_path: Absolute path to the file (required)
            - content: Content to write to the file (required)
            - mode: Write mode - "write" or "append" (optional, default: "write")
            - create_parent_dirs: Auto-create parent directories (optional, default: true)
            - encoding: File encoding (optional, default: "utf-8")

    Returns:
        Creation result
    """
    logger = logging.getLogger(__name__)

    file_path = parameters.get("file_path")
    content = parameters.get("content", "")
    mode = parameters.get("mode", "write")  # "write" or "append"
    create_parent_dirs = parameters.get("create_parent_dirs", True)
    encoding = parameters.get("encoding", "utf-8")

    if not file_path:
        return "❌ 错误：缺少文件路径"

    logger.info(f"创建文件：{file_path} (模式：{mode})")

    try:
        # 自动创建父目录
        if create_parent_dirs:
            dir_path = os.path.dirname(file_path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
                logger.info(f"创建目录：{dir_path}")

        # 选择写入模式
        file_mode = 'a' if mode == 'append' else 'w'

        # 写入文件
        with open(file_path, file_mode, encoding=encoding) as f:
            f.write(content)

        # 获取文件大小
        file_size = os.path.getsize(file_path)

        if mode == 'append':
            logger.info(f"文件追加成功：{file_path}，追加{len(content)}字节")
            return f"✅ 文件追加成功：{file_path}\n追加大小：{len(content)}字节\n当前文件大小：{file_size}字节"
        else:
            logger.info(f"文件创建成功：{file_path}，{len(content)}字节")
            return f"✅ 文件创建成功：{file_path}\n文件大小：{len(content)}字节"

    except Exception as e:
        logger.error(f"创建文件失败：{e}")
        return f"❌ 创建失败：{e}"
