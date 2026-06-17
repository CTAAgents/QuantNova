"""
新闻抓取模块

从多个数据源抓取财经新闻和政策公告，支持：
- 财新网（权威财经新闻）
- 新浪财经（实时行情和新闻）
- 央广网（政策解读）
- 东方财富（行业新闻）
- 雪球（市场情绪）

使用方式：
    from fundamental.news_crawler import NewsCrawler
    
    crawler = NewsCrawler()
    news = crawler.crawl(symbol="SC", keywords=["原油", "能源"])
"""

import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta
from typing import Any

import requests

# 导入数据模型
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from trend_scanner.models import NewsEvent

logger = logging.getLogger(__name__)


class NewsSource:
    """新闻源基类"""
    
    def __init__(self, name: str, base_url: str):
        self.name = name
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
    
    def search(self, keywords: list[str], max_results: int = 10) -> list[dict]:
        """
        搜索新闻
        
        Args:
            keywords: 关键词列表
            max_results: 最大结果数
            
        Returns:
            新闻列表
        """
        raise NotImplementedError


class CaixinSource(NewsSource):
    """财新网新闻源"""
    
    def __init__(self):
        super().__init__("财新网", "https://www.caixin.com")
    
    def search(self, keywords: list[str], max_results: int = 10) -> list[dict]:
        """搜索财新网新闻"""
        results = []
        try:
            # 使用财新网搜索API
            search_url = "https://search.caixin.com/search/search.jsp"
            for keyword in keywords[:2]:  # 限制关键词数量
                params = {
                    "keyword": keyword,
                    "pageNum": 1,
                    "pageSize": min(max_results, 5),
                    "sortType": 2,  # 按时间排序
                }
                response = self.session.get(search_url, params=params, timeout=10)
                if response.status_code == 200:
                    # 解析搜索结果（简化处理）
                    data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    if "data" in data:
                        for item in data["data"][:max_results]:
                            results.append({
                                "title": item.get("title", ""),
                                "content": item.get("summary", ""),
                                "url": item.get("url", ""),
                                "source": "财新网",
                                "timestamp": item.get("time", ""),
                            })
        except Exception as e:
            logger.warning(f"财新网搜索失败: {e}")
        return results


class SinaSource(NewsSource):
    """新浪财经新闻源"""
    
    def __init__(self):
        super().__init__("新浪财经", "https://finance.sina.com.cn")
    
    def search(self, keywords: list[str], max_results: int = 10) -> list[dict]:
        """搜索新浪财经新闻"""
        results = []
        try:
            # 使用新浪财经搜索API
            search_url = "https://search.sina.com.cn/news"
            for keyword in keywords[:2]:
                params = {
                    "q": keyword,
                    "c": "news",
                    "sort": "time",
                    "num": min(max_results, 5),
                }
                response = self.session.get(search_url, params=params, timeout=10)
                if response.status_code == 200:
                    # 解析HTML结果（简化处理）
                    content = response.text
                    # 提取新闻标题和链接
                    pattern = r'<h2><a[^>]*href="([^"]*)"[^>]*>(.*?)</a></h2>'
                    matches = re.findall(pattern, content, re.DOTALL)
                    for url, title in matches[:max_results]:
                        results.append({
                            "title": re.sub(r'<[^>]+>', '', title).strip(),
                            "content": "",
                            "url": url,
                            "source": "新浪财经",
                            "timestamp": datetime.now().isoformat(),
                        })
        except Exception as e:
            logger.warning(f"新浪财经搜索失败: {e}")
        return results


