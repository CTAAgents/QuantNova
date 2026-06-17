"""
基本面分析模块（v1.0）

提供新闻抓取、供需数据、地缘政治风险评估等功能。
"""

from .news_crawler import NewsCrawler
from .supply_demand import SupplyDemandProvider
from .geopolitical import GeopoliticalTracker

__all__ = ["NewsCrawler", "SupplyDemandProvider", "GeopoliticalTracker"]