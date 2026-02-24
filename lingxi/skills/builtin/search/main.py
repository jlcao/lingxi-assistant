#!/usr/bin/env python3
"""Search skill implementation"""

import logging
from typing import Dict, Any, List
import sys
import os

import importlib.util
import os

spec = importlib.util.spec_from_file_location(
    "MultiSiteSearchAgent",
    os.path.join(os.path.dirname(__file__), "MultiSiteSearchAgent.py")
)
multi_site_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(multi_site_module)
MultiSiteSearchAgent = multi_site_module.MultiSiteSearchAgent


def execute(parameters: Dict[str, Any]) -> str:
    """Execute search

    Args:
        parameters: Parameters dictionary
            - query: Search query string (required)
            - sites: List of sites to search (optional), e.g., ['csdn', 'baike', 'qqnews']
            - num_results: Number of results to return (optional, default: 10)

    Returns:
        Formatted search results
    """
    logger = logging.getLogger(__name__)

    query = parameters.get("query")
    if not query:
        return "错误: 缺少搜索查询词"

    sites = parameters.get("sites")
    num_results = parameters.get("num_results", 10)

    logger.info(f"搜索: {query}, 站点: {sites}, 结果数: {num_results}")

    try:
        search_agent = MultiSiteSearchAgent()
        results = search_agent.search(query, sites=sites, num_results=num_results)

        if not results:
            return f"未找到关于 '{query}' 的搜索结果"

        formatted_results = f"搜索结果: 关于 '{query}' 的信息\n\n"
        formatted_results += f"共找到 {len(results)} 条结果:\n\n"

        for idx, result in enumerate(results, 1):
            formatted_results += f"{idx}. 【{result['title']}】\n"
            formatted_results += f"   链接: {result['link']}\n"
            formatted_results += f"   来源: {result['source']} ({result['site']})\n"
            formatted_results += f"   摘要: {result['abstract'][:150]}...\n\n"

        return formatted_results.strip()

    except ValueError as e:
        return f"参数错误: {e}"
    except Exception as e:
        logger.error(f"搜索出错: {e}")
        return f"搜索过程中发生错误: {e}"
