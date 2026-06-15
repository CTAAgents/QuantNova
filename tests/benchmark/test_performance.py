"""
Phase 6.2: 性能基准测试

验证各模块的执行时间在可接受范围内：
- 因子生成（规则模式）< 5s
- 轨迹分析（100笔交易）< 10s
- 研报解析（规则模式）< 3s
- RL 接口设计（规则模式）< 5s

创建日期：2026-06-15
"""

import sys
import time
import pytest
from pathlib import Path
from dataclasses import asdict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.trend_scanner.factor_generator import FactorGenerator
from scripts.trend_scanner.trajectory_analyzer import TrajectoryAnalyzer, TradeRecord
from scripts.trend_scanner.report_parser import ReportParser
from scripts.trend_scanner.conceptual_feedback import ConceptualFeedbackGenerator, TradeResult
from scripts.trend_scanner.rl_interface_designer import RLInterfaceDesigner


# ============================================================
# 辅助函数
# ============================================================

def generate_trade_records(n: int):
    """生成 n 笔交易记录"""
    records = []
    for i in range(n):
        pnl = 100.0 if i % 3 != 0 else -80.0
        records.append({
            "trade_id": f"T{i:04d}",
            "symbol": "DCE.jm2609",
            "direction": "LONG" if i % 2 == 0 else "SHORT",
            "entry_price": 1500.0 + i * 10,
            "exit_price": 1500.0 + i * 10 + (60.0 if pnl > 0 else -80.0),
            "entry_time": f"2026-06-{(i % 28) + 1:02d}T09:00:00",
            "exit_time": f"2026-06-{(i % 28) + 1:02d}T15:00:00",
            "pnl": pnl,
            "pnl_percent": pnl / 1500.0 * 100,
            "holding_period": (i % 5) + 1,
            "market_state": ["trending", "ranging", "volatile"][i % 3],
            "trend_phase": ["DEVELOPING", "MATURE", "EXHAUSTING"][i % 3],
            "volatility": ["low", "medium", "high"][i % 3],
            "er": 0.3 + (i % 5) * 0.1,
            "tsi": -0.3 + (i % 7) * 0.1,
            "rsi": 30.0 + (i % 40),
            "adx": 15.0 + (i % 30),
            "max_drawdown": 0.01 + (i % 5) * 0.01,
            "sharpe_ratio": -0.5 + (i % 4) * 0.5,
            "failure_reason": "止损过紧" if pnl < 0 else None
        })
    return records


# ============================================================
# 性能基准测试
# ============================================================

class TestFactorGeneratorPerformance:
    """Phase 1: 因子生成器性能"""

    def test_generate_factor_rule_mode(self):
        """因子生成（规则模式）< 5s

        注意：FactorGenerator 要求 LLM 客户端，无 LLM 时测试初始化耗时
        """
        start = time.time()
        try:
            gen = FactorGenerator()
            result = gen.generate_factor("焦煤市场处于上升趋势，安全检查限产")
            elapsed = time.time() - start
            assert elapsed < 5.0, f"因子生成耗时 {elapsed:.2f}s，超过 5s 阈值"
        except ValueError as e:
            # 无 LLM 客户端时，验证初始化本身 < 2s
            elapsed = time.time() - start
            assert elapsed < 2.0, f"因子生成器初始化耗时 {elapsed:.2f}s，超过 2s 阈值"
            pytest.skip(f"无 LLM 客户端，跳过因子生成性能测试: {e}")
        print(f"\n因子生成耗时: {elapsed:.3f}s")


class TestTrajectoryAnalyzerPerformance:
    """Phase 2: 轨迹分析器性能"""

    def test_analyze_100_trades(self):
        """100 笔交易轨迹分析 < 10s"""
        records = generate_trade_records(100)
        analyzer = TrajectoryAnalyzer()
        analyzer.load_trade_history(records)

        start = time.time()
        report = analyzer.analyze()
        elapsed = time.time() - start

        assert elapsed < 10.0, f"轨迹分析耗时 {elapsed:.2f}s，超过 10s 阈值"
        assert report["summary"]["total_trades"] == 100
        print(f"\n100 笔交易轨迹分析耗时: {elapsed:.3f}s")

    def test_analyze_1000_trades(self):
        """1000 笔交易轨迹分析 < 30s"""
        records = generate_trade_records(1000)
        analyzer = TrajectoryAnalyzer()
        analyzer.load_trade_history(records)

        start = time.time()
        report = analyzer.analyze()
        elapsed = time.time() - start

        assert elapsed < 30.0, f"1000 笔交易轨迹分析耗时 {elapsed:.2f}s，超过 30s 阈值"
        assert report["summary"]["total_trades"] == 1000
        print(f"\n1000 笔交易轨迹分析耗时: {elapsed:.3f}s")


class TestReportParserPerformance:
    """Phase 3: 研报解析器性能"""

    def test_parse_report_rule_mode(self):
        """研报解析（规则模式）< 3s"""
        parser = ReportParser()

        content = """焦煤市场分析报告

核心观点：安全检查限产导致供应收紧，焦煤价格有支撑。
主要观点：港口库存处于低位，补库需求存在。

数据逻辑：
- 焦煤矿开工率为65%，同比下降10个百分点
- 焦化利润为300元/吨，处于年内高位
- 港口库存为150万吨，处于近三年低位

逻辑链：限产 → 供应收紧 → 库存下降 → 价格上涨
"""
        metadata = {"source": "benchmark", "title": "性能测试研报"}

        start = time.time()
        analysis = parser.parse_report(content, metadata)
        elapsed = time.time() - start

        assert elapsed < 3.0, f"研报解析耗时 {elapsed:.2f}s，超过 3s 阈值"
        print(f"\n研报解析耗时: {elapsed:.3f}s")


