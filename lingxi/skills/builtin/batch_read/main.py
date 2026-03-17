#!/usr/bin/env python3
"""Batch read files skill - 批量读取多个文件"""

import logging
import os
import glob
from typing import Dict, Any, List


def execute(parameters: Dict[str, Any]) -> str:
    """
    批量读取文件

    Args:
        parameters: Parameters dictionary
            - file_paths: 文件路径列表（可选）
            - pattern: 文件匹配模式（可选，如 "*.py"）
            - directory: 搜索目录（可选，与 pattern 配合使用）
            - max_files: 最大文件数（可选，默认 20）
            - max_size_per_file: 单个文件最大字节数（可选，默认 100KB）
            - encoding: 文件编码（可选，默认 utf-8）

    Returns:
        批量读取结果
    """
    logger = logging.getLogger(__name__)

    file_paths = parameters.get("file_paths", [])
    pattern = parameters.get("pattern")
    directory = parameters.get("directory")
    max_files = parameters.get("max_files", 20)
    max_size_per_file = parameters.get("max_size_per_file", 100 * 1024)
    encoding = parameters.get("encoding", "utf-8")

    # 使用 pattern 搜索文件
    if pattern and directory:
        search_pattern = os.path.join(directory, "**", pattern)
        file_paths = glob.glob(search_pattern, recursive=True)
        file_paths = file_paths[:max_files]
        logger.info(f"搜索到 {len(file_paths)} 个文件 (pattern: {pattern})")

    if not file_paths:
        return "❌ 错误：没有指定文件路径"

    logger.info(f"批量读取 {len(file_paths)} 个文件")

    # 批量读取
    results = []
    total_size = 0
    total_lines = 0

    for file_path in file_paths[:max_files]:
        try:
            # 检查文件大小
            file_size = os.path.getsize(file_path)
            if file_size > max_size_per_file:
                results.append({
                    "path": file_path,
                    "error": f"文件过大 ({file_size}字节 > {max_size_per_file}字节限制)",
                    "success": False
                })
                logger.warning(f"文件过大跳过：{file_path} ({file_size}字节)")
                continue

            # 读取文件
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()

            lines = content.count('\n') + 1
            results.append({
                "path": file_path,
                "content": content,
                "size": file_size,
                "lines": lines,
                "success": True
            })

            total_size += file_size
            total_lines += lines
            logger.debug(f"读取成功：{file_path} ({file_size}字节，{lines}行)")

        except Exception as e:
            results.append({
                "path": file_path,
                "error": str(e),
                "success": False
            })
            logger.error(f"读取失败：{file_path} - {e}")

    # 生成报告
    success_count = sum(1 for r in results if r.get("success"))
    failed_count = len(results) - success_count

    report = f"📦 批量读取完成\n\n"
    report += f"✅ 成功：{success_count}个\n"
    report += f"❌ 失败：{failed_count}个\n"
    report += f"📊 总计：{total_size}字节，{total_lines}行\n\n"

    # 显示内容
    for result in results:
        report += f"{'='*60}\n"
        report += f"📄 {result['path']}\n"
        report += f"{'='*60}\n"

        if result.get("success"):
            report += f"大小：{result['size']}字节 | 行数：{result['lines']}\n\n"
            content = result.get("content", "")
            # 限制显示长度
            if len(content) > 2000:
                report += content[:2000]
                report += "\n...（内容已截断）"
            else:
                report += content
        else:
            report += f"❌ 错误：{result.get('error')}\n"

        report += "\n\n"

    logger.info(f"批量读取完成：{success_count}成功，{failed_count}失败")
    return report
