"""
基本面分析模块测试

测试新闻抓取、供需数据、地缘政治追踪等功能。
"""

import json
import os
import sys
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

# 添加模块路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))

from trend_scanner.models import (
    FundamentalContext,
    GeopoliticalRisk,
    MarketContext,
    NewsEvent,
    PolicyImpact,
    SupplyDemandData,
)


class TestNewsEvent(unittest.TestCase):
    """测试NewsEvent数据类"""
    
    def test_create_news_event(self):
        """测试创建新闻事件"""
        event = NewsEvent(
            event_id="test_001",
            timestamp=datetime.now().isoformat(),
            source="财新网",
            title="美伊和平协议达成",
            content="美国与伊朗宣布达成和平协议",
            category="geopolitical",
            impact="negative",
            keywords=["美伊", "和平", "协议"],
            affected_symbols=["SC"],
            confidence=0.9,
        )
        
        self.assertEqual(event.event_id, "test_001")
        self.assertEqual(event.source, "财新网")
        self.assertEqual(event.title, "美伊和平协议达成")
        self.assertEqual(event.category, "geopolitical")
        self.assertEqual(event.impact, "negative")
        self.assertIn("SC", event.affected_symbols)
    
    def test_to_dict(self):
        """测试转换为字典"""
        event = NewsEvent(
            event_id="test_001",
            title="测试新闻",
            source="测试",
        )
        
        d = event.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["event_id"], "test_001")
        self.assertEqual(d["title"], "测试新闻")
    
    def test_to_prompt_text(self):
        """测试转换为提示词文本"""
        event = NewsEvent(
            title="美伊和平协议达成",
            source="财新网",
            impact="negative",
        )
        
        text = event.to_prompt_text()
        self.assertIn("财新网", text)
        self.assertIn("美伊和平协议达成", text)
        self.assertIn("利空", text)


class TestSupplyDemandData(unittest.TestCase):
    """测试SupplyDemandData数据类"""
    
    def test_create_supply_demand(self):
        """测试创建供需数据"""
        data = SupplyDemandData(
            symbol="SC",
            timestamp=datetime.now().isoformat(),
            inventory_exchange=1000000,
            inventory_change_pct=-5.0,
            production=500000,
            balance_status="deficit",
        )
        
        self.assertEqual(data.symbol, "SC")
        self.assertEqual(data.inventory_exchange, 1000000)
        self.assertEqual(data.balance_status, "deficit")
    
    def test_to_prompt_text(self):
        """测试转换为提示词文本"""
        data = SupplyDemandData(
            symbol="SC",
            inventory_exchange=1000000,
            inventory_change_pct=-5.0,
            production=500000,
            balance_status="deficit",
        )
        
        text = data.to_prompt_text()
        self.assertIn("交易所库存", text)
        self.assertIn("供不应求", text)


class TestGeopoliticalRisk(unittest.TestCase):
    """测试GeopoliticalRisk数据类"""
    
    def test_create_geopolitical_risk(self):
        """测试创建地缘政治风险"""
        risk = GeopoliticalRisk(
            risk_id="risk_001",
            timestamp=datetime.now().isoformat(),
            region="中东",
            risk_type="peace_agreement",
            risk_level="low",
            affected_commodities=["energy"],
            affected_symbols=["SC"],
            description="美伊和平协议达成",
            impact_analysis="风险溢价消退",
            confidence=0.9,
        )
        
        self.assertEqual(risk.risk_id, "risk_001")
        self.assertEqual(risk.region, "中东")
        self.assertEqual(risk.risk_type, "peace_agreement")
        self.assertEqual(risk.risk_level, "low")
    
    def test_to_prompt_text(self):
        """测试转换为提示词文本"""
        risk = GeopoliticalRisk(
            region="中东",
            risk_type="peace_agreement",
            risk_level="low",
            description="美伊和平协议达成",
        )
        
        text = risk.to_prompt_text()
        self.assertIn("中东", text)
        self.assertIn("和平协议", text)


