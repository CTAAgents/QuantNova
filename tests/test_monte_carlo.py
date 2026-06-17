"""
MonteCarloSimulator 单元测试

覆盖:
- 全盈利/全亏损/混合交易场景
- 破产概率计算
- 最大回撤分布
- 置信区间统计
- 最差情景分析
- 空交易列表边界条件
- 便捷函数
"""

import os
import sys


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from scripts.trend_scanner.monte_carlo import MonteCarloResult, MonteCarloSimulator, run_monte_carlo


class TestMonteCarloResult:
    """MonteCarloResult 数据类测试"""

    def test_to_dict(self):
        result = MonteCarloResult(
            n_simulations=1000,
            initial_capital=100000,
            trades_count=100,
            final_capital_median=120000,
            ruin_probability=0.05,
        )
        d = result.to_dict()
        assert d["n_simulations"] == 1000
        assert d["initial_capital"] == 100000
        assert d["risk"]["ruin_probability"] == 0.05

    def test_empty_result(self):
        result = MonteCarloResult(
            n_simulations=1000,
            initial_capital=100000,
            trades_count=0,
        )
        d = result.to_dict()
        assert d["trades_count"] == 0


class TestMonteCarloSimulator:
    """MonteCarloSimulator 核心功能测试"""

    def setup_method(self):
        self.sim = MonteCarloSimulator(n_simulations=1000, random_seed=42)

    def test_all_profitable_trades(self):
        """全盈利交易：破产概率=0，最终资金>初始资金"""
        trades = [100, 200, 300, 400, 500]
        result = self.sim.simulate(trades, initial_capital=10000)

        assert result.ruin_probability == 0.0
        assert result.final_capital_median > 10000
        assert result.trades_count == 5

    def test_all_losing_trades(self):
        """全亏损交易：最终资金<初始资金，有显著回撤"""
        trades = [-100, -200, -300, -400, -500]
        result = self.sim.simulate(trades, initial_capital=10000, ruin_threshold=0.5)

        # 全亏损时，最终资金低于初始资金
        assert result.final_capital_median < 10000
        # 有回撤（虽然相对于10000本金可能不大）
        assert result.max_drawdown_median > 0
        # 胜率为0
        assert result.win_rate_median == 0.0

    def test_mixed_trades(self):
        """混合交易：破产概率介于0和1之间"""
        trades = [500, -300, 800, -200, 600, -100]
        result = self.sim.simulate(trades, initial_capital=10000)

        assert 0.0 <= result.ruin_probability <= 1.0
        assert result.final_capital_median > 0

    def test_empty_trades(self):
        """空交易列表：返回空结果"""
        result = self.sim.simulate([], initial_capital=10000)

        assert result.trades_count == 0
        assert result.final_capital_median == 0.0

    def test_single_trade(self):
        """单笔交易"""
        result = self.sim.simulate([100], initial_capital=10000)

        assert result.trades_count == 1
        assert result.final_capital_median == 10100

    def test_max_drawdown_range(self):
        """最大回撤在合理范围内"""
        trades = [100, -50, 200, -80, 150, -30]
        result = self.sim.simulate(trades, initial_capital=10000)

        assert 0.0 <= result.max_drawdown_median <= 1.0
        assert 0.0 <= result.max_drawdown_95 <= 1.0
        assert 0.0 <= result.max_drawdown_99 <= 1.0

    def test_confidence_levels(self):
        """99%回撤 >= 95%回撤"""
        trades = [100, -50, 200, -80, 150, -30, 120, -60]
        result = self.sim.simulate(trades, initial_capital=10000)

        assert result.max_drawdown_99 >= result.max_drawdown_95

    def test_final_capital_stats(self):
        """最终资金统计合理"""
        trades = [100, -50, 200, -80]
        result = self.sim.simulate(trades, initial_capital=10000)

        assert result.final_capital_mean > 0
        assert result.final_capital_std >= 0

    def test_worst_case(self):
        """最差情景包含必要字段"""
        trades = [500, -300, 800, -200]
        result = self.sim.simulate(trades, initial_capital=10000)

        assert "final_capital" in result.worst_case
        assert "max_drawdown" in result.worst_case
        assert "ruin_occurred" in result.worst_case

    def test_save_curves(self):
        """保存权益曲线"""
        trades = [100, -50, 200]
        result = self.sim.simulate(trades, initial_capital=10000, save_curves=True)

        assert result.equity_curves is not None
        assert result.equity_curves.shape == (1000, 4)  # n_sims x (n_trades+1)

    def test_no_save_curves(self):
        """默认不保存权益曲线"""
        trades = [100, -50, 200]
        result = self.sim.simulate(trades, initial_capital=10000)

        assert result.equity_curves is None

    def test_reproducible_with_seed(self):
        """固定随机种子产生可重复结果"""
        sim1 = MonteCarloSimulator(n_simulations=500, random_seed=123)
        sim2 = MonteCarloSimulator(n_simulations=500, random_seed=123)

        trades = [100, -50, 200, -80, 150]
        r1 = sim1.simulate(trades, initial_capital=10000)
        r2 = sim2.simulate(trades, initial_capital=10000)

        assert r1.final_capital_median == r2.final_capital_median
        assert r1.ruin_probability == r2.ruin_probability

    def test_high_volatility_trades(self):
        """高波动交易：回撤可能较大"""
        trades = [1000, -900, 1200, -1100, 800, -700]
        result = self.sim.simulate(trades, initial_capital=10000)

        assert result.max_drawdown_median > 0.1  # 高波动应有显著回撤


