"""
Carry 策略分析器测试

测试内容：
1. TermStructure 期限结构计算
2. InventoryData 库存数据计算
3. CarryAnalyzer 信号生成
4. 品种 Carry 适配性评级

版本：v1.0
创建日期：2026-06-18
"""

import pytest
from strategies.carry import (
    CarryAnalyzer,
    TermStructure,
    InventoryData,
    CarrySignal,
    analyze_carry,
)


class TestTermStructure:
    """期限结构测试"""

    def test_backwardation_structure(self):
        """测试 Backwardation 结构"""
        ts = TermStructure(
            symbol="CU",
            near_month="CU2407",
            far_month="CU2408",
            near_price=70000,
            far_price=69500,
            months_interval=1,
        )

        assert ts.structure_type == "Backwardation"
        assert ts.spread == 500
        assert ts.roll_yield > 0
        assert ts.slope < 0

    def test_contango_structure(self):
        """测试 Contango 结构"""
        ts = TermStructure(
            symbol="TA",
            near_month="TA2407",
            far_month="TA2408",
            near_price=6000,
            far_price=6100,
            months_interval=1,
        )

        assert ts.structure_type == "Contango"
        assert ts.spread == -100
        assert ts.roll_yield < 0
        assert ts.slope > 0

    def test_roll_yield_calculation(self):
        """测试展期收益率计算"""
        ts = TermStructure(
            symbol="M",
            near_month="M2407",
            far_month="M2409",
            near_price=3200,
            far_price=3100,
            months_interval=2,
        )

        # Roll Yield = (3200 - 3100) / 3100 * (12 / 2) * 100%
        expected_roll_yield = (100 / 3100) * 6 * 100
        assert abs(ts.roll_yield - expected_roll_yield) < 0.1

    def test_slope_calculation(self):
        """测试斜率计算"""
        ts = TermStructure(
            symbol="I",
            near_month="I2407",
            far_month="I2408",
            near_price=800,
            far_price=820,
            months_interval=1,
        )

        # Slope = (820 - 800) / 800 = 0.025
        assert abs(ts.slope - 0.025) < 0.001

    def test_normalized_rank(self):
        """测试标准化排序"""
        ts = TermStructure(
            symbol="CU",
            near_month="CU2407",
            far_month="CU2408",
            near_price=70000,
            far_price=69500,
            months_interval=1,
        )

        # R = (70000 - 69500) / 69500
        expected_rank = 500 / 69500
        assert abs(ts.normalized_rank - expected_rank) < 0.001


class TestInventoryData:
    """库存数据测试"""

    def test_percentile_calculation(self):
        """测试库存分位数计算"""
        inv = InventoryData(
            symbol="CU",
            current_level=50000,
            historical_min=30000,
            historical_max=80000,
        )

        # 分位数 = (50000 - 30000) / (80000 - 30000) * 100 = 40%
        assert inv.percentile == 40.0

    def test_inventory_zone(self):
        """测试库存区间"""
        # 低库存
        inv_low = InventoryData(
            symbol="CU",
            current_level=35000,
            historical_min=30000,
            historical_max=80000,
        )
        assert inv_low.inventory_zone == "LOW"

        # 高库存
        inv_high = InventoryData(
            symbol="CU",
            current_level=75000,
            historical_min=30000,
            historical_max=80000,
        )
        assert inv_high.inventory_zone == "HIGH"

        # 中等库存
        inv_medium = InventoryData(
            symbol="CU",
            current_level=55000,
            historical_min=30000,
            historical_max=80000,
        )
        assert inv_medium.inventory_zone == "MEDIUM"


