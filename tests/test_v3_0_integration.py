"""
V3.0 方案集成测试

测试基于 V3.0 方案的新模块：
- DataConflictResolver
- AnomalyWeighter
- HallucinationDetector
- AdaptivePromptRouter
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "scripts"))

from data.conflict_resolver import DataConflictResolver, DataPoint, DataCredibility
from data.anomaly_weighter import AnomalyWeighter, AnomalyType, AnomalyResult
from reasoning.hallucination_detector import HallucinationDetector, HallucinationType
from reasoning.adaptive_prompt_router import AdaptivePromptRouter, PromptTemplateType


class TestDataConflictResolver:
    """数据冲突裁决引擎测试"""
    
    def test_init(self):
        """测试初始化"""
        resolver = DataConflictResolver()
        assert resolver.conflict_threshold == 0.05
    
    def test_resolve_single_source(self):
        """测试单数据源"""
        resolver = DataConflictResolver()
        
        data_points = [
            DataPoint(
                value=3500.0,
                source="交易所",
                credibility=DataCredibility.LEVEL_1,
                timestamp="2026-06-18",
                data_type="price"
            )
        ]
        
        result = resolver.resolve(data_points)
        
        assert not result.has_conflict
        assert result.resolved_value == 3500.0
        assert result.resolution_method == "single_source"
    
    def test_resolve_no_conflict(self):
        """测试无冲突多数据源"""
        resolver = DataConflictResolver()
        
        data_points = [
            DataPoint(
                value=3500.0,
                source="交易所",
                credibility=DataCredibility.LEVEL_1,
                timestamp="2026-06-18",
                data_type="price"
            ),
            DataPoint(
                value=3510.0,
                source="Wind",
                credibility=DataCredibility.LEVEL_3,
                timestamp="2026-06-18",
                data_type="price"
            ),
        ]
        
        result = resolver.resolve(data_points)
        
        assert not result.has_conflict
        assert result.resolution_method == "weighted_average"
    
    def test_resolve_with_conflict(self):
        """测试有冲突数据源"""
        resolver = DataConflictResolver(conflict_threshold=0.01)  # 1%阈值
        
        data_points = [
            DataPoint(
                value=3500.0,
                source="交易所",
                credibility=DataCredibility.LEVEL_1,
                timestamp="2026-06-18",
                data_type="price"
            ),
            DataPoint(
                value=3600.0,
                source="自媒体",
                credibility=DataCredibility.LEVEL_4,
                timestamp="2026-06-18",
                data_type="price"
            ),
        ]
        
        result = resolver.resolve(data_points)
        
        assert result.has_conflict
        assert result.resolved_value == 3500.0  # 应该选择高可信度数据
        assert result.resolution_method == "credibility_weighted"


class TestAnomalyWeighter:
    """异常值分层加权测试"""
    
    def test_init(self):
        """测试初始化"""
        weighter = AnomalyWeighter()
        assert weighter.price_change_threshold == 0.05
    
    def test_detect_normal(self):
        """测试正常数据检测"""
        weighter = AnomalyWeighter()
        
        np.random.seed(42)
        dates = pd.date_range("2026-01-01", periods=100)
        df = pd.DataFrame({
            "open": np.random.randn(100) + 100,
            "high": np.random.randn(100) + 101,
            "low": np.random.randn(100) + 99,
            "close": np.random.randn(100) + 100,
            "volume": np.random.randint(1000, 5000, 100),
        }, index=dates)
        
        result = weighter.detect(df, 50)
        
        assert result.anomaly_type == AnomalyType.NORMAL
        assert not result.is_anomaly
    
    def test_detect_institutional(self):
        """测试制度性异常检测（涨跌停）"""
        weighter = AnomalyWeighter()
        
        # 创建包含涨跌停的数据（直接从idx=1开始检测）
        dates = pd.date_range("2026-01-01", periods=10)
        df = pd.DataFrame({
            "open": [100, 111, 102, 103, 104, 105, 106, 107, 108, 109],
            "high": [101, 112, 103, 104, 105, 106, 107, 108, 109, 110],
            "low": [99, 109, 101, 102, 103, 104, 105, 106, 107, 108],
            "close": [100, 111, 102, 103, 104, 105, 106, 107, 108, 109],  # 第二天涨停10%
            "volume": [1000] * 10,
        }, index=dates)
        
        result = weighter.detect(df, 1)  # 检测第二天
        
        assert result.anomaly_type == AnomalyType.INSTITUTIONAL
        assert result.is_anomaly
        assert result.weight_factor == 0.5
    
    def test_batch_detect(self):
        """测试批量检测"""
        weighter = AnomalyWeighter()
        
        np.random.seed(42)
        dates = pd.date_range("2026-01-01", periods=100)
        df = pd.DataFrame({
            "open": np.random.randn(100) + 100,
            "high": np.random.randn(100) + 101,
            "low": np.random.randn(100) + 99,
            "close": np.random.randn(100) + 100,
            "volume": np.random.randint(1000, 5000, 100),
        }, index=dates)
        
        results = weighter.batch_detect(df)
        
        assert len(results) == 100
        assert all(isinstance(r, AnomalyResult) for r in results)


class TestHallucinationDetector:
    """幻觉检测器测试"""
    
    def test_init(self):
        """测试初始化"""
        detector = HallucinationDetector()
        assert detector is not None
    
    def test_check_no_hallucination(self):
        """测试无幻觉检测"""
        detector = HallucinationDetector()
        
        text = "基于技术分析，螺纹钢当前处于上升趋势，RSI指标为65，处于正常区间。"
        results = detector.check(text)
        
        assert len(results) == 0
    
    def test_check_certainty_claim(self):
        """测试确定性结论检测"""
        detector = HallucinationDetector()
        
        text = "螺纹钢必然上涨100%，这是绝对的。"
        results = detector.check(text)
        
        certainty_results = [r for r in results if r.hallucination_type == HallucinationType.CERTAINTY_CLAIM]
        assert len(certainty_results) > 0
    
    def test_check_low_credibility(self):
        """测试低可信度数据标注检测"""
        detector = HallucinationDetector()
        
        text = "根据股吧消息，螺纹钢将大涨。"
        results = detector.check(text)
        
        credibility_results = [r for r in results if r.hallucination_type == HallucinationType.LOW_CREDIBILITY]
        assert len(credibility_results) > 0


class TestAdaptivePromptRouter:
    """自适应Prompt路由器测试"""
    
    def test_init(self):
        """测试初始化"""
        router = AdaptivePromptRouter()
        assert len(router.templates) == 3
    
    def test_route_minimal(self):
        """测试极简模板路由"""
        router = AdaptivePromptRouter()
        
        query = "解读螺纹钢的技术指标"
        template = router.route(query)
        
        assert template.template_type == PromptTemplateType.MINIMAL
    
    def test_route_standard(self):
        """测试标准模板路由"""
        router = AdaptivePromptRouter()
        
        query = "分析螺纹钢日线行情"
        template = router.route(query)
        
        assert template.template_type == PromptTemplateType.STANDARD
    
    def test_route_deep(self):
        """测试深度模板路由"""
        router = AdaptivePromptRouter()
        
        query = "重仓研判螺纹钢，需要对冲分析"
        template = router.route(query)
        
        assert template.template_type == PromptTemplateType.DEEP
    
    def test_assemble_prompt(self):
        """测试Prompt组装"""
        router = AdaptivePromptRouter()
        
        template = router.templates[PromptTemplateType.STANDARD]
        prompt = router.assemble_prompt(
            template=template,
            query="分析螺纹钢行情",
            data_context="当前价格3500，RSI=65"
        )
        
        assert "系统角色" in prompt
        assert "约束条件" in prompt
        assert "数据上下文" in prompt
        assert "分析要求" in prompt


class TestIntegration:
    """集成测试"""
    
    def test_full_workflow(self):
        """测试完整工作流"""
        # 1. 数据冲突裁决
        resolver = DataConflictResolver()
        data_points = [
            DataPoint(3500, "交易所", DataCredibility.LEVEL_1, "2026-06-18", "price"),
            DataPoint(3510, "Wind", DataCredibility.LEVEL_3, "2026-06-18", "price"),
        ]
        conflict_result = resolver.resolve(data_points)
        
        # 2. 异常值检测
        weighter = AnomalyWeighter()
        np.random.seed(42)
        dates = pd.date_range("2026-01-01", periods=100)
        df = pd.DataFrame({
            "open": np.random.randn(100) + 100,
            "high": np.random.randn(100) + 101,
            "low": np.random.randn(100) + 99,
            "close": np.random.randn(100) + 100,
            "volume": np.random.randint(1000, 5000, 100),
        }, index=dates)
        anomaly_results = weighter.batch_detect(df)
        
        # 3. 幻觉检测
        detector = HallucinationDetector()
        text = "基于技术分析，螺纹钢处于上升趋势。"
        hallucination_results = detector.check(text)
        
        # 4. Prompt路由
        router = AdaptivePromptRouter()
        template = router.route("分析螺纹钢行情")
        
        # 验证
        assert conflict_result.resolved_value > 0
        assert len(anomaly_results) == 100
        assert len(hallucination_results) == 0
        assert template.template_type == PromptTemplateType.STANDARD


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
