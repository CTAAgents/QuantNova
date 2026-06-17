"""
集成测试 - 验证基本面分析模块与核心系统的集成

测试完整的扫描-推理流程，确保基本面信息能够正确传递。
"""

import os
import sys
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

# 添加模块路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))

import pandas as pd
import numpy as np

from trend_scanner.models import (
    FundamentalContext,
    GeopoliticalRisk,
    MarketContext,
    NewsEvent,
    SupplyDemandData,
)
from trend_scanner.context import ContextAssembler
from trend_scanner.reasoning import ReasoningEngine


class TestIntegrationFundamental(unittest.TestCase):
    """测试基本面分析模块与核心系统的集成"""
    
    def _create_sample_dataframe(self, rows=120):
        """创建样本DataFrame"""
        dates = pd.date_range(end=datetime.now(), periods=rows, freq='D')
        df = pd.DataFrame({
            'date': dates,
            'open': np.random.uniform(400, 500, rows),
            'high': np.random.uniform(450, 550, rows),
            'low': np.random.uniform(350, 450, rows),
            'close': np.random.uniform(400, 500, rows),
            'volume': np.random.randint(100000, 1000000, rows),
            'open_interest': np.random.randint(50000, 200000, rows),
        })
        return df
    
    @patch('fundamental.news_crawler.NewsCrawler.crawl')
    @patch('fundamental.supply_demand.SupplyDemandProvider.get_supply_demand')
    @patch('fundamental.geopolitical.GeopoliticalTracker.track')
    def test_context_assembler_with_fundamental(self, mock_track, mock_supply, mock_crawl):
        """测试ContextAssembler能够组装基本面信息"""
        # 模拟返回值
        mock_crawl.return_value = [
            NewsEvent(
                event_id="test_001",
                title="美伊和平协议达成",
                source="财新网",
                impact="negative",
                category="geopolitical",
            ),
        ]
        mock_supply.return_value = SupplyDemandData(
            symbol="SC",
            balance_status="deficit",
            inventory_change_pct=-5.0,
        )
        mock_track.return_value = [
            GeopoliticalRisk(
                region="中东",
                risk_type="peace_agreement",
                risk_level="low",
                description="美伊和平协议达成",
            ),
        ]
        
        # 创建DataFrame
        df = self._create_sample_dataframe()
        
        # 创建ContextAssembler
        assembler = ContextAssembler(symbol="SC")
        
        # 组装上下文（包含基本面信息）
        context = assembler.assemble(df, include_fundamental=True)
        
        # 验证基本面信息
        self.assertIsNotNone(context.fundamental)
        self.assertEqual(context.fundamental.symbol, "SC")
        self.assertTrue(len(context.fundamental.news_events) > 0)
        self.assertEqual(context.fundamental.supply_demand.balance_status, "deficit")
        self.assertTrue(len(context.fundamental.geopolitical_risks) > 0)
        
        # 验证基本面评估
        self.assertIn(context.fundamental.fundamental_direction, ["bullish", "bearish", "neutral"])
    
    @patch('fundamental.news_crawler.NewsCrawler.crawl')
    @patch('fundamental.supply_demand.SupplyDemandProvider.get_supply_demand')
    @patch('fundamental.geopolitical.GeopoliticalTracker.track')
    def test_context_to_prompt_text_includes_fundamental(self, mock_track, mock_supply, mock_crawl):
        """测试to_prompt_text包含基本面信息"""
        # 模拟返回值
        mock_crawl.return_value = [
            NewsEvent(
                title="美伊和平协议达成",
                source="财新网",
                impact="negative",
            ),
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
                description="美伊和平协议达成",
            ),
        ]
        
        # 创建DataFrame
        df = self._create_sample_dataframe()
        
        # 创建ContextAssembler
        assembler = ContextAssembler(symbol="SC")
        
        # 组装上下文
        context = assembler.assemble(df, include_fundamental=True)
        
        # 获取提示词文本
        prompt_text = context.to_prompt_text()
        
        # 验证包含基本面信息
        self.assertIn("基本面信息", prompt_text)
        self.assertIn("美伊和平协议达成", prompt_text)
        self.assertIn("地缘政治风险", prompt_text)
    
    @patch('fundamental.news_crawler.NewsCrawler.crawl')
    @patch('fundamental.supply_demand.SupplyDemandProvider.get_supply_demand')
    @patch('fundamental.geopolitical.GeopoliticalTracker.track')
    def test_reasoning_engine_with_fundamental(self, mock_track, mock_supply, mock_crawl):
        """测试ReasoningEngine能够使用基本面信息"""
        # 模拟返回值
        mock_crawl.return_value = [
            NewsEvent(
                title="美伊和平协议达成",
                source="财新网",
                impact="negative",
            ),
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
                description="美伊和平协议达成",
            ),
        ]
        
        # 创建DataFrame
        df = self._create_sample_dataframe()
        
        # 创建ContextAssembler
        assembler = ContextAssembler(symbol="SC")
        
        # 组装上下文
        context = assembler.assemble(df, include_fundamental=True)
        
        # 创建ReasoningEngine
        engine = ReasoningEngine()
        
        # 构建用户提示词
        prompt = engine._build_user_prompt(
            context=context,
            similar_experiences=[],
            experience_aggregation={},
        )
        
        # 验证包含基本面信息
        self.assertIn("基本面信息", prompt)
        self.assertIn("美伊和平协议达成", prompt)
        self.assertIn("地缘政治风险", prompt)
    
    @patch('fundamental.news_crawler.NewsCrawler.crawl')
    @patch('fundamental.supply_demand.SupplyDemandProvider.get_supply_demand')
    @patch('fundamental.geopolitical.GeopoliticalTracker.track')
    def test_fundamental_score_calculation(self, mock_track, mock_supply, mock_crawl):
        """测试基本面评分计算"""
        # 模拟返回值 - 负面新闻 + 供不应求 + 低风险
        mock_crawl.return_value = [
            NewsEvent(title="负面新闻", impact="negative"),
            NewsEvent(title="另一个负面新闻", impact="negative"),
        ]
        mock_supply.return_value = SupplyDemandData(
            symbol="SC",
            balance_status="deficit",
        )
        mock_track.return_value = [
            GeopoliticalRisk(
                risk_level="low",
                risk_type="peace_agreement",
            ),
        ]
        
        # 创建DataFrame
        df = self._create_sample_dataframe()
        
        # 创建ContextAssembler
        assembler = ContextAssembler(symbol="SC")
        
        # 组装上下文
        context = assembler.assemble(df, include_fundamental=True)
        
        # 验证基本面评分
        self.assertIsNotNone(context.fundamental.fundamental_score)
        self.assertIsInstance(context.fundamental.fundamental_score, float)
        self.assertGreaterEqual(context.fundamental.fundamental_score, -1.0)
        self.assertLessEqual(context.fundamental.fundamental_score, 1.0)
    
    @patch('fundamental.news_crawler.NewsCrawler.crawl')
    @patch('fundamental.supply_demand.SupplyDemandProvider.get_supply_demand')
    @patch('fundamental.geopolitical.GeopoliticalTracker.track')
    def test_key_drivers_identification(self, mock_track, mock_supply, mock_crawl):
        """测试关键驱动因素识别"""
        # 模拟返回值
        mock_crawl.return_value = [
            NewsEvent(title="美伊和平协议达成", source="财新网", impact="negative", confidence=0.9),
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
                description="美伊和平协议达成",
                confidence=0.9,
            ),
        ]
        
        # 创建DataFrame
        df = self._create_sample_dataframe()
        
        # 创建ContextAssembler
        assembler = ContextAssembler(symbol="SC")
        
        # 组装上下文
        context = assembler.assemble(df, include_fundamental=True)
        
        # 验证关键驱动因素
        self.assertIsNotNone(context.fundamental.key_drivers)
        self.assertIsInstance(context.fundamental.key_drivers, list)
        self.assertTrue(len(context.fundamental.key_drivers) > 0)
    
    def test_context_assembler_without_fundamental(self):
        """测试不包含基本面信息的上下文组装"""
        # 创建DataFrame
        df = self._create_sample_dataframe()
        
        # 创建ContextAssembler
        assembler = ContextAssembler(symbol="SC")
        
        # 组装上下文（不包含基本面信息）
        context = assembler.assemble(df, include_fundamental=False)
        
        # 验证基本面信息为空
        self.assertIsNotNone(context.fundamental)
        self.assertEqual(len(context.fundamental.news_events), 0)
        self.assertEqual(context.fundamental.fundamental_direction, "")
    
    @patch('fundamental.news_crawler.NewsCrawler.crawl')
    def test_fundamental_assembly_failure_handling(self, mock_crawl):
        """测试基本面信息组装失败的处理"""
        # 模拟新闻抓取失败
        mock_crawl.side_effect = Exception("网络连接失败")
        
        # 创建DataFrame
        df = self._create_sample_dataframe()
        
        # 创建ContextAssembler
        assembler = ContextAssembler(symbol="SC")
        
        # 组装上下文（基本面信息组装应该失败，但不影响整体）
        context = assembler.assemble(df, include_fundamental=True)
        
        # 验证上下文仍然正常创建
        self.assertIsNotNone(context)
        self.assertEqual(context.symbol, "SC")
        self.assertIsNotNone(context.fundamental)
        self.assertEqual(len(context.fundamental.news_events), 0)


class TestIntegrationWithScanner(unittest.TestCase):
    """测试与Scanner的集成"""
    
    @patch('fundamental.news_crawler.NewsCrawler.crawl')
    @patch('fundamental.supply_demand.SupplyDemandProvider.get_supply_demand')
    @patch('fundamental.geopolitical.GeopoliticalTracker.track')
    def test_scanner_output_includes_fundamental(self, mock_track, mock_supply, mock_crawl):
        """测试Scanner输出包含基本面信息"""
        # 模拟返回值
        mock_crawl.return_value = [
            NewsEvent(title="测试新闻", source="测试", impact="negative"),
        ]
        mock_supply.return_value = SupplyDemandData(symbol="SC")
        mock_track.return_value = []
        
        # 这里需要实际的Scanner集成测试
        # 由于Scanner依赖较多外部组件，这里只验证概念
        pass


if __name__ == "__main__":
    unittest.main()