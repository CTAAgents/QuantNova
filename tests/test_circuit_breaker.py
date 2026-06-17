"""
CircuitBreaker 单元测试

覆盖:
- 未触发熔断场景
- 触发亏损熔断
- 触发回撤熔断
- 触发连续亏损熔断
- 冷却期机制
- 重置功能
- 持久化
- 边界条件
"""

import os
import sys


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import tempfile

import pandas as pd

from scripts.trend_scanner.circuit_breaker import CircuitBreaker, CircuitBreakerConfig, StrategyState


class TestCircuitBreakerConfig:
    """CircuitBreakerConfig 测试"""

    def test_defaults(self):
        config = CircuitBreakerConfig()
        assert config.max_loss_per_strategy == 5000.0
        assert config.max_drawdown_pct == 0.20
        assert config.max_consecutive_losses == 10
        assert config.cooldown_days == 30

    def test_to_dict(self):
        config = CircuitBreakerConfig()
        d = config.to_dict()
        assert d["max_loss_per_strategy"] == 5000.0
        assert d["max_drawdown_pct"] == 0.20


class TestCircuitBreaker:
    """CircuitBreaker 核心功能测试"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = os.path.join(self.temp_dir, "test_cb.json")
        self.cb = CircuitBreaker(
            config={
                "max_loss_per_strategy": 5000,
                "max_drawdown_pct": 0.20,
                "max_consecutive_losses": 5,
                "cooldown_days": 30,
            },
            storage_path=self.storage_path,
        )

    def test_no_trigger(self):
        """正常交易不触发熔断"""
        trades = [{"pnl": 100}, {"pnl": -50}, {"pnl": 200}, {"pnl": -30}]
        equity = pd.Series([100000, 100100, 100050, 100250, 100220])

        result = self.cb.check("strategy_001", equity, trades)

        assert result.triggered is False
        assert result.recommendation == "continue"

    def test_trigger_max_loss(self):
        """累计亏损超过阈值触发熔断"""
        trades = [{"pnl": -2000}, {"pnl": -1500}, {"pnl": -1800}]

        result = self.cb.check("strategy_001", trades=trades)

        assert result.triggered is True
        assert "累计亏损" in result.trigger_reason

    def test_trigger_max_drawdown(self):
        """回撤超过阈值触发熔断"""
        # 从100000跌到75000，回撤25%
        equity = pd.Series([100000, 95000, 85000, 75000])

        result = self.cb.check("strategy_001", equity_curve=equity)

        assert result.triggered is True
        assert "回撤" in result.trigger_reason

    def test_trigger_consecutive_losses(self):
        """连续亏损超过阈值触发熔断"""
        trades = [
            {"pnl": 100},
            {"pnl": -50},  # 连续亏损1
            {"pnl": -30},  # 连续亏损2
            {"pnl": -20},  # 连续亏损3
            {"pnl": -40},  # 连续亏损4
            {"pnl": -60},  # 连续亏损5
        ]

        result = self.cb.check("strategy_001", trades=trades)

        assert result.triggered is True
        assert "连续亏损" in result.trigger_reason

    def test_cooldown_period(self):
        """冷却期内保持暂停"""
        trades = [{"pnl": -6000}]
        self.cb.check("strategy_001", trades=trades)

        # 再次检查，仍在冷却期
        result = self.cb.check("strategy_001", trades=trades)

        assert result.triggered is True
        assert result.recommendation == "pause"
        assert result.cooldown_remaining > 0

    def test_reset(self):
        """重置熔断状态"""
        trades = [{"pnl": -6000}]
        self.cb.check("strategy_001", trades=trades)

        self.cb.reset("strategy_001")

        status = self.cb.get_status("strategy_001")
        assert status["is_paused"] is False

    def test_get_status(self):
        """获取策略状态"""
        self.cb.check("strategy_001", trades=[{"pnl": 100}])

        status = self.cb.get_status("strategy_001")

        assert status["strategy_id"] == "strategy_001"
        assert status["check_count"] == 1

    def test_get_all_status(self):
        """获取所有策略状态"""
        self.cb.check("s1", trades=[{"pnl": 100}])
        self.cb.check("s2", trades=[{"pnl": -50}])

        all_status = self.cb.get_all_status()

        assert len(all_status) == 2
        assert "s1" in all_status
        assert "s2" in all_status

    def test_get_paused_strategies(self):
        """获取已暂停策略"""
        self.cb.check("s1", trades=[{"pnl": 100}])
        self.cb.check("s2", trades=[{"pnl": -6000}])

        paused = self.cb.get_paused_strategies()

        assert "s2" in paused
        assert "s1" not in paused

    def test_persistence(self):
        """持久化到JSON文件"""
        self.cb.check("strategy_001", trades=[{"pnl": 100}])

        # 创建新实例
        cb2 = CircuitBreaker(
            config={"max_loss_per_strategy": 5000},
            storage_path=self.storage_path,
        )

        status = cb2.get_status("strategy_001")
        assert status["check_count"] == 1

    def test_equity_curve_only(self):
        """仅提供权益曲线"""
        equity = pd.Series([100000, 95000, 90000, 85000, 79000])  # 回撤21%

        result = self.cb.check("strategy_001", equity_curve=equity)

        assert result.triggered is True  # 回撤21%触发

    def test_trades_only(self):
        """仅提供交易记录"""
        trades = [{"pnl": 100}, {"pnl": -50}, {"pnl": 200}]

        result = self.cb.check("strategy_001", trades=trades)

        assert result.triggered is False

    def test_multiple_strategies(self):
        """多策略独立管理"""
        self.cb.check("s1", trades=[{"pnl": -6000}])
        self.cb.check("s2", trades=[{"pnl": 100}])

        assert self.cb.get_status("s1")["is_paused"] is True
        assert self.cb.get_status("s2")["is_paused"] is False


class TestStrategyState:
    """StrategyState 数据类测试"""

    def test_to_dict(self):
        state = StrategyState(
            strategy_id="test_001",
            is_paused=True,
            pause_reason="测试暂停",
            total_loss=-5000,
        )
        d = state.to_dict()
        assert d["strategy_id"] == "test_001"
        assert d["is_paused"] is True
        assert d["total_loss"] == -5000
