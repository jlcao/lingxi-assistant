#!/usr/bin/env python3
"""Read file skill - 增强版，支持流式读取、编码自动检测"""
import logging
import chardet
from typing import Dict, Any


def execute(parameters: Dict[str, Any]) -> str:
    """Execute read file with enhanced features

    Args:
        parameters: Parameters dictionary
            - file_path: Absolute path to the file (required)
            - search_text: Text to search for (optional)
            - context_lines: Number of context lines (optional, default: 5)
            - stream: Enable streaming for large files (optional, default: false)
            - chunk_size: Chunk size for streaming (optional, default: 8192)
            - max_lines: Maximum lines to read (optional, default: 1000)
            - encoding: File encoding (optional)
            - detect_encoding: Auto-detect encoding (optional, default: true)

    Returns:
        File content or search results
    """
    logger = logging.getLogger(__name__)

    file_path = parameters.get("file_path")
    search_text = parameters.get("search_text")
    context_lines = parameters.get("context_lines", 5)
    stream = parameters.get("stream", False)
    chunk_size = parameters.get("chunk_size", 8192)
    max_lines = parameters.get("max_lines", 1000)
    encoding = parameters.get("encoding")
    detect_encoding = parameters.get("detect_encoding", True)

    if not file_path:
        return "❌ 错误：缺少文件路径"

    # 自动检测编码
    if detect_encoding and not encoding:
        encoding = _detect_file_encoding(file_path, logger)

    logger.info(f"读取文件：{file_path} (编码：{encoding}, 流式：{stream})")

    # 流式读取大文件
    if stream:
        return _read_file_stream(file_path, chunk_size, encoding, max_lines, logger)

    # 普通读取
    return _read_file_normal(file_path, search_text, context_lines, encoding, max_lines, logger)


def _detect_file_encoding(file_path: str, logger: logging.Logger) -> str:
    """检测文件编码"""
    try:
        with open(file_path, 'rb') as f:
            raw = f.read(1024 * 1024)  # 读取前 1MB
            result = chardet.detect(raw)
            encoding = result['encoding']
            confidence = result['confidence']

            # 置信度>0.7 才使用检测结果
            if confidence > 0.7 and encoding:
                logger.info(f"检测到编码：{encoding} (置信度：{confidence:.2f})")
                return encoding
    except Exception as e:
        logger.warning(f"编码检测失败：{e}，使用默认 UTF-8")

    return 'utf-8'  # 默认 UTF-8


def _read_file_stream(file_path: str, chunk_size: int, encoding: str, max_lines: int, logger: logging.Logger) -> str:
    """流式读取大文件"""
    lines_count = 0
    content_chunks = []
    total_bytes = 0

    try:
        with open(file_path, 'r', encoding=encoding) as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break

                content_chunks.append(chunk)
                lines_count += chunk.count('\n')
                total_bytes += len(chunk)

                # 超过最大行数限制
                if lines_count > max_lines:
                    logger.warning(f"文件过大，已读取前{max_lines}行")
                    return f"⚠️ 文件过大，已读取前{max_lines}行（共{total_bytes}字节）\n\n" + ''.join(content_chunks)

        logger.info(f"流式读取完成：{lines_count}行，{total_bytes}字节")
        return f"✅ 文件读取成功（{lines_count}行，{total_bytes}字节）\n\n" + ''.join(content_chunks)

    except UnicodeDecodeError as e:
        logger.error(f"编码错误：{e}")
        return f"❌ 编码错误：{e}\n提示：尝试设置 encoding 参数或使用 detect_encoding=true"
    except Exception as e:
        logger.error(f"读取失败：{e}")
        return f"❌ 读取失败：{e}"


def _read_file_normal(file_path: str, search_text: str, context_lines: int, encoding: str, max_lines: int, logger: logging.Logger) -> str:
    """普通读取（带搜索功能）"""
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            lines = f.readlines()

        # 限制最大行数
        truncated_msg = ""
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            truncated_msg = f"\n\n⚠️ 文件过大，已截断至前 {max_lines} 行"
            logger.warning(f"文件截断：{len(lines)}行")

        if not search_text:
            logger.info(f"读取完成：{len(lines)}行")
            return f"📄 文件内容 ({len(lines)} 行):\n\n{''.join(lines)}{truncated_msg}"

        # 搜索功能
        search_text_lower = search_text.lower()
        results = []

        for i, line in enumerate(lines, 1):
            if search_text_lower in line.lower():
                start = max(0, i - context_lines - 1)
                end = min(len(lines), i + context_lines)
                context = ''.join(lines[start:end])
                results.append(f"--- 第 {i} 行 ---\n{context}")

        if not results:
            logger.info(f"未找到搜索文本：{search_text}")
            return f"🔍 未找到搜索文本：{search_text}{truncated_msg}"

        logger.info(f"搜索完成：{len(results)}处匹配")
        return f"🔍 搜索结果 (共{len(results)}处匹配):\n\n" + "\n\n".join(results) + truncated_msg

    except UnicodeDecodeError as e:
        logger.error(f"编码错误：{e}")
        return f"❌ 编码错误：{e}\n提示：尝试设置 encoding 参数或使用 detect_encoding=true"
    except FileNotFoundError:
        logger.error(f"文件不存在：{file_path}")
        return f"❌ 错误：文件不存在 - {file_path}"
    except Exception as e:
        logger.error(f"读取失败：{e}")
        return f"❌ 读取失败：{e}"
