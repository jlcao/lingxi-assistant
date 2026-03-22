---
name: financial_news
description: "Get latest financial news headlines from CaiLian She (财联社). Use this skill when user asks for financial news, stock market news, or economic headlines."
version: "1.0.0"
trigger_conditions: "用户请求获取财经新闻、股市新闻、经济头条时触发"
execution_guidelines: "1. 验证参数\n2. 优先使用Selenium获取新闻（支持动态内容）\n3. 如果Selenium失败，回退到requests方法\n4. 过滤最近24小时的新闻\n5. 返回格式化的新闻列表"
author: "Lingxi Team"
license: MIT
---

# Financial News Skill

## Overview

The financial_news skill retrieves the latest financial news headlines from CaiLian She (财联社), a leading Chinese financial news platform. It supports both Selenium (for dynamic content) and requests (for static content) methods.

## Usage

### Parameters

- **hours** (optional): Filter news from the last N hours (default: 24)
- **num_results** (optional): Number of news items to return (default: 20)
- **method** (optional): Preferred method - "selenium" (default) or "requests"

### Example

```python
# Get latest financial news (last 24 hours)
financial_news()

# Get news from last 6 hours
financial_news(hours=6)

# Get 10 news items
financial_news(num_results=10)

# Use requests method instead of selenium
financial_news(method="requests")
```

## Implementation Notes

This skill integrates with get_cls_news_final.py to provide real-time financial news:

1. **Dual Method Support**: 
   - Selenium: Handles dynamic JavaScript-rendered content
   - Requests: Fallback for static content

2. **Time Filtering**: Filters news based on publication time within specified hours

3. **Error Handling**: Graceful fallback between methods with detailed error messages

4. **News Structure**: Returns title, link, brief, and time for each news item

## Dependencies

- `selenium`: For dynamic content extraction (optional)
- `requests`: For HTTP requests
- `beautifulsoup4`: For HTML parsing
- `webdriver-manager`: For automatic Chrome driver management (optional)

## Supported Sources

- **财联社 (CaiLian She)**: https://www.cls.cn/depth?id=1000
