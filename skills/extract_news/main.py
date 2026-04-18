#!/usr/bin/env python3
"""Extract news content from webpage using trafilatura"""

import logging
import os
from typing import Dict, Any


def execute(parameters: Dict[str, Any]) -> str:
    """Execute extract news

    Args:
        parameters: Parameters dictionary
            - url: Webpage URL (required)
            - timeout: Timeout in seconds (optional, default: 30)
            - save_path: Absolute path to save content (optional)
            - output_format: Output format - "markdown" (default), "txt", "html", "json", "csv", "xml", "xmltei", or "python" (optional)

    Returns:
        Extracted news content or save result
    """
    logger = logging.getLogger(__name__)

    url = parameters.get("url")
    timeout = parameters.get("timeout", 30)
    save_path = parameters.get("save_path")
    output_format = parameters.get("output_format", "markdown")

    if not url:
        return "错误: 缺少URL"

    logger.info(f"提取新闻内容: {url}")

    try:
        import trafilatura

        downloaded = trafilatura.fetch_url(url)

        if not downloaded:
            return f"错误: 无法下载网页内容"

        valid_formats = ["csv", "html", "json", "markdown", "python", "txt", "xml", "xmltei"]
        
        if output_format not in valid_formats:
            if output_format == "text":
                output_format = "txt"
            else:
                return f"错误: 不支持的输出格式 '{output_format}'，支持的格式: {', '.join(valid_formats)}"

        extracted = trafilatura.extract(downloaded, output_format=output_format)

        if not extracted:
            return f"错误: 无法提取网页主要内容"

        result = extracted

        if save_path:
            dir_path = os.path.dirname(save_path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)

            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(result)

            return f"新闻内容已保存到: {save_path}\n内容长度: {len(result)} 字符"
        else:
            return result

    except Exception as e:
        logger.error(f"提取新闻内容失败: {e}")
        return f"提取新闻内容失败: {str(e)}"


if __name__ == "__main__":
    import argparse
    import json
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--params", type=str, required=True, help="参数文件路径")
    args = parser.parse_args()
    
    with open(args.params, "r", encoding="utf-8") as f:
        parameters = json.load(f)
    
    result = execute(parameters)
    print(result)
