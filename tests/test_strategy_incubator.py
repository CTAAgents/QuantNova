"""
StrategyIncubator 单元测试

覆盖:
- 孵化会话创建与状态管理
- 信号记录
- 孵化评估（通过/拒绝/延长）
- 信号一致性计算
- 持久化（JSON存储）
- 边界条件
"""

import os
import sys


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import tempfile
from datetime import datetime, timedelta

import pytest

from scripts.trend_scanner.strategy_incubator import IncubationResult, IncubationSession, StrategyIncubator


class TestIncubationSession:
    """IncubationSession 数据类测试"""

    def test_creation(self):
        session = IncubationSession(
            strategy_id="test_001",
            start_time=datetime.now(),
            expected_sharpe=1.5,
            expected_win_rate=0.55,
        )
        assert session.strategy_id == "test_001"
        assert session.status == "active"
        assert session.expected_sharpe == 1.5

    def test_to_dict(self):
        session = IncubationSession(
            strategy_id="test_001",
            start_time=datetime(2026, 1, 1),
            expected_sharpe=1.5,
        )
        d = session.to_dict()
        assert d["strategy_id"] == "test_001"
        assert d["status"] == "active"
        assert d["expected"]["sharpe"] == 1.5


class TestStrategyIncubator:
    """StrategyIncubator 核心功能测试"""

    def setup_method(self):
        # 使用临时目录避免污染真实数据
        self.temp_dir = tempfile.mkdtemp()
        self.storage_path = os.path.join(self.temp_dir, "test_incubation.json")
        self.incubator = StrategyIncubator(
            storage_path=self.storage_path,
            default_incubation_days=90,
            default_max_deviation=0.3,
        )

    def test_start_incubation(self):
        """创建孵化会话"""
        session = self.incubator.start_incubation(
            "strategy_001",
            {
                "expected_sharpe": 1.5,
                "expected_win_rate": 0.55,
                "expected_max_drawdown": 0.15,
            },
        )

        assert session.strategy_id == "strategy_001"
        assert session.status == "active"
        assert session.expected_sharpe == 1.5
        assert session.incubation_days == 90

    def test_start_duplicate_raises(self):
        """重复创建活跃会话抛出异常"""
        self.incubator.start_incubation("strategy_001", {"expected_sharpe": 1.0})

        with pytest.raises(ValueError, match="已有活跃"):
            self.incubator.start_incubation("strategy_001", {"expected_sharpe": 1.0})

    def test_record_signal(self):
        """记录实盘信号"""
        self.incubator.start_incubation("strategy_001", {"expected_sharpe": 1.0})

        self.incubator.record_signal(
            "strategy_001",
            datetime.now(),
            signal=1.0,
            market_state={"close": 100},
        )

        session = self.incubator.get_session("strategy_001")
        assert len(session.actual_signals) == 1
        assert session.actual_signals[0]["signal"] == 1.0

    def test_record_signal_no_session(self):
        """无会话时记录信号抛出异常"""
        with pytest.raises(ValueError, match="没有活跃"):
            self.incubator.record_signal("nonexistent", datetime.now(), 1.0)

    def test_record_multiple_signals(self):
        """记录多个信号"""
        self.incubator.start_incubation("strategy_001", {"expected_sharpe": 1.0})

        for i in range(5):
            self.incubator.record_signal(
                "strategy_001",
                datetime.now() + timedelta(hours=i),
                signal=1.0 if i % 2 == 0 else -1.0,
            )

        session = self.incubator.get_session("strategy_001")
        assert len(session.actual_signals) == 5

    def test_evaluate_insufficient_period(self):
        """孵化期不足时建议延长"""
        self.incubator.start_incubation(
            "strategy_001",
            {
                "expected_sharpe": 1.5,
                "incubation_days": 90,
            },
        )

        # 刚开始，不足一半
        result = self.incubator.evaluate("strategy_001")

        assert result.passed is False
        assert result.recommendation == "extend"

    def test_evaluate_no_signals(self):
        """无信号时拒绝"""
        session = self.incubator.start_incubation(
            "strategy_001",
            {
                "expected_sharpe": 1.5,
                "incubation_days": 10,  # 短孵化期
            },
        )
        # 手动设置开始时间为很久以前
        session.start_time = datetime.now() - timedelta(days=20)

        result = self.incubator.evaluate("strategy_001")

        assert result.passed is False
        assert result.recommendation == "reject"
        assert "无实盘信号" in result.details

    def test_evaluate_with_signals(self):
        """有信号时评估一致性"""
        session = self.incubator.start_incubation(
            "strategy_001",
            {
                "expected_sharpe": 1.5,
                "expected_win_rate": 0.55,
                "incubation_days": 10,
            },
        )
        # 手动设置开始时间为很久以前
        session.start_time = datetime.now() - timedelta(days=20)

        # 记录信号（全部为正，与预期一致）
        for i in range(10):
            self.incubator.record_signal(
                "strategy_001",
                datetime.now() + timedelta(hours=i),
                signal=1.0,
                expected_signal=1.0,
            )

        result = self.incubator.evaluate("strategy_001")

        assert result.signal_consistency > 0.8  # 高一致性
        assert result.deviation_sharpe >= 0

    def test_get_session(self):
        """获取孵化会话"""
        self.incubator.start_incubation("strategy_001", {"expected_sharpe": 1.0})

        session = self.incubator.get_session("strategy_001")
        assert session is not None
        assert session.strategy_id == "strategy_001"

    def test_get_nonexistent_session(self):
        """获取不存在的会话返回None"""
        assert self.incubator.get_session("nonexistent") is None

    def test_get_all_sessions(self):
        """获取所有会话"""
        self.incubator.start_incubation("s1", {"expected_sharpe": 1.0})
        self.incubator.start_incubation("s2", {"expected_sharpe": 1.5})

        sessions = self.incubator.get_all_sessions()
        assert len(sessions) == 2

    def test_get_active_sessions(self):
        """获取活跃会话"""
        self.incubator.start_incubation("s1", {"expected_sharpe": 1.0})
        self.incubator.start_incubation("s2", {"expected_sharpe": 1.5})

        # 完成 s1
        self.incubator.force_complete("s1", "completed")

        active = self.incubator.get_active_sessions()
        assert len(active) == 1
        assert active[0].strategy_id == "s2"

    def test_force_complete(self):
        """强制完成会话"""
        self.incubator.start_incubation("strategy_001", {"expected_sharpe": 1.0})

        self.incubator.force_complete("strategy_001", "completed")

        session = self.incubator.get_session("strategy_001")
        assert session.status == "completed"
        assert session.end_time is not None

    def test_persistence(self):
        """持久化到JSON文件"""
        self.incubator.start_incubation("strategy_001", {"expected_sharpe": 1.0})
        self.incubator.record_signal("strategy_001", datetime.now(), 1.0)

        # 创建新实例，从文件加载
        incubator2 = StrategyIncubator(storage_path=self.storage_path)
        session = incubator2.get_session("strategy_001")

        assert session is not None
        assert len(session.actual_signals) == 1

    def test_restart_after_completion(self):
        """完成后可以重新开始"""
        self.incubator.start_incubation("strategy_001", {"expected_sharpe": 1.0})
        self.incubator.force_complete("strategy_001", "completed")

        # 重新开始
        session2 = self.incubator.start_incubation("strategy_001", {"expected_sharpe": 1.5})
        assert session2.status == "active"
        assert session2.expected_sharpe == 1.5


class TestIncubationResult:
    """IncubationResult 数据类测试"""

    def test_to_dict(self):
        result = IncubationResult(
            strategy_id="test_001",
            passed=True,
            signal_consistency=0.85,
            latency_avg=0.5,
            deviation_sharpe=0.15,
            deviation_win_rate=0.1,
            deviation_drawdown=0.05,
            recommendation="approve",
            details="孵化通过",
        )
        d = result.to_dict()
        assert d["strategy_id"] == "test_001"
        assert d["passed"] is True
        assert d["recommendation"] == "approve"
        assert d["signal_consistency"] == 0.85