class TestCarryAnalyzer:
    """Carry 分析器测试"""

    def test_basic_analysis(self):
        """基础分析测试"""
        ts = TermStructure(
            symbol="CU",
            near_month="CU2407",
            far_month="CU2408",
            near_price=70000,
            far_price=69500,
            months_interval=1,
        )

        analyzer = CarryAnalyzer()
        signal = analyzer.analyze(ts)

        assert signal.symbol == "CU"
        assert signal.term_structure.structure_type == "Backwardation"
        assert signal.signal_direction in ["LONG_CARRY", "SHORT_CARRY", "NEUTRAL"]
        assert signal.signal_strength in ["STRONG", "MEDIUM", "WEAK"]

    def test_backwardation_signal(self):
        """测试 Backwardation 信号"""
        ts = TermStructure(
            symbol="CU",
            near_month="CU2407",
            far_month="CU2408",
            near_price=70000,
            far_price=69500,
            months_interval=1,
        )

        inv = InventoryData(
            symbol="CU",
            current_level=35000,
            historical_min=30000,
            historical_max=80000,
        )

        analyzer = CarryAnalyzer()
        signal = analyzer.analyze(ts, inv)

        assert signal.signal_direction == "LONG_CARRY"
        assert signal.roll_yield_score > 0

    def test_contango_signal(self):
        """测试 Contango 信号"""
        ts = TermStructure(
            symbol="TA",
            near_month="TA2407",
            far_month="TA2408",
            near_price=6000,
            far_price=6100,
            months_interval=1,
        )

        inv = InventoryData(
            symbol="TA",
            current_level=70000,
            historical_min=30000,
            historical_max=80000,
        )

        analyzer = CarryAnalyzer()
        signal = analyzer.analyze(ts, inv)

        assert signal.signal_direction == "SHORT_CARRY"
        assert signal.roll_yield_score < 0

    def test_inventory_score(self):
        """测试库存得分"""
        ts = TermStructure(
            symbol="CU",
            near_month="CU2407",
            far_month="CU2408",
            near_price=70000,
            far_price=69500,
            months_interval=1,
        )

        # 低库存 + Back结构 = 正分
        inv_low = InventoryData(
            symbol="CU",
            current_level=35000,
            historical_min=30000,
            historical_max=80000,
            change_rate=-1000,
        )

        analyzer = CarryAnalyzer()
        signal = analyzer.analyze(ts, inv_low)

        assert signal.inventory_score > 0

    def test_compatibility_rating(self):
        """测试品种适配性评级"""
        # 第一梯队
        ts_cu = TermStructure("CU", "CU2407", "CU2408", 70000, 69500, 1)
        analyzer = CarryAnalyzer()
        signal_cu = analyzer.analyze(ts_cu)
        assert signal_cu.composite_score is not None

        # 第三梯队
        ts_rb = TermStructure("RB", "RB2410", "RB2501", 3600, 3700, 3)
        signal_rb = analyzer.analyze(ts_rb)
        # 第三梯队品种信号强度会被降级
        assert signal_rb.signal_strength in ["WEAK", "MEDIUM"]

    def test_rank_products(self):
        """测试品种排序"""
        signals = []

        # CU: Back结构
        ts_cu = TermStructure("CU", "CU2407", "CU2408", 70000, 69500, 1)
        analyzer = CarryAnalyzer()
        signals.append(analyzer.analyze(ts_cu))

        # TA: Contango结构
        ts_ta = TermStructure("TA", "TA2407", "TA2408", 6000, 6100, 1)
        signals.append(analyzer.analyze(ts_ta))

        # 排序
        ranked = analyzer.rank_products(signals)

        # CU应该排在TA前面（正Carry vs 负Carry）
        assert ranked[0].symbol == "CU"
        assert ranked[1].symbol == "TA"

    def test_get_top_opportunities(self):
        """测试获取最佳机会"""
        signals = []

        # 多个品种
        symbols = ["CU", "AL", "ZN", "TA", "RB"]
        prices = [
            (70000, 69500),  # CU: Back
            (20000, 19800),  # AL: Back
            (22000, 21800),  # ZN: Back
            (6000, 6100),  # TA: Contango
            (3600, 3700),  # RB: Contango
        ]

        analyzer = CarryAnalyzer()
        for sym, (near, far) in zip(symbols, prices):
            ts = TermStructure(sym, f"{sym}2407", f"{sym}2408", near, far, 1)
            signals.append(analyzer.analyze(ts))

        top = analyzer.get_top_carry_opportunities(signals, top_n=2)

        assert len(top["long_carry"]) == 2
        assert len(top["short_carry"]) == 2
        assert top["long_carry"][0].symbol in ["CU", "AL", "ZN"]

    def test_format_analysis(self):
        """测试格式化输出"""
        ts = TermStructure(
            symbol="CU",
            near_month="CU2407",
            far_month="CU2408",
            near_price=70000,
            far_price=69500,
            months_interval=1,
        )

        analyzer = CarryAnalyzer()
        signal = analyzer.analyze(ts)

        formatted = analyzer.format_analysis(signal)
        assert "CU" in formatted
        assert "Backwardation" in formatted
        assert "展期收益率" in formatted


class TestConvenienceFunction:
    """便捷函数测试"""

    def test_analyze_carry(self):
        """测试便捷函数"""
        signal = analyze_carry(
            symbol="CU",
            near_price=70000,
            far_price=69500,
            near_month="CU2407",
            far_month="CU2408",
            months_interval=1,
        )

        assert signal.symbol == "CU"
        assert signal.term_structure.structure_type == "Backwardation"

    def test_analyze_carry_with_inventory(self):
        """测试带库存数据的便捷函数"""
        signal = analyze_carry(
            symbol="CU",
            near_price=70000,
            far_price=69500,
            near_month="CU2407",
            far_month="CU2408",
            months_interval=1,
            inventory_level=35000,
            historical_min=30000,
            historical_max=80000,
            change_rate=-1000,
        )

        assert signal.symbol == "CU"
        assert signal.inventory is not None
        assert signal.inventory.inventory_zone == "LOW"


class TestRiskChecks:
    """风险检查测试"""

    def test_curve_flip_risk(self):
        """测试 Curve Flip 风险检测"""
        ts = TermStructure(
            symbol="CU",
            near_month="CU2407",
            far_month="CU2408",
            near_price=70000,
            far_price=69500,
            months_interval=1,
        )

        # 历史价差为负（Contango），当前为正（Back）= Curve Flip
        historical = [-500, -300, -200]

        analyzer = CarryAnalyzer()
        signal = analyzer.analyze(ts, historical_spreads=historical)

        assert any("Curve Flip" in w for w in signal.warnings)

    def test_inventory_structure_divergence(self):
        """测试库存与结构背离检测"""
        ts = TermStructure(
            symbol="CU",
            near_month="CU2407",
            far_month="CU2408",
            near_price=70000,
            far_price=69500,
            months_interval=1,
        )

        # 高库存 + Back结构 = 不可靠
        inv = InventoryData(
            symbol="CU",
            current_level=75000,
            historical_min=30000,
            historical_max=80000,
        )

        analyzer = CarryAnalyzer()
        signal = analyzer.analyze(ts, inv)

        assert any("结构风险" in w for w in signal.warnings)
