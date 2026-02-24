"""
财联社新闻获取工具
使用Selenium获取财联社新闻内容
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import re
import sys

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'https://www.cls.cn/',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}

def get_cls_news_selenium():
    """
    使用Selenium获取财联社新闻
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time
        
        print("正在启动Chrome浏览器...")
        
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument(f'user-agent={HEADERS["User-Agent"]}')
        
        # 禁用一些不必要的功能
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-infobars')
        chrome_options.add_argument('--disable-notifications')
        
        driver = webdriver.Chrome(options=chrome_options)
        
        print("正在访问财联社...")
        driver.get('https://www.cls.cn/depth?id=1000')
        
        # 等待页面加载
        print("等待页面加载...")
        time.sleep(10)
        
        # 获取页面源码
        page_source = driver.page_source
        driver.quit()
        
        print("正在解析页面...")
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # 查找新闻元素 - 使用正确的选择器
        news_list = []
        
        # 选择器: 查找所有新闻项
        news_items = soup.find_all('div', class_='subject-interest-list')
        print(f"找到 {len(news_items)} 个新闻项")
        
        for item in news_items[:30]:
            try:
                # 标题 - subject-interest-title是div的class，a标签在里面
                title_div = item.find('div', class_='subject-interest-title')
                if title_div:
                    title_tag = title_div.find('a')
                    title = title_tag.get_text(strip=True) if title_tag else ''
                    link = title_tag.get('href', '') if title_tag else ''
                else:
                    # 备用方法
                    title_tag = item.find('a', href=True)
                    title = title_tag.get_text(strip=True) if title_tag else ''
                    link = title_tag.get('href', '') if title_tag else ''
                
                # 摘要
                brief_tag = item.find('div', class_='subject-interest-brief')
                brief = brief_tag.get_text(strip=True) if brief_tag else ''
                
                # 时间
                time_tag = item.find('div', class_='subject-interest-time')
                time_str = time_tag.get_text(strip=True) if time_tag else ''
                
                if title and link:
                    if not link.startswith('http'):
                        link = 'https://www.cls.cn' + link
                    
                    news_list.append({
                        'title': title,
                        'link': link,
                        'brief': brief,
                        'time': time_str,
                        'method': 'selenium'
                    })
            except Exception as e:
                continue
        
        # 去重
        seen = set()
        unique_news = []
        for news in news_list:
            link = news.get('link', '')
            if link and link not in seen:
                seen.add(link)
                unique_news.append(news)
        
        print(f"去重后: {len(unique_news)} 条新闻")
        return unique_news[:20]
    
    except ImportError as e:
        print(f"错误: 未安装selenium")
        print(f"安装命令: pip install selenium")
        return []
    except Exception as e:
        print(f"Selenium出错: {e}")
        import traceback
        traceback.print_exc()
        return []

def get_cls_news_requests():
    """
    使用requests获取财联社新闻（备用方法）
    """
    try:
        url = 'https://www.cls.cn/depth?id=1000'
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        news_list = []
        news_items = soup.find_all('div', class_='subject-interest-list')
        print(f"Requests方法找到 {len(news_items)} 个新闻项")
        
        for item in news_items[:20]:
            try:
                title_div = item.find('div', class_='subject-interest-title')
                if title_div:
                    title_tag = title_div.find('a')
                    title = title_tag.get_text(strip=True) if title_tag else ''
                    link = title_tag.get('href', '') if title_tag else ''
                else:
                    title_tag = item.find('a', href=True)
                    title = title_tag.get_text(strip=True) if title_tag else ''
                    link = title_tag.get('href', '') if title_tag else ''
                
                brief_tag = item.find('div', class_='subject-interest-brief')
                brief = brief_tag.get_text(strip=True) if brief_tag else ''
                
                time_tag = item.find('div', class_='subject-interest-time')
                time_str = time_tag.get_text(strip=True) if time_tag else ''
                
                if title and link:
                    if not link.startswith('http'):
                        link = 'https://www.cls.cn' + link
                    
                    news_list.append({
                        'title': title,
                        'link': link,
                        'brief': brief,
                        'time': time_str,
                        'method': 'requests'
                    })
            except Exception as e:
                continue
        
        return news_list
    
    except Exception as e:
        print(f"Requests方法失败: {e}")
        return []

def print_news(news_list):
    """打印新闻列表"""
    print(f"\n{'='*80}")
    print(f"财联社头条新闻 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")
    
    for idx, news in enumerate(news_list, 1):
        print(f"{idx}. {news['title']}")
        if news.get('brief'):
            print(f"   摘要: {news['brief'][:100]}...")
        if news.get('time'):
            print(f"   时间: {news['time']}")
        if news.get('link'):
            print(f"   链接: {news['link']}")
        print()

def save_to_json(news_list, filename='cls_news.json'):
    """保存新闻到JSON文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(news_list, f, ensure_ascii=False, indent=2)
    print(f"新闻已保存到 {filename}")

def main():
    """主函数"""
    print("="*80)
    print("财联社新闻获取工具")
    print("="*80 + "\n")
    
    # 优先使用Selenium
    print("方法1: 使用Selenium获取新闻...")
    news_list = get_cls_news_selenium()
    
    # 如果Selenium失败，尝试requests
    if not news_list:
        print("\n方法1失败，尝试方法2: 使用requests...")
        news_list = get_cls_news_requests()
    
    if news_list:
        print(f"\n✓ 成功获取 {len(news_list)} 条新闻\n")
        print_news(news_list)
        save_to_json(news_list)
    else:
        print("\n✗ 所有方法都失败了")
        print("\n请检查：")
        print("1. 网络连接是否正常")
        print("2. 是否已安装Chrome浏览器")
        print("3. selenium是否正确安装: pip install selenium")
        print("4. 查看保存的 cls_page_debug.html 了解页面结构")

if __name__ == "__main__":
    main()