class CnrSource(NewsSource):
    """央广网新闻源"""
    
    def __init__(self):
        super().__init__("央广网", "https://www.cnr.cn")
    
    def search(self, keywords: list[str], max_results: int = 10) -> list[dict]:
        """搜索央广网新闻"""
        results = []
        try:
            # 使用央广网搜索API
            search_url = "https://so.cnr.cn/search"
            for keyword in keywords[:2]:
                params = {
                    "keyword": keyword,
                    "page": 1,
                    "pagesize": min(max_results, 5),
                }
                response = self.session.get(search_url, params=params, timeout=10)
                if response.status_code == 200:
                    # 解析搜索结果
                    data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                    if "data" in data:
                        for item in data["data"][:max_results]:
                            results.append({
                                "title": item.get("title", ""),
                                "content": item.get("summary", ""),
                                "url": item.get("url", ""),
                                "source": "央广网",
                                "timestamp": item.get("time", ""),
                            })
        except Exception as e:
            logger.warning(f"央广网搜索失败: {e}")
        return results


class EastmoneySource(NewsSource):
    """东方财富新闻源"""
    
    def __init__(self):
        super().__init__("东方财富", "https://www.eastmoney.com")
    
    def search(self, keywords: list[str], max_results: int = 10) -> list[dict]:
        """搜索东方财富新闻"""
        results = []
        try:
            # 使用东方财富搜索API
            search_url = "https://search-api-web.eastmoney.com/search/jsonp"
            for keyword in keywords[:2]:
                params = {
                    "cb": "jQuery",
                    "param": json.dumps({
                        "uid": "",
                        "keyword": keyword,
                        "type": ["cmsArticleWebOld"],
                        "client": "web",
                        "clientType": "web",
                        "clientVersion": "curr",
                        "param": {
                            "cmsArticleWebOld": {
                                "searchScope": "default",
                                "sort": "default",
                                "pageIndex": 1,
                                "pageSize": min(max_results, 5),
                            }
                        }
                    }),
                }
                response = self.session.get(search_url, params=params, timeout=10)
                if response.status_code == 200:
                    # 解析JSONP响应
                    content = response.text
                    json_str = re.search(r'jQuery\((.*)\)', content)
                    if json_str:
                        data = json.loads(json_str.group(1))
                        if "result" in data:
                            for item in data["result"].get("cmsArticleWebOld", {}).get("list", [])[:max_results]:
                                results.append({
                                    "title": item.get("title", ""),
                                    "content": item.get("content", "")[:200],
                                    "url": item.get("url", ""),
                                    "source": "东方财富",
                                    "timestamp": item.get("date", ""),
                                })
        except Exception as e:
            logger.warning(f"东方财富搜索失败: {e}")
        return results