class TestFundamentalContext(unittest.TestCase):
    """测试FundamentalContext数据类"""
    
    def test_create_fundamental_context(self):
        """测试创建基本面上下文"""
        context = FundamentalContext(
            symbol="SC",
            timestamp=datetime.now().isoformat(),
            news_sentiment="negative",
            news_count=5,
            geopolitical_risk_level="low",
            fundamental_score=-0.3,
            fundamental_direction="bearish",
            key_drivers=["新闻：美伊协议", "供需：供过于求"],
        )
        
        self.assertEqual(context.symbol, "SC")
        self.assertEqual(context.news_sentiment, "negative")
        self.assertEqual(context.fundamental_direction, "bearish")
        self.assertIn("新闻：美伊协议", context.key_drivers)
    
    def test_to_prompt_text_with_data(self):
        """测试有数据时转换为提示词文本"""
        context = FundamentalContext(
            symbol="SC",
            news_events=[
                NewsEvent(title="美伊协议达成", source="财新网", impact="negative"),
            ],
            news_count=1,
            geopolitical_risks=[
                GeopoliticalRisk(region="中东", risk_type="peace_agreement", risk_level="low", description="和平协议"),
            ],
            fundamental_direction="bearish",
            key_drivers=["新闻：美伊协议"],
        )
        
        text = context.to_prompt_text()
        self.assertIn("近期新闻", text)
        self.assertIn("地缘政治风险", text)
        self.assertIn("基本面评估", text)
        self.assertIn("关键驱动", text)
    
    def test_to_prompt_text_empty(self):
        """测试空数据时转换为提示词文本"""
        context = FundamentalContext(symbol="SC")
        
        text = context.to_prompt_text()
        self.assertEqual(text, "暂无基本面数据")


class TestMarketContextWithFundamental(unittest.TestCase):
    """测试包含基本面信息的MarketContext"""
    
    def test_market_context_with_fundamental(self):
        """测试MarketContext包含基本面信息"""
        from trend_scanner.models import IndicatorSnapshot
        
        context = MarketContext(
            symbol="SC",
            timestamp=datetime.now().isoformat(),
            current_price=500.0,
            snapshot=IndicatorSnapshot(
                timestamp=datetime.now().isoformat(),
                close=500.0,
                high=510.0,
                low=490.0,
                open=495.0,
                volume=1000000,
            ),
            fundamental=FundamentalContext(
                symbol="SC",
                news_sentiment="negative",
                fundamental_direction="bearish",
            ),
        )
        
        self.assertEqual(context.symbol, "SC")
        self.assertIsNotNone(context.fundamental)
        self.assertEqual(context.fundamental.fundamental_direction, "bearish")
    
    def test_to_prompt_text_includes_fundamental(self):
        """测试to_prompt_text包含基本面信息"""
        from trend_scanner.models import IndicatorSnapshot
        
        context = MarketContext(
            symbol="SC",
            timestamp=datetime.now().isoformat(),
            current_price=500.0,
            snapshot=IndicatorSnapshot(
                timestamp=datetime.now().isoformat(),
                close=500.0,
                high=510.0,
                low=490.0,
                open=495.0,
                volume=1000000,
            ),
            fundamental=FundamentalContext(
                symbol="SC",
                news_events=[
                    NewsEvent(title="测试新闻", source="测试", impact="negative"),
                ],
                news_count=1,
            ),
        )
        
        text = context.to_prompt_text()
        self.assertIn("基本面信息", text)
        self.assertIn("测试新闻", text)


class TestNewsCrawler(unittest.TestCase):
    """测试NewsCrawler"""
    
    @patch('fundamental.news_crawler.requests.Session')
    def test_crawler_initialization(self, mock_session):
        """测试新闻抓取器初始化"""
        from fundamental.news_crawler import NewsCrawler
        
        crawler = NewsCrawler()
        self.assertIsNotNone(crawler.sources)
        self.assertTrue(len(crawler.sources) > 0)
    
    def test_classify_news(self):
        """测试新闻分类"""
        from fundamental.news_crawler import NewsCrawler
        
        crawler = NewsCrawler()
        
        # 测试地缘政治新闻
        category = crawler._classify_news("美伊战争爆发", "中东地区冲突升级")
        self.assertEqual(category, "geopolitical")
        
        # 测试政策新闻
        category = crawler._classify_news("央行降息", "货币政策调整")
        self.assertEqual(category, "policy")
        
        # 测试行业新闻
        category = crawler._classify_news("原油价格上涨", "市场供需变化")
        self.assertEqual(category, "industry")
    
    def test_assess_impact(self):
        """测试影响评估"""
        from fundamental.news_crawler import NewsCrawler
        
        crawler = NewsCrawler()
        
        # 测试利好新闻
        impact = crawler._assess_impact("价格上涨", "市场增长强劲")
        self.assertEqual(impact, "positive")
        
        # 测试利空新闻
        impact = crawler._assess_impact("价格下跌", "供应过剩库存增加")
        self.assertEqual(impact, "negative")
        
        # 测试中性新闻
        impact = crawler._assess_impact("市场平稳", "交易清淡")
        self.assertEqual(impact, "neutral")


