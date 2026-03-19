import requests
from bs4 import BeautifulSoup
import urllib.parse
import time

# 配置请求头，模拟浏览器访问
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'https://www.baidu.com/',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}

class MultiSiteSearchAgent:
    """多站点搜索Agent技能类"""
    
    def __init__(self):
        # 定义支持的站点及搜索语法前缀
        self.supported_sites = {
            'csdn': 'site:csdn.net',
            'baike': 'site:baike.baidu.com',
            'qqnews': 'site:news.qq.com',
            'bing': 'site:bing.com'
        }
        self.search_base_url = 'https://www.baidu.com/s'

    def search(self, query: str, sites: list = None, num_results: int = 10) -> list:
        """
        执行多站点搜索
        :param query: 搜索关键词
        :param sites: 指定搜索的站点列表，如['csdn', 'baike']，默认搜索全部
        :param num_results: 返回结果数量
        :return: 结构化的搜索结果列表
        """
        # 处理默认站点
        if not sites:
            sites = list(self.supported_sites.keys())
        
        # 验证站点合法性
        invalid_sites = [s for s in sites if s not in self.supported_sites]
        if invalid_sites:
            raise ValueError(f"不支持的站点：{invalid_sites}，支持的站点有：{list(self.supported_sites.keys())}")
        
        # 分别查询每个站点，避免触发验证码
        results = []
        results_per_site = num_results // len(sites) + 1  # 每个站点查询的结果数
        
        for site in sites:
            site_filter = self.supported_sites[site]
            full_query = f"{query} {site_filter}"
            
            try:
                params = {
                    'wd': full_query,
                    'pn': 0,
                    'rn': results_per_site
                }
                response = requests.get(self.search_base_url, params=params, headers=HEADERS, timeout=10)
                response.raise_for_status()
                
                # 检查是否被重定向到验证码页面
                if 'captcha' in response.url or 'wappass' in response.url:
                    print(f"警告：查询站点 {site} 时触发验证码，跳过该站点")
                    time.sleep(2)
                    continue
                
                # 解析搜索结果
                soup = BeautifulSoup(response.text, 'html.parser')
                content_left = soup.find('div', id='content_left')
                
                if not content_left:
                    print(f"站点 {site} 未找到搜索结果")
                    continue
                
                result_items = content_left.find_all('div', class_=lambda x: x and ('c-container' in x))
                
                # 提取关键信息
                for item in result_items[:results_per_site]:
                    # 标题
                    title_tag = item.find('h3')
                    title = title_tag.get_text(strip=True) if title_tag else '无标题'
                    
                    # 链接
                    link_tag = item.find('a')
                    link = link_tag['href'] if link_tag and 'href' in link_tag.attrs else '无链接'
                    
                    # 摘要 - 尝试多种选择器
                    abstract = '无摘要'
                    abstract_selectors = ['c-abstract', 'c-span-last', 'c-span']
                    for selector in abstract_selectors:
                        abstract_tag = item.find('div', class_=selector)
                        if abstract_tag:
                            abstract = abstract_tag.get_text(strip=True)
                            break
                    if abstract == '无摘要':
                        # 尝试从整个item中提取文本
                        text_content = item.get_text(' ', strip=True)
                        if text_content and len(text_content) > len(title) + 10:
                            abstract = text_content[:200]
                    
                    # 来源
                    source_tag = item.find('span', class_='c-color-gray')
                    source = source_tag.get_text(strip=True) if source_tag else site
                    
                    results.append({
                        'title': title,
                        'link': link,
                        'abstract': abstract,
                        'source': source,
                        'site': site
                    })
                
                time.sleep(2)  # 增加延迟避免触发验证码
                
            except requests.exceptions.RequestException as e:
                print(f"查询站点 {site} 时出错：{e}")
        
        # 限制返回结果数量
        return results[:num_results]

# ------------------- 测试使用 -------------------
if __name__ == "__main__":
    # 初始化搜索Agent
    search_agent = MultiSiteSearchAgent()
    
    # 示例1：搜索全部站点（CSDN、百度百科、腾讯新闻）
    print("=== 搜索全部站点（Python 进阶教程）===")
    all_results = search_agent.search("Python 进阶教程", num_results=5)
    for idx, res in enumerate(all_results, 1):
        print(f"\n{idx}. 标题：{res['title']}")
        print(f"   链接：{res['link']}")
        print(f"   来源：{res['source']}")
        print(f"   摘要：{res['abstract'][:100]}...")
    
    # 示例2：只搜索CSDN和百度百科
    print("\n=== 只搜索CSDN和百度百科（人工智能 定义）===")
    partial_results = search_agent.search("人工智能 定义", sites=['csdn', 'baike'], num_results=3)
    for idx, res in enumerate(partial_results, 1):
        print(f"\n{idx}. 标题：{res['title']}")
        print(f"   链接：{res['link']}")
        print(f"   来源：{res['source']}")
        print(f"   摘要：{res['abstract'][:100]}...")