class XueqiuSource(NewsSource):
    """雪球新闻源"""
    
    def __init__(self):
        super().__init__("雪球", "https://xueqiu.com")
    
    def search(self, keywords: list[str], max_results: int = 10) -> list[dict]:
        """搜索雪球新闻"""
        results = []
        try:
            # 使用雪球搜索API
            search_url = "https://xueqiu.com/query/v1/search/status.json"
            for keyword in keywords[:2]:
                params = {
                    "q": keyword,
                    "count": min(max_results, 5),
                    "sort": "time",
                    "source": "all",
                }
                response = self.session.get(search_url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if "list" in data:
                        for item in data["list"][:max_results]:
                            results.append({
                                "title": item.get("title", "") or item.get("description", "")[:50],
                                "content": item.get("description", ""),
                                "url": f"https://xueqiu.com{item.get('target', '')}",
                                "source": "雪球",
                                "timestamp": datetime.fromtimestamp(item.get("created_at", 0) / 1000).isoformat() if item.get("created_at") else "",
                            })
        except Exception as e:
            logger.warning(f"雪球搜索失败: {e}")
        return results


class NewsCrawler:
    """
    新闻抓取器
    
    从多个数据源抓取财经新闻和政策公告。
    """
    
    # 品种关键词映射
    SYMBOL_KEYWORDS = {
        # 能源
        "SC": ["原油", "石油", "能源", "OPEC", "油价"],
        "FU": ["燃料油", "燃油", "船用燃料"],
        "BU": ["沥青", "道路沥青"],
        "LU": ["低硫燃料油", "船用油"],
        # 化工
        "BZ": ["纯苯", "苯", "化工"],
        "TA": ["PTA", "精对苯二甲酸"],
        "MA": ["甲醇", "醇类"],
        "EG": ["乙二醇", "MEG"],
        "EB": ["苯乙烯", "SM"],
        "PP": ["聚丙烯", "PP"],
        "V": ["PVC", "聚氯乙烯"],
        "L": ["塑料", "LLDPE"],
        # 黑色系
        "RB": ["螺纹钢", "钢材", "建筑钢材"],
        "HC": ["热卷", "热轧卷板"],
        "I": ["铁矿石", "铁矿", "矿石"],
        "J": ["焦炭", "冶金焦"],
        "JM": ["焦煤", "炼焦煤"],
        # 有色金属
        "CU": ["铜", "伦铜", "沪铜"],
        "AL": ["铝", "电解铝"],
        "ZN": ["锌", "沪锌"],
        "NI": ["镍", "沪镍"],
        # 农产品
        "CF": ["棉花", "棉纺"],
        "SR": ["白糖", "食糖"],
        "M": ["豆粕", "大豆"],
        "Y": ["豆油", "食用油"],
        "P": ["棕榈油", "棕油"],
        # 贵金属
        "AU": ["黄金", "金价", "贵金属"],
        "AG": ["白银", "银价"],
    }
    
    # 地缘政治关键词
    GEOPOLITICAL_KEYWORDS = [
        "战争", "冲突", "制裁", "关税", "贸易战", "地缘政治",
        "中东", "俄罗斯", "乌克兰", "伊朗", "美国", "中国",
        "OPEC", "减产", "增产", "石油禁运", "海上封锁",
    ]
    
    # 政策关键词
    POLICY_KEYWORDS = [
        "政策", "监管", "央行", "货币政策", "财政政策",
        "环保", "安全检查", "限产", "产能", "库存",
        "利率", "准备金", "降息", "加息",
    ]
    
    def __init__(self, cache_dir: str = None):
        """
        初始化新闻抓取器
        
        Args:
            cache_dir: 缓存目录
        """
        self.sources = [
            CaixinSource(),
            SinaSource(),
            CnrSource(),
            EastmoneySource(),
            XueqiuSource(),
        ]
        
        # 缓存目录
        self.cache_dir = cache_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "news_cache"
        )
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 已抓取的新闻ID（去重）
        self.crawled_ids = set()
        self._load_crawled_ids()
    
    def _load_crawled_ids(self):
        """加载已抓取的新闻ID"""
        id_file = os.path.join(self.cache_dir, "crawled_ids.json")
        if os.path.exists(id_file):
            try:
                with open(id_file, encoding="utf-8") as f:
                    self.crawled_ids = set(json.load(f))
            except Exception:
                self.crawled_ids = set()
    
    def _save_crawled_ids(self):
        """保存已抓取的新闻ID"""
        id_file = os.path.join(self.cache_dir, "crawled_ids.json")
        try:
            with open(id_file, "w", encoding="utf-8") as f:
                json.dump(list(self.crawled_ids), f)
        except Exception as e:
            logger.warning(f"保存已抓取ID失败: {e}")
    
    def _generate_id(self, title: str, source: str) -> str:
        """生成新闻ID"""
        content = f"{title}_{source}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _is_duplicate(self, title: str, source: str) -> bool:
        """检查是否重复"""
        news_id = self._generate_id(title, source)
        return news_id in self.crawled_ids
    
    def _mark_crawled(self, title: str, source: str):
        """标记为已抓取"""
        news_id = self._generate_id(title, source)
        self.crawled_ids.add(news_id)
    
    def crawl(self, symbol: str = None, keywords: list[str] = None, 
              max_results: int = 20, hours_back: int = 24) -> list[NewsEvent]:
        """
        抓取新闻
        
        Args:
            symbol: 品种代码（可选）
            keywords: 额外关键词（可选）
            max_results: 最大结果数
            hours_back: 抓取最近N小时的新闻
            
        Returns:
            新闻事件列表
        """
        # 构建关键词列表
        search_keywords = []
        
        # 添加品种关键词
        if symbol and symbol in self.SYMBOL_KEYWORDS:
            search_keywords.extend(self.SYMBOL_KEYWORDS[symbol])
        
        # 添加用户关键词
        if keywords:
            search_keywords.extend(keywords)
        
        # 如果没有关键词，使用通用关键词
        if not search_keywords:
            search_keywords = ["期货", "大宗商品", "市场"]
        
        # 限制关键词数量
        search_keywords = search_keywords[:5]
        
        logger.info(f"开始抓取新闻，关键词：{search_keywords}")
        
        # 从各数据源抓取
        all_news = []
        for source in self.sources:
            try:
                news = source.search(search_keywords, max_results=max_results // len(self.sources))
                all_news.extend(news)
                time.sleep(0.5)  # 避免请求过快
            except Exception as e:
                logger.warning(f"从{source.name}抓取失败: {e}")
        
        # 转换为NewsEvent对象
        news_events = []
        for news in all_news:
            # 去重
            if self._is_duplicate(news.get("title", ""), news.get("source", "")):
                continue
            
            # 解析时间
            timestamp = news.get("timestamp", "")
            if not timestamp:
                timestamp = datetime.now().isoformat()
            
            # 判断新闻类别
            category = self._classify_news(news.get("title", ""), news.get("content", ""))
            
            # 判断影响方向
            impact = self._assess_impact(news.get("title", ""), news.get("content", ""))
            
            # 创建NewsEvent对象
            event = NewsEvent(
                event_id=self._generate_id(news.get("title", ""), news.get("source", "")),
                timestamp=timestamp,
                source=news.get("source", ""),
                title=news.get("title", ""),
                content=news.get("content", "")[:200],  # 限制内容长度
                category=category,
                impact=impact,
                keywords=search_keywords,
                affected_symbols=[symbol] if symbol else [],
                confidence=0.7,  # 默认置信度
                url=news.get("url", ""),
            )
            
            news_events.append(event)
            self._mark_crawled(news.get("title", ""), news.get("source", ""))
        
        # 保存已抓取ID
        self._save_crawled_ids()
        
        logger.info(f"抓取完成，共{len(news_events)}条新闻")
        return news_events
    
    def _classify_news(self, title: str, content: str) -> str:
        """
        分类新闻
        
        Args:
            title: 标题
            content: 内容
            
        Returns:
            新闻类别
        """
        text = title + " " + content
        
        # 检查地缘政治关键词
        for keyword in self.GEOPOLITICAL_KEYWORDS:
            if keyword in text:
                return "geopolitical"
        
        # 检查政策关键词
        for keyword in self.POLICY_KEYWORDS:
            if keyword in text:
                return "policy"
        
        # 默认为行业新闻
        return "industry"
    
    def _assess_impact(self, title: str, content: str) -> str:
        """
        评估新闻影响
        
        Args:
            title: 标题
            content: 内容
            
        Returns:
            影响方向
        """
        text = title + " " + content
        
        # 利好关键词
        positive_keywords = ["上涨", "增长", "突破", "利好", "支持", "减产", "限产", "供应紧张"]
        # 利空关键词
        negative_keywords = ["下跌", "下降", "跌破", "利空", "增加", "增产", "供应过剩", "库存增加"]
        
        positive_count = sum(1 for kw in positive_keywords if kw in text)
        negative_count = sum(1 for kw in negative_keywords if kw in text)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"


# 测试代码
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # 测试新闻抓取
    crawler = NewsCrawler()
    
    # 测试原油新闻
    print("=== 测试原油新闻抓取 ===")
    news = crawler.crawl(symbol="SC", max_results=5)
    for event in news:
        print(f"[{event.source}] {event.title}")
        print(f"  类别：{event.category}，影响：{event.impact}")
        print(f"  链接：{event.url}")
        print()
    
    # 测试焦煤新闻
    print("=== 测试焦煤新闻抓取 ===")
    news = crawler.crawl(symbol="JM", max_results=5)
    for event in news:
        print(f"[{event.source}] {event.title}")
        print(f"  类别：{event.category}，影响：{event.impact}")
        print()