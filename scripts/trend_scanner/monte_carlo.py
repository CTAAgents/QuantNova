"""
MonteCarloSimulator — 蒙特卡洛模拟模块 v1.0

基于 Kevin J. Davey《构建盈利的算法交易系统》中的核心验证步骤：
对交易结果进行数千次随机重排，生成替代性权益曲线，
评估最坏情况、破产风险和置信区间。

核心功能：
1. 交易重排模拟（有放回随机抽样）
2. 破产概率计算
3. 最大回撤分布
4. 各置信水平统计量
5. 最差情景分析

使用方式：
    from monte_carlo import MonteCarloSimulator
    sim = MonteCarloSimulator(n_simulations=10000)
    result = sim.simulate(trades=[500, -300, 800, -200], initial_capital=100000)
    print(f"破产概率: {result.ruin_probability:.2%}")
    print(f"95%回撤: {result.max_drawdown_95:.2%}")

版本：v1.0
创建日期：2026-06-17
"""

import logging
from dataclasses import dataclass, field

import numpy as np


logger = logging.getLogger(__name__)


# ===================== 数据模型 =====================


@dataclass
class MonteCarloResult:
    """蒙特卡洛模拟结果"""

    n_simulations: int
    initial_capital: float
    trades_count: int

    # 资金统计
    final_capital_median: float = 0.0
    final_capital_mean: float = 0.0
    final_capital_std: float = 0.0

    # 回撤统计
    max_drawdown_median: float = 0.0
    max_drawdown_mean: float = 0.0
    max_drawdown_95: float = 0.0  # 95%置信水平
    max_drawdown_99: float = 0.0  # 99%置信水平

    # 风险指标
    ruin_probability: float = 0.0  # 破产概率
    sharpe_ratio_median: float = 0.0
    win_rate_median: float = 0.0

    # 最差情景
    worst_case: dict = field(default_factory=dict)

    # 可选：模拟权益曲线（仅在 save_curves=True 时保存）
    equity_curves: np.ndarray | None = None

    def to_dict(self) -> dict:
        """转为字典（便于JSON序列化）"""
        return {
            "n_simulations": self.n_simulations,
            "initial_capital": self.initial_capital,
            "trades_count": self.trades_count,
            "final_capital": {
                "median": round(self.final_capital_median, 2),
                "mean": round(self.final_capital_mean, 2),
                "std": round(self.final_capital_std, 2),
            },
            "max_drawdown": {
                "median": round(self.max_drawdown_median, 4),
                "mean": round(self.max_drawdown_mean, 4),
                "p95": round(self.max_drawdown_95, 4),
                "p99": round(self.max_drawdown_99, 4),
            },
            "risk": {
                "ruin_probability": round(self.ruin_probability, 4),
                "sharpe_ratio_median": round(self.sharpe_ratio_median, 4),
                "win_rate_median": round(self.win_rate_median, 4),
            },
            "worst_case": self.worst_case,
        }


# ===================== 模拟器 =====================


