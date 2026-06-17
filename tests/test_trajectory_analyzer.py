"""
轨迹分析器单元测试

测试轨迹分析器、失败学习器、优化规则生成器的功能。

版本：v1.0
创建日期：2026-06-15
"""

import os
import sys

import pytest


# 添加模块路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))

from trend_scanner.trajectory_analyzer import (
    FailureLearner,
    OptimizationRule,
    OptimizationRuleGenerator,
    Pattern,
    TradeRecord,
    TrajectoryAnalyzer,
)


class TestTrajectoryAnalyzer:
    """轨迹分析器测试"""

    def setup_method(self):
        """测试前准备"""
        self.analyzer = TrajectoryAnalyzer()

    def test_load_trade_history(self):
        """测试加载交易历史"""
        trade_history = [
            {
                "trade_id": "trade_001",
                "symbol": "DCE.jm2609",
                "direction": "LONG",
                "entry_price": 1500,
                "exit_price": 1550,
                "entry_time": "2026-06-01 10:00:00",
                "exit_time": "2026-06-05 15:00:00",
                "pnl": 50,
                "pnl_percent": 3.33,
                "holding_period": 4,
                "market_state": "trending",
                "trend_phase": "DEVELOPING",
                "volatility": "medium",
                "er": 0.7,
                "tsi": 25.3,
                "rsi": 55,
                "adx": 30,
                "max_drawdown": 1.5,
                "sharpe_ratio": 1.2,
            }
        ]

        self.analyzer.load_trade_history(trade_history)

        assert len(self.analyzer.trade_history) == 1
        assert self.analyzer.trade_history[0].trade_id == "trade_001"

    def test_analyze_with_empty_history(self):
        """测试空历史分析"""
        report = self.analyzer.analyze()

        assert "error" in report

    def test_analyze_with_trade_history(self):
        """测试有交易历史的分析"""
        trade_history = [
            {
                "trade_id": "trade_001",
                "symbol": "DCE.jm2609",
                "direction": "LONG",
                "entry_price": 1500,
                "exit_price": 1550,
                "entry_time": "2026-06-01 10:00:00",
                "exit_time": "2026-06-05 15:00:00",
                "pnl": 50,
                "pnl_percent": 3.33,
                "holding_period": 4,
                "market_state": "trending",
                "trend_phase": "DEVELOPING",
                "volatility": "medium",
                "er": 0.7,
                "tsi": 25.3,
                "rsi": 55,
                "adx": 30,
                "max_drawdown": 1.5,
                "sharpe_ratio": 1.2,
            },
            {
                "trade_id": "trade_002",
                "symbol": "DCE.jm2609",
                "direction": "LONG",
                "entry_price": 1550,
                "exit_price": 1520,
                "entry_time": "2026-06-06 10:00:00",
                "exit_time": "2026-06-08 15:00:00",
                "pnl": -30,
                "pnl_percent": -1.94,
                "holding_period": 2,
                "market_state": "ranging",
                "trend_phase": "UNKNOWN",
                "volatility": "low",
                "er": 0.4,
                "tsi": 5.2,
                "rsi": 48,
                "adx": 15,
                "max_drawdown": 2.5,
                "sharpe_ratio": -0.8,
                "failure_reason": "市场震荡，趋势不明确",
            },
        ]

        self.analyzer.load_trade_history(trade_history)
        report = self.analyzer.analyze()

        assert "summary" in report
        assert "patterns" in report
        assert "optimization_rules" in report
        assert "failure_analysis" in report
        assert "success_analysis" in report

        assert report["summary"]["total_trades"] == 2
        assert report["summary"]["success_count"] == 1
        assert report["summary"]["failure_count"] == 1

    def test_classify_cases(self):
        """测试分类成功和失败案例"""
        trade_history = [
            {
                "trade_id": "trade_001",
                "symbol": "DCE.jm2609",
                "direction": "LONG",
                "entry_price": 1500,
                "exit_price": 1550,
                "entry_time": "2026-06-01 10:00:00",
                "exit_time": "2026-06-05 15:00:00",
                "pnl": 50,
                "pnl_percent": 3.33,
                "holding_period": 4,
                "market_state": "trending",
                "trend_phase": "DEVELOPING",
                "volatility": "medium",
                "er": 0.7,
                "tsi": 25.3,
                "rsi": 55,
                "adx": 30,
                "max_drawdown": 1.5,
                "sharpe_ratio": 1.2,
            },
            {
                "trade_id": "trade_002",
                "symbol": "DCE.jm2609",
                "direction": "LONG",
                "entry_price": 1550,
                "exit_price": 1520,
                "entry_time": "2026-06-06 10:00:00",
                "exit_time": "2026-06-08 15:00:00",
                "pnl": -30,
                "pnl_percent": -1.94,
                "holding_period": 2,
                "market_state": "ranging",
                "trend_phase": "UNKNOWN",
                "volatility": "low",
                "er": 0.4,
                "tsi": 5.2,
                "rsi": 48,
                "adx": 15,
                "max_drawdown": 2.5,
                "sharpe_ratio": -0.8,
                "failure_reason": "市场震荡，趋势不明确",
            },
        ]

        self.analyzer.load_trade_history(trade_history)
        self.analyzer._classify_cases()

        assert len(self.analyzer.success_cases) == 1
        assert len(self.analyzer.failure_cases) == 1
        assert self.analyzer.success_cases[0].trade_id == "trade_001"
        assert self.analyzer.failure_cases[0].trade_id == "trade_002"


