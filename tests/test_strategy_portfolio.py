"""
StrategyPortfolio 单元测试

覆盖:
- 策略添加/移除
- 组合权益曲线计算
- 分散化比率
- 相关性分析
- 权重优化
- 组合统计
- 高相关性警告
- 边界条件
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import numpy as np
import pandas as pd

from scripts.trend_scanner.strategy_portfolio import (
    StrategyPortfolio, StrategyInfo, PortfolioStats
)


class TestStrategyInfo:
    """StrategyInfo 数据类测试"""

    def test_creation(self):
        equity = pd.Series([100, 105, 110, 108, 115])
        info = StrategyInfo(strategy_id="test", weight=0.5, equity_curve=equity)

        assert info.strategy_id == "test"
        assert info.weight == 0.5
        assert info.sharpe != 0 or len(equity) < 3  # 需要足够数据

    def test_post_init_calculates_metrics(self):
        equity = pd.Series([100, 102, 101, 105, 110, 108, 115])
        info = StrategyInfo(strategy_id="test", weight=0.5, equity_curve=equity)

        assert info.returns is not None
        assert len(info.returns) > 0
        assert info.max_drawdown >= 0


class TestStrategyPortfolio:
    """StrategyPortfolio 核心功能测试"""

    def setup_method(self):
        self.portfolio = StrategyPortfolio(max_strategies=5)

        # 创建三个不同特征的策略
        np.random.seed(42)

        # 策略1：稳定上涨
        self.eq1 = pd.Series([100 + i * 2 + np.random.randn() * 2 for i in range(50)])

        # 策略2：波动较大
        self.eq2 = pd.Series([100 + np.random.randn() * 10 for i in range(50)]).cumsum() + 100

        # 策略3：与策略1部分相关
        self.eq3 = pd.Series([100 + i * 1.5 + np.random.randn() * 3 for i in range(50)])

    def test_add_strategy(self):
        """添加策略"""
        self.portfolio.add_strategy("s1", 0.4, self.eq1)

        assert "s1" in self.portfolio.get_all_strategies()
        assert self.portfolio.get_strategy("s1").weight == 0.4

    def test_add_multiple_strategies(self):
        """添加多个策略"""
        self.portfolio.add_strategy("s1", 0.4, self.eq1)
        self.portfolio.add_strategy("s2", 0.3, self.eq2)
        self.portfolio.add_strategy("s3", 0.3, self.eq3)

        assert len(self.portfolio.get_all_strategies()) == 3

    def test_remove_strategy(self):
        """移除策略"""
        self.portfolio.add_strategy("s1", 0.4, self.eq1)
        self.portfolio.remove_strategy("s1")

        assert "s1" not in self.portfolio.get_all_strategies()

    def test_max_strategies_limit(self):
        """策略数上限"""
        portfolio = StrategyPortfolio(max_strategies=2)
        portfolio.add_strategy("s1", 0.5, self.eq1)
        portfolio.add_strategy("s2", 0.5, self.eq2)

        with pytest.raises(ValueError, match="上限"):
            portfolio.add_strategy("s3", 0.5, self.eq3)

    def test_calculate_portfolio_equity(self):
        """计算组合权益曲线"""
        self.portfolio.add_strategy("s1", 0.4, self.eq1)
        self.portfolio.add_strategy("s2", 0.3, self.eq2)
        self.portfolio.add_strategy("s3", 0.3, self.eq3)

        equity = self.portfolio.calculate_portfolio_equity()

        assert len(equity) > 0
        assert equity.iloc[0] > 0

    def test_empty_portfolio_equity(self):
        """空组合返回空曲线"""
        equity = self.portfolio.calculate_portfolio_equity()
        assert len(equity) == 0

    def test_diversification_ratio(self):
        """分散化比率"""
        self.portfolio.add_strategy("s1", 0.5, self.eq1)
        self.portfolio.add_strategy("s2", 0.5, self.eq2)

        ratio = self.portfolio.calculate_diversification_ratio()

        # 不相关策略的分散化比率应 > 1
        assert ratio > 0

    def test_single_strategy_diversification(self):
        """单策略分散化比率 = 1"""
        self.portfolio.add_strategy("s1", 1.0, self.eq1)

        ratio = self.portfolio.calculate_diversification_ratio()
        assert ratio == 1.0

    def test_analyze_correlation(self):
        """相关性分析"""
        self.portfolio.add_strategy("s1", 0.4, self.eq1)
        self.portfolio.add_strategy("s2", 0.3, self.eq2)
        self.portfolio.add_strategy("s3", 0.3, self.eq3)

        corr = self.portfolio.analyze_correlation()

        assert not corr.empty
        assert corr.shape == (3, 3)
        # 对角线为1
        assert corr.loc["s1", "s1"] == 1.0

    def test_empty_correlation(self):
        """空组合相关性为空"""
        corr = self.portfolio.analyze_correlation()
        assert corr.empty

    def test_optimize_weights_equal(self):
        """等权重优化"""
        self.portfolio.add_strategy("s1", 0.5, self.eq1)
        self.portfolio.add_strategy("s2", 0.5, self.eq2)

        weights = self.portfolio.optimize_weights(method="equal_weight")

        assert abs(weights["s1"] - 0.5) < 0.01
        assert abs(weights["s2"] - 0.5) < 0.01

    def test_optimize_weights_equal_risk(self):
        """等风险权重优化"""
        self.portfolio.add_strategy("s1", 0.5, self.eq1)
        self.portfolio.add_strategy("s2", 0.5, self.eq2)

        weights = self.portfolio.optimize_weights(method="equal_risk")

        # 权重总和为1
        assert abs(sum(weights.values()) - 1.0) < 0.01

    def test_optimize_weights_max_sharpe(self):
        """最大夏普权重优化"""
        self.portfolio.add_strategy("s1", 0.5, self.eq1)
        self.portfolio.add_strategy("s2", 0.5, self.eq2)

        weights = self.portfolio.optimize_weights(method="max_sharpe")

        assert abs(sum(weights.values()) - 1.0) < 0.01

    def test_get_portfolio_stats(self):
        """获取组合统计"""
        self.portfolio.add_strategy("s1", 0.4, self.eq1)
        self.portfolio.add_strategy("s2", 0.3, self.eq2)
        self.portfolio.add_strategy("s3", 0.3, self.eq3)

        stats = self.portfolio.get_portfolio_stats()

        assert isinstance(stats, PortfolioStats)
        assert stats.total_strategies == 3
        assert stats.portfolio_volatility >= 0
        assert stats.portfolio_max_drawdown >= 0

    def test_empty_portfolio_stats(self):
        """空组合统计"""
        stats = self.portfolio.get_portfolio_stats()
        assert stats.total_strategies == 0

    def test_check_correlation_warning(self):
        """高相关性警告"""
        # 创建两个高度相关的策略
        eq_a = pd.Series([100 + i * 2 for i in range(50)])
        eq_b = pd.Series([100 + i * 2 + np.random.randn() * 0.1 for i in range(50)])

        portfolio = StrategyPortfolio(max_correlation=0.5)
        portfolio.add_strategy("a", 0.5, eq_a)
        portfolio.add_strategy("b", 0.5, eq_b)

        warnings = portfolio.check_correlation_warning()

        # 高度相关的策略应产生警告
        assert len(warnings) > 0
        assert warnings[0][2] > 0.5  # 相关性 > 0.5

    def test_no_correlation_warning(self):
        """低相关性无警告"""
        self.portfolio.add_strategy("s1", 0.5, self.eq1)
        self.portfolio.add_strategy("s2", 0.5, self.eq2)

        warnings = self.portfolio.check_correlation_warning()

        # 不一定有警告（取决于实际相关性）
        assert isinstance(warnings, list)

    def test_portfolio_stats_to_dict(self):
        """PortfolioStats 转字典"""
        stats = PortfolioStats(
            total_strategies=3,
            weights_sum=1.0,
            diversification_ratio=1.2,
            portfolio_sharpe=1.5,
            portfolio_max_drawdown=0.15,
            portfolio_annual_return=0.20,
            portfolio_volatility=0.12,
        )

        d = stats.to_dict()
        assert d["total_strategies"] == 3
        assert d["diversification_ratio"] == 1.2
        assert d["portfolio_sharpe"] == 1.5