class MonteCarloSimulator:
    """
    蒙特卡洛模拟器

    对交易结果进行随机重排，生成替代性权益曲线，
    评估策略在各种极端情况下的表现。
    """

    def __init__(
        self, n_simulations: int = 10000, confidence_levels: list[float] = None, random_seed: int | None = None
    ):
        """
        参数:
            n_simulations: 模拟次数（默认10000）
            confidence_levels: 置信水平列表（默认[0.95, 0.99]）
            random_seed: 随机种子（可选，用于可重复性）
        """
        self.n_simulations = n_simulations
        self.confidence_levels = confidence_levels or [0.95, 0.99]
        self.rng = np.random.RandomState(random_seed)

    def simulate(
        self,
        trades: list[float],
        initial_capital: float = 100000,
        ruin_threshold: float = 0.5,
        save_curves: bool = False,
    ) -> MonteCarloResult:
        """
        对交易结果进行随机重排模拟

        参数:
            trades: 每笔交易的盈亏列表（如 [+500, -300, +800, ...]）
            initial_capital: 初始资金
            ruin_threshold: 破产阈值（如 0.5 表示资金降至50%为破产）
            save_curves: 是否保存所有模拟权益曲线（内存密集）

        返回:
            MonteCarloResult 包含各项统计指标
        """
        if not trades:
            return MonteCarloResult(
                n_simulations=self.n_simulations,
                initial_capital=initial_capital,
                trades_count=0,
            )

        trades_arr = np.array(trades)
        n_trades = len(trades_arr)
        ruin_capital = initial_capital * ruin_threshold

        # 生成模拟权益曲线
        # shape: (n_simulations, n_trades+1)
        equity_curves = np.zeros((self.n_simulations, n_trades + 1))
        equity_curves[:, 0] = initial_capital

        for sim_idx in range(self.n_simulations):
            # 随机重排交易顺序（有放回抽样）
            sampled_trades = self.rng.choice(trades_arr, size=n_trades, replace=True)
            equity_curves[sim_idx, 1:] = initial_capital + np.cumsum(sampled_trades)

        # ====== 资金统计 ======
        final_capitals = equity_curves[:, -1]
        final_capital_median = float(np.median(final_capitals))
        final_capital_mean = float(np.mean(final_capitals))
        final_capital_std = float(np.std(final_capitals))

        # ====== 最大回撤统计 ======
        max_drawdowns = np.zeros(self.n_simulations)
        for i in range(self.n_simulations):
            curve = equity_curves[i]
            running_max = np.maximum.accumulate(curve)
            drawdowns = (running_max - curve) / np.maximum(running_max, 1e-10)
            max_drawdowns[i] = float(np.max(drawdowns))

        max_drawdown_median = float(np.median(max_drawdowns))
        max_drawdown_mean = float(np.mean(max_drawdowns))
        max_drawdown_95 = float(np.percentile(max_drawdowns, 95))
        max_drawdown_99 = float(np.percentile(max_drawdowns, 99))

        # ====== 破产概率 ======
        ruin_count = 0
        for i in range(self.n_simulations):
            if np.any(equity_curves[i] <= ruin_capital):
                ruin_count += 1
        ruin_probability = ruin_count / self.n_simulations

        # ====== 夏普比率 ======
        # 基于每条曲线的交易收益率
        trade_returns = trades_arr / initial_capital
        if len(trade_returns) > 1 and np.std(trade_returns) > 0:
            sharpe_ratio_median = float(
                np.median(
                    [
                        self._sharpe_ratio(self.rng.choice(trade_returns, size=n_trades, replace=True))
                        for _ in range(min(1000, self.n_simulations))
                    ]
                )
            )
        else:
            sharpe_ratio_median = 0.0

        # ====== 胜率 ======
        win_rates = []
        for i in range(min(1000, self.n_simulations)):
            sampled = self.rng.choice(trades_arr, size=n_trades, replace=True)
            win_rate = np.sum(sampled > 0) / n_trades
            win_rates.append(win_rate)
        win_rate_median = float(np.median(win_rates)) if win_rates else 0.0

        # ====== 最差情景 ======
        worst_idx = int(np.argmin(final_capitals))
        worst_case = {
            "final_capital": round(float(final_capitals[worst_idx]), 2),
            "max_drawdown": round(float(max_drawdowns[worst_idx]), 4),
            "ruin_occurred": bool(np.any(equity_curves[worst_idx] <= ruin_capital)),
        }

        # ====== 构建结果 ======
        result = MonteCarloResult(
            n_simulations=self.n_simulations,
            initial_capital=initial_capital,
            trades_count=n_trades,
            final_capital_median=final_capital_median,
            final_capital_mean=final_capital_mean,
            final_capital_std=final_capital_std,
            max_drawdown_median=max_drawdown_median,
            max_drawdown_mean=max_drawdown_mean,
            max_drawdown_95=max_drawdown_95,
            max_drawdown_99=max_drawdown_99,
            ruin_probability=ruin_probability,
            sharpe_ratio_median=sharpe_ratio_median,
            win_rate_median=win_rate_median,
            worst_case=worst_case,
        )

        if save_curves:
            result.equity_curves = equity_curves

        return result

    def calculate_ruin_probability(
        self,
        trades: list[float],
        initial_capital: float = 100000,
        ruin_threshold: float = 0.5,
        n_simulations: int = None,
    ) -> float:
        """
        快速计算破产概率

        参数:
            trades: 每笔交易的盈亏列表
            initial_capital: 初始资金
            ruin_threshold: 破产阈值
            n_simulations: 模拟次数（默认使用实例配置）

        返回:
            破产概率 (0-1)
        """
        if not trades:
            return 0.0

        n_sims = n_simulations or self.n_simulations
        trades_arr = np.array(trades)
        n_trades = len(trades_arr)
        ruin_capital = initial_capital * ruin_threshold

        ruin_count = 0
        for _ in range(n_sims):
            sampled = self.rng.choice(trades_arr, size=n_trades, replace=True)
            equity = initial_capital + np.cumsum(sampled)
            if np.any(equity <= ruin_capital):
                ruin_count += 1

        return ruin_count / n_sims

    def calculate_expected_drawdown(
        self, trades: list[float], initial_capital: float = 100000, n_simulations: int = None
    ) -> dict:
        """
        计算预期最大回撤分布

        返回:
            {
                "median": 中位数回撤,
                "mean": 平均回撤,
                "std": 回撤标准差,
                "p95": 95%分位数,
                "p99": 99%分位数,
                "min": 最小回撤,
                "max": 最大回撤,
            }
        """
        if not trades:
            return {"median": 0, "mean": 0, "std": 0, "p95": 0, "p99": 0, "min": 0, "max": 0}

        n_sims = n_simulations or self.n_simulations
        trades_arr = np.array(trades)
        n_trades = len(trades_arr)

        max_drawdowns = np.zeros(n_sims)
        for i in range(n_sims):
            sampled = self.rng.choice(trades_arr, size=n_trades, replace=True)
            equity = initial_capital + np.cumsum(sampled)
            equity = np.insert(equity, 0, initial_capital)
            running_max = np.maximum.accumulate(equity)
            drawdowns = (running_max - equity) / np.maximum(running_max, 1e-10)
            max_drawdowns[i] = np.max(drawdowns)

        return {
            "median": round(float(np.median(max_drawdowns)), 4),
            "mean": round(float(np.mean(max_drawdowns)), 4),
            "std": round(float(np.std(max_drawdowns)), 4),
            "p95": round(float(np.percentile(max_drawdowns, 95)), 4),
            "p99": round(float(np.percentile(max_drawdowns, 99)), 4),
            "min": round(float(np.min(max_drawdowns)), 4),
            "max": round(float(np.max(max_drawdowns)), 4),
        }

    @staticmethod
    def _sharpe_ratio(returns: np.ndarray, risk_free_rate: float = 0.0) -> float:
        """计算夏普比率"""
        if len(returns) < 2:
            return 0.0
        excess = returns - risk_free_rate
        std = np.std(excess)
        if std < 1e-10:
            return 0.0
        return float(np.mean(excess) / std * np.sqrt(252))  # 年化


# ===================== 便捷函数 =====================


def run_monte_carlo(
    trades: list[float], initial_capital: float = 100000, n_simulations: int = 10000, ruin_threshold: float = 0.5
) -> MonteCarloResult:
    """
    便捷函数：运行蒙特卡洛模拟

    参数:
        trades: 每笔交易的盈亏列表
        initial_capital: 初始资金
        n_simulations: 模拟次数
        ruin_threshold: 破产阈值

    返回:
        MonteCarloResult
    """
    sim = MonteCarloSimulator(n_simulations=n_simulations)
    return sim.simulate(trades, initial_capital, ruin_threshold)
