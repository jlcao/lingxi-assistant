#!/usr/bin/env python3
"""Get latest financial news from CaiLian She"""

import logging
import sys
import os
from typing import Dict, Any, List
from datetime import datetime, timedelta
import re

import importlib.util
import os

spec = importlib.util.spec_from_file_location(
    "get_cls_news_final",
    os.path.join(os.path.dirname(__file__), "get_cls_news_final.py")
)
cls_news_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cls_news_module)
get_cls_news_selenium = cls_news_module.get_cls_news_selenium
get_cls_news_requests = cls_news_module.get_cls_news_requests
get_cls_news_playwright = cls_news_module.get_cls_news_playwright_sync


def parse_time_str(time_str: str) -> datetime:
    """Parse time string to datetime object
    
    Args:
        time_str: Time string like "10:30", "10-30 10:30", "2024-01-15"
    
    Returns:
        datetime object
    """
    now = datetime.now()
    
    if not time_str:
        return now
    
    time_str = time_str.strip()
    
    try:
        if ':' in time_str:
            if '-' in time_str:
                return datetime.strptime(time_str, '%m-%d %H:%M').replace(year=now.year)
            else:
                return datetime.strptime(time_str, '%H:%M').replace(
                    year=now.year, month=now.month, day=now.day
                )
        elif '-' in time_str:
            return datetime.strptime(time_str, '%Y-%m-%d')
    except ValueError:
        pass
    
    return now


def filter_news_by_hours(news_list: List[Dict], hours: int = 24) -> List[Dict]:
    """Filter news by time range
    
    Args:
        news_list: List of news items
        hours: Number of hours to filter
    
    Returns:
        Filtered news list
    """
    if hours <= 0:
        return news_list
    
    cutoff_time = datetime.now() - timedelta(hours=hours)
    filtered_news = []
    
    for news in news_list:
        time_str = news.get('time', '')
        news_time = parse_time_str(time_str)
        
        if news_time >= cutoff_time:
            filtered_news.append(news)
    
    return filtered_news


def format_news_results(news_list: List[Dict]) -> str:
    """Format news results for display
    
    Args:
        news_list: List of news items
    
    Returns:
        Formatted string
    """
    if not news_list:
        return "未找到符合条件的财经新闻"
    
    result = f"财经头条新闻 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    result += f"{'='*80}\n\n"
    result += f"共找到 {len(news_list)} 条新闻:\n\n"
    
    for idx, news in enumerate(news_list, 1):
        result += f"{idx}. 【{news['title']}】\n"
        
        if news.get('brief'):
            brief = news['brief'][:150] + '...' if len(news['brief']) > 150 else news['brief']
            result += f"   摘要: {brief}\n"
        
        if news.get('time'):
            result += f"   时间: {news['time']}\n"
        
        if news.get('link'):
            result += f"   链接: {news['link']}\n"
        
        result += "\n"
    
    return result.strip()


def execute(parameters: Dict[str, Any]) -> str:
    """Execute financial news retrieval
    
    Args:
        parameters: Parameters dictionary
            - hours: Filter news from last N hours (optional, default: 24)
            - num_results: Number of news items to return (optional, default: 20)
            - method: Preferred method - "playwright", "selenium" or "requests" (optional, default: "playwright")
    
    Returns:
        Formatted financial news
    """
    logger = logging.getLogger(__name__)
    
    hours = parameters.get("hours", 24)
    num_results = parameters.get("num_results", 20)
    method = parameters.get("method", "playwright")
    
    logger.info(f"获取财经新闻: 最近{hours}小时, 结果数:{num_results}, 方法:{method}")
    
    try:
        news_list = []
        
        if method == "requests":
            logger.info("使用 requests 方法获取新闻")
            news_list = get_cls_news_requests()
        elif method == "selenium":
            logger.info("使用 selenium 方法获取新闻")
            news_list = get_cls_news_selenium()
            
            if not news_list:
                logger.info("Selenium 方法失败，回退到 requests 方法")
                news_list = get_cls_news_requests()
        else:
            logger.info("使用 playwright 方法获取新闻")
            news_list = get_cls_news_playwright()
            
            if not news_list:
                logger.info("Playwright 方法失败，回退到 selenium 方法")
                news_list = get_cls_news_selenium()
                
                if not news_list:
                    logger.info("Selenium 方法失败，回退到 requests 方法")
                    news_list = get_cls_news_requests()
        
        if not news_list:
            return "未能获取到财经新闻，请检查网络连接或稍后重试"
        
        logger.info(f"获取到 {len(news_list)} 条新闻")
        
        filtered_news = filter_news_by_hours(news_list, hours)
        logger.info(f"过滤后剩余 {len(filtered_news)} 条新闻")
        
        if not filtered_news:
            return f"最近 {hours} 小时内没有找到符合条件的财经新闻"
        
        limited_news = filtered_news[:num_results]
        
        return format_news_results(limited_news)
    
    except Exception as e:
        logger.error(f"获取财经新闻失败: {e}")
        return f"获取财经新闻失败: {str(e)}"


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
