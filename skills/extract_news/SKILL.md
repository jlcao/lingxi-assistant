---
name: extract_news
description: "Extract news content from webpage using trafilatura. Use this skill when user needs to extract main content from news articles, blog posts, or web pages."
version: "1.0.0"
trigger_conditions: "用户请求从网页提取新闻内容、文章正文、去除广告和导航栏时触发"
execution_guidelines: "1. 验证url参数\n2. 使用trafilatura提取网页主要内容\n3. 支持提取标题、正文、作者、发布日期等\n4. 如果提供save_path，保存到文件\n5. 返回提取的新闻内容"
author: "Lingxi Team"
license: MIT
---

# Extract News Skill

## Overview

The extract_news skill uses trafilatura to extract the main content from webpages. It intelligently removes navigation bars, ads, footers, and other non-content elements, leaving only the main article content.

## Usage

### Parameters

- **url** (required): Webpage URL to extract news from
- **timeout** (optional): Timeout in seconds (default: 30)
- **save_path** (optional): Absolute path to save extracted content (if not provided, content is not saved)
- **output_format** (optional): Output format - "markdown" (default), "txt", "html", "json", "csv", "xml", "xmltei", or "python". Note: "text" is automatically converted to "txt"

### Example

```python
# Extract news content
extract_news(url="https://example.com/news/article")

# Extract and save news
extract_news(
    url="https://example.com/news/article",
    save_path="/path/to/news.md"
)

# Extract with custom format
extract_news(
    url="https://example.com/news/article",
    output_format="text"
)
```

## Implementation Notes

- Uses trafilatura for content extraction
- Removes navigation, ads, and non-content elements
- Supports Markdown and plain text output
- Extracts title, author, date, and main content
- Returns structured news information

## Dependencies

- `trafilatura`: For webpage content extraction
- `requests`: For HTTP requests