class TestSupplyDemandProvider(unittest.TestCase):
    """测试SupplyDemandProvider"""
    
    def test_provider_initialization(self):
        """测试供需数据提供者初始化"""
        from fundamental.supply_demand import SupplyDemandProvider
        
        provider = SupplyDemandProvider()
        self.assertIsNotNone(provider.sources)
    
    def test_calculate_balance_status(self):
        """测试供需平衡状态计算"""
        from fundamental.supply_demand import SupplyDemandProvider
        
        provider = SupplyDemandProvider()
        
        # 测试供过于求
        data = SupplyDemandData(inventory_change_pct=10)
        status = provider._calculate_balance_status(data)
        self.assertEqual(status, "surplus")
        
        # 测试供不应求
        data = SupplyDemandData(inventory_change_pct=-10)
        status = provider._calculate_balance_status(data)
        self.assertEqual(status, "deficit")
        
        # 测试供需平衡
        data = SupplyDemandData(inventory_change_pct=0)
        status = provider._calculate_balance_status(data)
        self.assertEqual(status, "balanced")


class TestGeopoliticalTracker(unittest.TestCase):
    """测试GeopoliticalTracker"""
    
    def test_tracker_initialization(self):
        """测试地缘政治追踪器初始化"""
        from fundamental.geopolitical import GeopoliticalTracker
        
        tracker = GeopoliticalTracker()
        self.assertIsNotNone(tracker.REGION_SYMBOL_MAP)
        self.assertIsNotNone(tracker.RISK_TYPE_IMPACT)
    
    def test_identify_risk_type(self):
        """测试风险类型识别"""
        from fundamental.geopolitical import GeopoliticalTracker
        
        tracker = GeopoliticalTracker()
        
        # 测试战争风险
        risk_type = tracker._identify_risk_type("战争爆发，军事冲突升级")
        self.assertEqual(risk_type, "war")
        
        # 测试和平协议
        risk_type = tracker._identify_risk_type("和平协议达成，谈判成功")
        self.assertEqual(risk_type, "peace_agreement")
        
        # 测试制裁风险
        risk_type = tracker._identify_risk_type("实施制裁，封锁海上通道")
        self.assertEqual(risk_type, "sanctions")
    
    def test_identify_region(self):
        """测试地区识别"""
        from fundamental.geopolitical import GeopoliticalTracker
        
        tracker = GeopoliticalTracker()
        
        # 测试中东地区
        region = tracker._identify_region("伊朗宣布石油禁运")
        self.assertEqual(region, "中东")
        
        # 测试俄罗斯
        region = tracker._identify_region("乌克兰局势紧张")
        self.assertEqual(region, "俄罗斯")
    
    def test_determine_risk_level(self):
        """测试风险等级确定"""
        from fundamental.geopolitical import GeopoliticalTracker
        
        tracker = GeopoliticalTracker()
        
        # 测试高风险
        level = tracker._determine_risk_level("war", "全面战争爆发")
        self.assertEqual(level, "high")
        
        # 测试中风险
        level = tracker._determine_risk_level("sanctions", "实施经济制裁")
        self.assertEqual(level, "medium")
        
        # 测试低风险
        level = tracker._determine_risk_level("peace_agreement", "和平协议")
        self.assertEqual(level, "low")
    
    def test_get_affected_symbols(self):
        """测试获取受影响品种"""
        from fundamental.geopolitical import GeopoliticalTracker
        
        tracker = GeopoliticalTracker()
        
        # 测试中东地区
        symbols = tracker._get_affected_symbols("中东", "war")
        self.assertIn("SC", symbols)
        self.assertIn("AU", symbols)
    
    def test_analyze_news(self):
        """测试从新闻中分析地缘政治风险"""
        from fundamental.geopolitical import GeopoliticalTracker
        
        tracker = GeopoliticalTracker()
        
        # 创建测试新闻
        news_events = [
            NewsEvent(
                event_id="test_001",
                timestamp=datetime.now().isoformat(),
                source="测试",
                title="美伊和平协议达成",
                content="美国与伊朗宣布达成和平协议，双方停止军事行动",
                category="geopolitical",
                impact="negative",
                keywords=["美伊", "和平", "协议"],
                affected_symbols=["SC"],
                confidence=0.9,
            ),
        ]
        
        risks = tracker.analyze_news(news_events)
        self.assertTrue(len(risks) > 0)
        
        risk = risks[0]
        self.assertEqual(risk.risk_type, "peace_agreement")
        self.assertIn("SC", risk.affected_symbols)