class TestFailureLearner:
    """失败学习器测试"""

    def setup_method(self):
        """测试前准备"""
        self.learner = FailureLearner()

    def test_learn_from_failures(self):
        """测试从失败案例中学习"""
        failure_cases = [
            TradeRecord(
                trade_id="trade_001",
                symbol="DCE.jm2609",
                direction="LONG",
                entry_price=1500,
                exit_price=1480,
                entry_time="2026-06-01 10:00:00",
                exit_time="2026-06-03 15:00:00",
                pnl=-20,
                pnl_percent=-1.33,
                holding_period=2,
                market_state="ranging",
                trend_phase="UNKNOWN",
                volatility="low",
                er=0.4,
                tsi=5.2,
                rsi=48,
                adx=15,
                max_drawdown=2.0,
                sharpe_ratio=-0.5,
                failure_reason="市场震荡，趋势不明确",
            ),
            TradeRecord(
                trade_id="trade_002",
                symbol="DCE.jm2609",
                direction="LONG",
                entry_price=1520,
                exit_price=1500,
                entry_time="2026-06-04 10:00:00",
                exit_time="2026-06-06 15:00:00",
                pnl=-20,
                pnl_percent=-1.32,
                holding_period=2,
                market_state="ranging",
                trend_phase="UNKNOWN",
                volatility="low",
                er=0.35,
                tsi=3.1,
                rsi=45,
                adx=12,
                max_drawdown=1.8,
                sharpe_ratio=-0.6,
                failure_reason="市场震荡，趋势不明确",
            ),
        ]

        rules = self.learner.learn_from_failures(failure_cases)

        assert len(rules) > 0
        assert rules[0].rule_type == "avoidance"
        assert "市场震荡" in rules[0].reason

    def test_learn_from_empty_failures(self):
        """测试从空失败案例中学习"""
        rules = self.learner.learn_from_failures([])

        assert len(rules) == 0


class TestOptimizationRuleGenerator:
    """优化规则生成器测试"""

    def setup_method(self):
        """测试前准备"""
        self.generator = OptimizationRuleGenerator()

    def test_generate_rules(self):
        """测试生成优化规则"""
        patterns = [
            Pattern(
                pattern_id="failure_001",
                pattern_type="failure",
                description="市场震荡下的失败模式",
                conditions={"market_state": "ranging", "failure_reason": "市场震荡，趋势不明确"},
                frequency=5,
                avg_pnl=-2.5,
                confidence=0.8,
            ),
            Pattern(
                pattern_id="success_001",
                pattern_type="success",
                description="趋势市场的成功模式",
                conditions={"market_state": "trending"},
                frequency=8,
                avg_pnl=3.2,
                confidence=0.9,
            ),
        ]

        rules = self.generator.generate_rules(patterns)

        assert len(rules) == 2

        # 检查避免规则
        avoidance_rules = [r for r in rules if r.rule_type == "avoidance"]
        assert len(avoidance_rules) == 1
        assert avoidance_rules[0].priority == "high"  # frequency >= 5

        # 检查增强规则
        enhancement_rules = [r for r in rules if r.rule_type == "enhancement"]
        assert len(enhancement_rules) == 1
        assert enhancement_rules[0].priority == "medium"  # frequency >= 3

    def test_generate_rules_with_empty_patterns(self):
        """测试空模式生成规则"""
        rules = self.generator.generate_rules([])

        assert len(rules) == 0


class TestTradeRecord:
    """交易记录测试"""

    def test_create_trade_record(self):
        """测试创建交易记录"""
        trade = TradeRecord(
            trade_id="trade_001",
            symbol="DCE.jm2609",
            direction="LONG",
            entry_price=1500,
            exit_price=1550,
            entry_time="2026-06-01 10:00:00",
            exit_time="2026-06-05 15:00:00",
            pnl=50,
            pnl_percent=3.33,
            holding_period=4,
            market_state="trending",
            trend_phase="DEVELOPING",
            volatility="medium",
            er=0.7,
            tsi=25.3,
            rsi=55,
            adx=30,
            max_drawdown=1.5,
            sharpe_ratio=1.2,
        )

        assert trade.trade_id == "trade_001"
        assert trade.symbol == "DCE.jm2609"
        assert trade.direction == "LONG"
        assert trade.pnl == 50


class TestPattern:
    """模式测试"""

    def test_create_pattern(self):
        """测试创建模式"""
        pattern = Pattern(
            pattern_id="success_001",
            pattern_type="success",
            description="趋势市场的成功模式",
            conditions={"market_state": "trending"},
            frequency=8,
            avg_pnl=3.2,
            confidence=0.9,
        )

        assert pattern.pattern_id == "success_001"
        assert pattern.pattern_type == "success"
        assert pattern.frequency == 8


class TestOptimizationRule:
    """优化规则测试"""

    def test_create_optimization_rule(self):
        """测试创建优化规则"""
        rule = OptimizationRule(
            rule_id="avoidance_001",
            rule_type="avoidance",
            condition="市场状态为 ranging",
            action="避免入场",
            reason="历史失败模式",
            priority="high",
            source_pattern_id="failure_001",
        )

        assert rule.rule_id == "avoidance_001"
        assert rule.rule_type == "avoidance"
        assert rule.priority == "high"


# 运行测试
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