class TestConceptualFeedbackPerformance:
    """Phase 4: 概念反馈生成器性能"""

    def test_generate_feedback(self):
        """概念反馈生成 < 2s"""
        gen = ConceptualFeedbackGenerator()
        trade = TradeResult(
            trade_id="T001", symbol="DCE.jm2609", direction="LONG",
            entry_price=1500.0, exit_price=1560.0,
            pnl=60.0, pnl_percent=4.0, holding_period=2,
            market_state="trending", trend_phase="DEVELOPING",
            entry_reason="动量突破信号",
            exit_reason="达到目标止盈位",
            success_factors=["趋势确立", "成交量配合"],
            failure_factors=[]
        )

        start = time.time()
        feedback = gen.generate_feedback(trade)
        elapsed = time.time() - start

        assert elapsed < 2.0, f"概念反馈生成耗时 {elapsed:.2f}s，超过 2s 阈值"
        print(f"\n概念反馈生成耗时: {elapsed:.3f}s")


class TestRLInterfaceDesignerPerformance:
    """Phase 5: RL 接口设计器性能"""

    def test_design_interface_rule_mode(self):
        """RL 接口设计（规则模式）< 5s"""
        designer = RLInterfaceDesigner()

        start = time.time()
        design = designer.design_interface(
            market_context="焦煤市场处于上升趋势",
            trading_objective="捕捉趋势机会，控制回撤在 10% 以内",
            available_data=["close", "volume", "high", "low", "open"],
            risk_rules={"max_drawdown": 0.10, "position_limit": 0.3}
        )
        elapsed = time.time() - start

        assert elapsed < 5.0, f"RL 接口设计耗时 {elapsed:.2f}s，超过 5s 阈值"
        assert design["state_space"]["dimension"] > 0
        print(f"\nRL 接口设计耗时: {elapsed:.3f}s")

    def test_refine_interface(self):
        """RL 接口诊断修正 < 5s"""
        designer = RLInterfaceDesigner()
        design = designer.design_interface(
            market_context="测试市场",
            trading_objective="测试目标",
            available_data=["close", "volume"],
            risk_rules={"max_drawdown": 0.10}
        )

        start = time.time()
        refinement = designer.refine_interface(
            current_design=design,
            training_metrics={"sharpe": 0.5, "max_drawdown": 0.15, "win_rate": 0.45},
            expected_metrics={"sharpe": 1.0, "max_drawdown": 0.10, "win_rate": 0.55}
        )
        elapsed = time.time() - start

        assert elapsed < 5.0, f"RL 接口诊断修正耗时 {elapsed:.2f}s，超过 5s 阈值"
        print(f"\nRL 接口诊断修正耗时: {elapsed:.3f}s")


class TestFullPipelinePerformance:
    """端到端全流程性能"""

    def test_full_pipeline_100_trades(self):
        """完整流程（100 笔交易）< 30s"""
        start_total = time.time()

        # Phase 3: 研报解析
        parser = ReportParser()
        t0 = time.time()
        analysis = parser.parse_report(
            "核心观点：安全检查限产导致供应收紧，焦煤价格有支撑。数据逻辑：焦煤矿开工率为65%。",
            {"source": "benchmark"}
        )
        t_report = time.time() - t0

        # Phase 2: 轨迹分析
        analyzer = TrajectoryAnalyzer()
        analyzer.load_trade_history(generate_trade_records(100))
        t0 = time.time()
        trajectory = analyzer.analyze()
        t_trajectory = time.time() - t0

        # Phase 4: 概念反馈
        gen = ConceptualFeedbackGenerator()
        trade = TradeResult(
            trade_id="T001", symbol="DCE.jm2609", direction="LONG",
            entry_price=1500.0, exit_price=1560.0,
            pnl=60.0, pnl_percent=4.0, holding_period=2,
            market_state="trending", trend_phase="DEVELOPING",
            entry_reason="动量突破", exit_reason="止盈",
            success_factors=["趋势确立"], failure_factors=[]
        )
        t0 = time.time()
        feedback = gen.generate_feedback(trade)
        t_feedback = time.time() - t0

        # Phase 5: RL 接口设计
        designer = RLInterfaceDesigner()
        t0 = time.time()
        rl_design = designer.design_interface(
            market_context="测试市场",
            trading_objective="捕捉趋势",
            available_data=["close", "volume"],
            risk_rules={"max_drawdown": 0.10}
        )
        t_rl = time.time() - t0

        elapsed_total = time.time() - start_total

        assert elapsed_total < 30.0, f"完整流程耗时 {elapsed_total:.2f}s，超过 30s 阈值"
        print(f"\n=== 完整流程性能 ===")
        print(f"  研报解析: {t_report:.3f}s")
        print(f"  轨迹分析(100笔): {t_trajectory:.3f}s")
        print(f"  概念反馈: {t_feedback:.3f}s")
        print(f"  RL 接口设计: {t_rl:.3f}s")
        print(f"  总耗时: {elapsed_total:.3f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