class TestContextAssemblerWithFundamental(unittest.TestCase):
    """测试包含基本面信息的ContextAssembler"""
    
    @patch('fundamental.news_crawler.NewsCrawler.crawl')
    @patch('fundamental.supply_demand.SupplyDemandProvider.get_supply_demand')
    @patch('fundamental.geopolitical.GeopoliticalTracker.track')
    def test_assemble_fundamental(self, mock_track, mock_supply, mock_crawl):
        """测试基本面信息组装"""
        from trend_scanner.context import ContextAssembler
        
        # 模拟返回值
        mock_crawl.return_value = [
            NewsEvent(title="测试新闻", source="测试", impact="negative"),
        ]
        mock_supply.return_value = SupplyDemandData(
            symbol="SC",
            balance_status="deficit",
        )
        mock_track.return_value = [
            GeopoliticalRisk(
                region="中东",
                risk_type="peace_agreement",
                risk_level="low",
                description="和平协议",
            ),
        ]
        
        assembler = ContextAssembler(symbol="SC")
        fundamental = assembler._assemble_fundamental()
        
        self.assertEqual(fundamental.symbol, "SC")
        self.assertTrue(len(fundamental.news_events) > 0)
        self.assertEqual(fundamental.supply_demand.balance_status, "deficit")
        self.assertTrue(len(fundamental.geopolitical_risks) > 0)


class TestReasoningWithFundamental(unittest.TestCase):
    """测试包含基本面信息的推理"""
    
    def test_build_user_prompt_with_fundamental(self):
        """测试构建包含基本面信息的用户提示词"""
        from trend_scanner.reasoning import ReasoningEngine
        from trend_scanner.models import IndicatorSnapshot
        
        engine = ReasoningEngine()
        
        # 创建包含基本面信息的MarketContext
        context = MarketContext(
            symbol="SC",
            timestamp=datetime.now().isoformat(),
            current_price=500.0,
            snapshot=IndicatorSnapshot(
                timestamp=datetime.now().isoformat(),
                close=500.0,
                high=510.0,
                low=490.0,
                open=495.0,
                volume=1000000,
            ),
            fundamental=FundamentalContext(
                symbol="SC",
                news_events=[
                    NewsEvent(title="美伊协议达成", source="财新网", impact="negative"),
                ],
                news_count=1,
                geopolitical_risks=[
                    GeopoliticalRisk(
                        region="中东",
                        risk_type="peace_agreement",
                        risk_level="low",
                        description="和平协议",
                    ),
                ],
                geopolitical_risk_level="low",
                fundamental_direction="bearish",
            ),
        )
        
        # 构建提示词
        prompt = engine._build_user_prompt(
            context=context,
            similar_experiences=[],
            experience_aggregation={},
        )
        
        # 验证包含基本面信息
        self.assertIn("基本面信息", prompt)
        self.assertIn("美伊协议达成", prompt)
        self.assertIn("地缘政治风险", prompt)


if __name__ == "__main__":
    unittest.main()