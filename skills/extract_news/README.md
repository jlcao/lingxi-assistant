# Extract News Skill

使用 trafilatura 从网页中提取新闻内容、文章正文等主要内容的扩展技能。

## 功能特性

- 智能提取网页主要内容（去除导航栏、广告、页脚等非内容元素）
- 支持多种输出格式（Markdown、TXT、HTML、JSON、CSV、XML 等）
- 支持将提取的内容保存到本地文件
- 自动处理编码问题

## 使用方法

### 基本用法

```python
from lingxi.skills.extract_news.main import execute

# 提取新闻内容
result = execute({
    "url": "https://example.com/news/article"
})

# 提取并保存到文件
result = execute({
    "url": "https://example.com/news/article",
    "save_path": "/path/to/news.md",
    "output_format": "markdown"
})
```

### 参数说明

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| url | str | 是 | - | 网页 URL |
| timeout | int | 否 | 30 | 超时时间（秒） |
| save_path | str | 否 | - | 保存路径（绝对路径） |
| output_format | str | 否 | markdown | 输出格式：markdown, txt, html, json, csv, xml, xmltei, python |

## 输出格式

- **markdown**: Markdown 格式（默认）
- **txt**: 纯文本格式
- **html**: HTML 格式
- **json**: JSON 格式
- **csv**: CSV 格式
- **xml**: XML 格式
- **xmltei**: XML TEI 格式
- **python**: Python 字典格式

## 依赖

- trafilatura>=2.0.0

## 示例

### 提取百度热搜

```python
result = execute({
    "url": "https://top.baidu.com/board?tab=realtime",
    "output_format": "markdown"
})
```

### 提取并保存新闻

```python
result = execute({
    "url": "https://example.com/news/article",
    "save_path": "D:/news/article.md",
    "output_format": "markdown"
})
```

## 注意事项

1. 某些网站可能有反爬虫机制，可能导致提取失败
2. 动态加载的内容可能无法提取（trafilatura 不支持 JavaScript 渲染）
3. 建议使用 `markdown` 格式以获得最佳可读性
