#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import re
import time
import random
from urllib.parse import quote, urlencode

class BaseScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        self.timeout = 15
        
    def fetch_page(self, url, delay=1):
        time.sleep(delay + random.uniform(0, 1))
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            return response.text
        except requests.RequestException as e:
            return None

    def extract_price(self, text):
        price_patterns = [
            r'¥(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'￥(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'price["\s:]+["\']?(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
            r'"price"\s*:\s*["\']?(\d+(?:,\d{3})*(?:\.\d{1,2})?)',
        ]
        for pattern in price_patterns:
            match = re.search(pattern, text)
            if match:
                price_str = match.group(1).replace(',', '')
                try:
                    return float(price_str)
                except ValueError:
                    continue
        return None

class JDScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = 'jd'
        self.display_name = '京东商城'
        self.base_url = 'https://search.jd.com/Search'
        
    def build_url(self, keyword):
        params = {
            'keyword': keyword,
            'enc': 'utf-8',
            'wq': keyword,
        }
        return f"{self.base_url}?{urlencode(params)}"
    
    def scrape(self, keyword):
        url = self.build_url(keyword)
        html = self.fetch_page(url, delay=2)
        if not html:
            return {'success': False, 'prices': [], 'source': self.display_name}
        
        soup = BeautifulSoup(html, 'html.parser')
        prices = []
        
        for item in soup.select('.gl-item'):
            try:
                price_elem = item.select_one('.p-price strong i')
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    price = float(price_text.replace(',', ''))
                    
                    title_elem = item.select_one('.p-name em')
                    title = title_elem.get_text(strip=True) if title_elem else ''
                    
                    detail_url = item.select_one('a')
                    product_url = 'https:' + detail_url.get('href', '') if detail_url else ''
                    
                    prices.append({
                        'price': price,
                        'title': title[:100] if title else '',
                        'url': product_url
                    })
            except (ValueError, AttributeError):
                continue
        
        for script in soup.find_all('script'):
            script_text = str(script)
            price = self.extract_price(script_text)
            if price and price > 0:
                title_match = re.search(r'"wareId"\s*:\s*"(\d+)"', script_text)
                if title_match:
                    title = f"商品ID: {title_match.group(1)}"
                    product_url = f"https://item.jd.com/{title_match.group(1)}.html"
                    if not any(p['price'] == price for p in prices):
                        prices.append({
                            'price': price,
                            'title': title,
                            'url': product_url
                        })
        
        return {
            'success': len(prices) > 0,
            'prices': sorted(prices, key=lambda x: x['price'])[:5],
            'source': self.display_name,
            'url': url
        }

class AlibabaScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = 'alibaba'
        self.display_name = '阿里巴巴'
        self.base_url = 'https://s.1688.com/jofferSearch'
        
    def build_url(self, keyword):
        params = {
            'keywords': keyword,
            'n': 'y',
            'n': 'y',
            'v': 'p',
        }
        return f"{self.base_url}?{urlencode(params)}"
    
    def scrape(self, keyword):
        url = self.build_url(keyword)
        html = self.fetch_page(url, delay=2)
        if not html:
            return {'success': False, 'prices': [], 'source': self.display_name}
        
        soup = BeautifulSoup(html, 'html.parser')
        prices = []
        
        for item in soup.select('.offer-list .offer-item'):
            try:
                price_elem = item.select_one('.price .value')
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    price = float(price_text.replace(',', ''))
                    
                    title_elem = item.select_one('.title .name')
                    title = title_elem.get_text(strip=True) if title_elem else ''
                    
                    detail_url = item.select_one('a')
                    product_url = detail_url.get('href', '') if detail_url else ''
                    
                    prices.append({
                        'price': price,
                        'title': title[:100] if title else '',
                        'url': product_url
                    })
            except (ValueError, AttributeError):
                continue
        
        json_pattern = r'window\.__SEED_DATA__\s*=\s*({.*?});'
        match = re.search(json_pattern, html, re.DOTALL)
        if match:
            import json
            try:
                data = json.loads(match.group(1))
                for offer in data.get('offers', [])[:5]:
                    price = offer.get('price', {})
                    if isinstance(price, dict):
                        price_val = float(price.get('value', 0))
                    else:
                        price_val = float(price)
                    if price_val > 0:
                        product_url = offer.get('productUrl', '')
                        title = offer.get('title', '')
                        if not any(p['price'] == price_val for p in prices):
                            prices.append({
                                'price': price_val,
                                'title': title[:100] if title else '',
                                'url': product_url
                            })
            except (json.JSONDecodeError, ValueError, KeyError):
                pass
        
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, list):
                    for item in data[:5]:
                        if item.get('@type') == 'Product':
                            offers = item.get('offers', {})
                            price = float(offers.get('price', 0))
                            if price > 0:
                                url = item.get('url', '')
                                title = item.get('name', '')
                                prices.append({
                                    'price': price,
                                    'title': title[:100] if title else '',
                                    'url': url
                                })
            except (json.JSONDecodeError, ValueError, KeyError, AttributeError):
                continue
        
        return {
            'success': len(prices) > 0,
            'prices': sorted(prices, key=lambda x: x['price'])[:5],
            'source': self.display_name,
            'url': url
        }

class TaobaoScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = 'taobao'
        self.display_name = '淘宝'
        self.base_url = 'https://s.taobao.com/search'
        
    def build_url(self, keyword):
        params = {
            'q': keyword,
            'sort': 'price-asc',
        }
        return f"{self.base_url}?{urlencode(params)}"
    
    def scrape(self, keyword):
        url = self.build_url(keyword)
        html = self.fetch_page(url, delay=2)
        if not html:
            return {'success': False, 'prices': [], 'source': self.display_name}
        
        soup = BeautifulSoup(html, 'html.parser')
        prices = []
        
        for item in soup.select('.item'):
            try:
                price_elem = item.select_one('.price')
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    price_match = re.search(r'(\d+\.?\d*)', price_text)
                    if price_match:
                        price = float(price_match.group(1))
                        
                        title_elem = item.select_one('.title')
                        title = title_elem.get_text(strip=True) if title_elem else ''
                        
                        detail_url = item.select_one('a')
                        product_url = detail_url.get('href', '') if detail_url else ''
                        if product_url and not product_url.startswith('http'):
                            product_url = 'https:' + product_url
                        
                        prices.append({
                            'price': price,
                            'title': title[:100] if title else '',
                            'url': product_url
                        })
            except (ValueError, AttributeError):
                continue
        
        g_page_config_match = re.search(r'g_page_config\s*=\s*({.*?})\s*;?\s*(?:var|$)', html, re.DOTALL)
        if g_page_config_match:
            import json
            try:
                config = json.loads(g_page_config_match.group(1))
                auctions = config.get('mods', {}).get('itemlist', {}).get('data', {}).get('auctions', [])
                for item in auctions[:5]:
                    price = float(item.get('view_price', 0))
                    if price > 0:
                        title = item.get('title', '')
                        product_url = item.get('detail_url', '')
                        if product_url and not product_url.startswith('http'):
                            product_url = 'https:' + product_url
                        if not any(p['price'] == price for p in prices):
                            prices.append({
                                'price': price,
                                'title': title[:100] if title else '',
                                'url': product_url
                            })
            except (json.JSONDecodeError, ValueError, KeyError):
                pass
        
        return {
            'success': len(prices) > 0,
            'prices': sorted(prices, key=lambda x: x['price'])[:5],
            'source': self.display_name,
            'url': url
        }

class BaiduScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = 'baidu'
        self.display_name = '百度爱采购'
        self.base_url = 'https://b2b.baidu.com/s'
        
    def build_url(self, keyword):
        params = {
            'q': keyword,
            'p': 'price',
        }
        return f"{self.base_url}?{urlencode(params)}"
    
    def scrape(self, keyword):
        url = self.build_url(keyword)
        html = self.fetch_page(url, delay=2)
        if not html:
            return {'success': False, 'prices': [], 'source': self.display_name}
        
        soup = BeautifulSoup(html, 'html.parser')
        prices = []
        
        for item in soup.select('.result-item, .b2b-item'):
            try:
                price_elem = item.select_one('.price, .item-price')
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    price_match = re.search(r'[\d,]+\.?\d*', price_text)
                    if price_match:
                        price = float(price_match.group().replace(',', ''))
                        
                        title_elem = item.select_one('.title, .name')
                        title = title_elem.get_text(strip=True) if title_elem else ''
                        
                        detail_url = item.select_one('a')
                        product_url = detail_url.get('href', '') if detail_url else ''
                        if product_url and not product_url.startswith('http'):
                            product_url = 'https://b2b.baidu.com' + product_url
                        
                        prices.append({
                            'price': price,
                            'title': title[:100] if title else '',
                            'url': product_url
                        })
            except (ValueError, AttributeError):
                continue
        
        return {
            'success': len(prices) > 0,
            'prices': sorted(prices, key=lambda x: x['price'])[:5],
            'source': self.display_name,
            'url': url
        }

def get_scraper(source_type):
    scrapers = {
        'jd': JDScraper,
        'alibaba': AlibabaScraper,
        'taobao': TaobaoScraper,
        'baidu': BaiduScraper,
    }
    scraper_class = scrapers.get(source_type.lower())
    if scraper_class:
        return scraper_class()
    return None

def scrape_all_sources(keyword):
    results = []
    sources = ['jd', 'alibaba', 'taobao']
    
    for source in sources:
        scraper = get_scraper(source)
        if scraper:
            try:
                result = scraper.scrape(keyword)
                results.append(result)
            except Exception as e:
                results.append({
                    'success': False,
                    'prices': [],
                    'source': scraper.display_name,
                    'error': str(e)
                })
            time.sleep(1)
    
    return results

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        keyword = sys.argv[1]
        print(f"正在搜索: {keyword}\n")
        results = scrape_all_sources(keyword)
        for result in results:
            print(f"【{result['source']}】")
            if result['success']:
                for item in result['prices'][:3]:
                    print(f"  ¥{item['price']:,.2f} - {item['title']}")
                    print(f"  URL: {item['url']}")
            else:
                print(f"  抓取失败")
            print()
    else:
        print("用法: python scrapers.py <关键词>")