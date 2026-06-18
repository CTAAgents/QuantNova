"""
风险模块集成测试

测试 CrowdingDetector 和 DeploymentRiskEstimator 与核心系统的集成
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "scripts"))

from core.context import ContextAssembler
from core.models import MarketContext
from risk.crowding_detector import CrowdingDetector, CrowdingLevel
from risk.deployment_risk import DeploymentRiskEstimator, ModelPerformance


class TestCrowdingDetector:
    """拥挤度检测器测试"""

    def test_init(self):
        """测试初始化"""
        detector = CrowdingDetector()
        assert detector.high_threshold == 0.7
        assert detector.critical_threshold == 0.9

    def test_detect_basic(self):
        """测试基本检测功能"""
        detector = CrowdingDetector()
        metrics = detector.detect(
            signal=0.5,
            market_volume=1000,
            price_change=0.02,
            order_flow=500,
        )

        assert 0 <= metrics.crowding_score <= 1
        assert isinstance(metrics.level, CrowdingLevel)
        assert 0 <= metrics.deployment_risk_premium <= 1

    def test_detect_high_crowding(self):
        """测试高拥挤度检测"""
        detector = CrowdingDetector()
        metrics = detector.detect(
            signal=0.9,  # 强信号
            market_volume=5000,  # 高成交量
            price_change=0.05,  # 大价格变化
            order_flow=4000,  # 高订单流
        )

        # 高信号+高成交量+高订单流应产生较高拥挤度
        assert metrics.signal_correlation > 0.5

    def test_crowding_curve(self):
        """测试拥挤曲线生成"""
        detector = CrowdingDetector()
        curve = detector.get_crowding_curve(
            signal_strengths=[0.3, 0.5, 0.7, 0.9],
            adoption_rates=[0.1, 0.3, 0.5, 0.7],
        )

        assert len(curve) == 4
        assert all("adoption_rate" in point for point in curve)
        assert all("deployment_risk" in point for point in curve)

    def test_ranking_reversal(self):
        """测试排名反转检测"""
        detector = CrowdingDetector()
        result = detector.check_ranking_reversal(
            model_a_score=0.8,
            model_b_score=0.6,
            adoption_rate=0.5,
            feedback_coefficient=0.5,
        )

        assert "ranking_reversed" in result
        assert "crowding_intensity" in result


class TestDeploymentRiskEstimator:
    """部署风险评估器测试"""

    def test_init(self):
        """测试初始化"""
        estimator = DeploymentRiskEstimator()
        assert estimator.feedback_coefficient == 0.3
        assert estimator.adoption_rate == 0.1

    def test_assess_basic(self):
        """测试基本评估功能"""
        estimator = DeploymentRiskEstimator()
        model = ModelPerformance(
            model_name="test_model",
            historical_accuracy=0.7,
            signal_strength=0.5,
            trading_frequency=0.5,
            position_size=0.3,
        )

        assessment = estimator.assess(model)

        assert 0 <= assessment.historical_risk <= 1
        assert 0 <= assessment.deployment_risk <= 1
        assert 0 <= assessment.feedback_gap <= 1
        assert assessment.deployment_risk >= assessment.historical_risk

    def test_compare_models(self):
        """测试模型比较"""
        estimator = DeploymentRiskEstimator()
        models = [
            ModelPerformance(
                model_name="aggressive",
                historical_accuracy=0.8,
                signal_strength=0.9,
                trading_frequency=0.8,
                position_size=0.5,
            ),
            ModelPerformance(
                model_name="conservative",
                historical_accuracy=0.6,
                signal_strength=0.3,
                trading_frequency=0.3,
                position_size=0.2,
            ),
        ]

        result = estimator.compare_models(models)

        assert "historical_ranking" in result
        assert "deployment_ranking" in result
        assert "ranking_reversed" in result

    def test_feedback_sensitivity(self):
        """测试反馈敏感性估算"""
        estimator = DeploymentRiskEstimator()
        model = ModelPerformance(
            model_name="test_model",
            historical_accuracy=0.7,
            signal_strength=0.5,
            trading_frequency=0.5,
            position_size=0.3,
        )

        curve = estimator.estimate_feedback_sensitivity(
            model, adoption_rates=[0.1, 0.3, 0.5, 0.7]
        )

        assert len(curve) == 4
        # 部署风险应随采用率增加而增加
        risks = [point["deployment_risk"] for point in curve]
        assert risks == sorted(risks)


class TestContextAssemblerIntegration:
    """ContextAssembler 集成测试"""

    def test_init_with_risk_modules(self):
        """测试风险模块加载"""
        assembler = ContextAssembler("RB2501")
        assert assembler._crowding_detector is not None
        assert assembler._deployment_risk_estimator is not None

    def test_assemble_with_risk_assessment(self):
        """测试组装包含风险评估"""
        assembler = ContextAssembler("RB2501")

        # 创建测试数据
        np.random.seed(42)
        n = 100
        dates = pd.date_range("2026-01-01", periods=n)
        df = pd.DataFrame(
            {
                "open": np.random.randn(n) + 100,
                "high": np.random.randn(n) + 101,
                "low": np.random.randn(n) + 99,
                "close": np.random.randn(n) + 100,
                "volume": np.random.randint(1000, 5000, n),
            },
            index=dates,
        )

        context = assembler.assemble(df)

        assert isinstance(context, MarketContext)
        assert context.symbol == "RB2501"
        assert 0 <= context.crowding_score <= 1
        assert context.crowding_level in ["low", "medium", "high", "critical", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
        assert 0 <= context.deployment_risk <= 1

    def test_to_prompt_text_includes_risk(self):
        """测试 to_prompt_text 包含风险信息"""
        assembler = ContextAssembler("RB2501")

        # 创建测试数据
        np.random.seed(42)
        n = 100
        dates = pd.date_range("2026-01-01", periods=n)
        df = pd.DataFrame(
            {
                "open": np.random.randn(n) + 100,
                "high": np.random.randn(n) + 101,
                "low": np.random.randn(n) + 99,
                "close": np.random.randn(n) + 100,
                "volume": np.random.randint(1000, 5000, n),
            },
            index=dates,
        )

        context = assembler.assemble(df)
        prompt_text = context.to_prompt_text()

        # 如果有风险信息，应该包含在输出中
        if context.crowding_score > 0 or context.deployment_risk > 0:
            assert "风险评估" in prompt_text
            assert "拥挤度" in prompt_text


class TestEndToEnd:
    """端到端集成测试"""

    def test_full_workflow(self):
        """测试完整工作流"""
        # 1. 创建上下文组装器
        assembler = ContextAssembler("RB2501")

        # 2. 创建测试数据
        np.random.seed(42)
        n = 100
        dates = pd.date_range("2026-01-01", periods=n)
        df = pd.DataFrame(
            {
                "open": np.random.randn(n) + 100,
                "high": np.random.randn(n) + 101,
                "low": np.random.randn(n) + 99,
                "close": np.random.randn(n) + 100,
                "volume": np.random.randint(1000, 5000, n),
            },
            index=dates,
        )

        # 3. 组装上下文
        context = assembler.assemble(df)

        # 4. 验证风险评估已集成
        assert hasattr(context, "crowding_score")
        assert hasattr(context, "deployment_risk")
        assert hasattr(context, "feedback_gap")

        # 5. 验证 to_prompt_text 输出
        prompt_text = context.to_prompt_text()
        assert "RB2501" in prompt_text
        assert "趋势阶段" in prompt_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