class TestRuinProbability:
    """破产概率计算测试"""

    def setup_method(self):
        self.sim = MonteCarloSimulator(n_simulations=1000, random_seed=42)

    def test_safe_strategy(self):
        """安全策略：破产概率低"""
        trades = [100, 80, 120, 90, 110]  # 全盈利
        prob = self.sim.calculate_ruin_probability(trades, initial_capital=10000)
        assert prob == 0.0

    def test_risky_strategy(self):
        """高风险策略：破产概率高"""
        trades = [-500, -400, -300, -200, -100]  # 全亏损
        prob = self.sim.calculate_ruin_probability(trades, initial_capital=10000, ruin_threshold=0.9)
        assert prob > 0.5

    def test_empty_trades(self):
        """空交易：破产概率=0"""
        prob = self.sim.calculate_ruin_probability([])
        assert prob == 0.0


class TestExpectedDrawdown:
    """预期最大回撤测试"""

    def setup_method(self):
        self.sim = MonteCarloSimulator(n_simulations=500, random_seed=42)

    def test_return_format(self):
        """返回格式正确"""
        trades = [100, -50, 200, -80]
        dd = self.sim.calculate_expected_drawdown(trades, initial_capital=10000)

        assert "median" in dd
        assert "mean" in dd
        assert "std" in dd
        assert "p95" in dd
        assert "p99" in dd
        assert "min" in dd
        assert "max" in dd

    def test_drawdown_range(self):
        """回撤在 [0, 1] 范围内"""
        trades = [100, -50, 200, -80, 150]
        dd = self.sim.calculate_expected_drawdown(trades, initial_capital=10000)

        assert 0.0 <= dd["median"] <= 1.0
        assert 0.0 <= dd["p95"] <= 1.0
        assert 0.0 <= dd["p99"] <= 1.0

    def test_p99_gte_p95(self):
        """99%分位数 >= 95%分位数"""
        trades = [100, -50, 200, -80, 150, -30]
        dd = self.sim.calculate_expected_drawdown(trades, initial_capital=10000)

        assert dd["p99"] >= dd["p95"]

    def test_empty_trades(self):
        """空交易：回撤全为0"""
        dd = self.sim.calculate_expected_drawdown([])
        assert dd["median"] == 0
        assert dd["mean"] == 0


class TestRunMonteCarlo:
    """便捷函数测试"""

    def test_basic_usage(self):
        trades = [500, -300, 800, -200]
        result = run_monte_carlo(trades, initial_capital=10000, n_simulations=500)

        assert isinstance(result, MonteCarloResult)
        assert result.n_simulations == 500
        assert result.trades_count == 4

    def test_custom_params(self):
        trades = [100, -50, 200]
        result = run_monte_carlo(
            trades,
            initial_capital=50000,
            n_simulations=200,
            ruin_threshold=0.3,
        )

        assert result.initial_capital == 50000
        assert result.n_simulations == 200
