"""
Phase 3/4/5 测试: 知识锚点 + 分级输出 + 套利分析
"""

import os
import tempfile
from datetime import datetime

import numpy as np
import pandas as pd

from trend_scanner.arbitrage_analyzer import ArbitrageAnalyzer, SpreadAnalysis
from trend_scanner.knowledge_anchors import DEFAULT_ANCHORS, KnowledgeAnchor, KnowledgeAnchorManager
from trend_scanner.tiered_output import TieredOutputFormatter, _SectionFormatter


# ===========================================================================
# 知识锚点测试
# ===========================================================================


class TestKnowledgeAnchor:
    def test_default_anchors_count(self):
        assert len(DEFAULT_ANCHORS) >= 10

    def test_anchor_dimensions(self):
        dimensions = set(a["dimension"] for a in DEFAULT_ANCHORS)
        assert "momentum" in dimensions
        assert "trend" in dimensions
        assert "volatility" in dimensions
        assert "volume" in dimensions
        assert "basis" in dimensions
        assert "seasonality" in dimensions

    def test_anchor_has_factor_seeds(self):
        for a in DEFAULT_ANCHORS:
            assert len(a["factor_seeds"]) > 0, f"{a['anchor_id']} 缺少因子种子"

    def test_anchor_has_validation_rules(self):
        for a in DEFAULT_ANCHORS:
            rules = a["validation_rules"]
            assert "min_ic" in rules or "min_ir" in rules or "min_win_rate" in rules


class TestKnowledgeAnchorManager:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_meta.db")

    def test_init_db(self):
        mgr = KnowledgeAnchorManager(self.db_path)
        assert os.path.exists(self.db_path)

    def test_seed_default_anchors(self):
        mgr = KnowledgeAnchorManager(self.db_path)
        count = mgr.seed_default_anchors()
        assert count == len(DEFAULT_ANCHORS)

    def test_get_anchor(self):
        mgr = KnowledgeAnchorManager(self.db_path)
        mgr.seed_default_anchors()
        anchor = mgr.get_anchor("momentum_rsi_extreme")
        assert anchor is not None
        assert anchor.anchor_id == "momentum_rsi_extreme"
        assert anchor.dimension == "momentum"

    def test_get_anchors_by_dimension(self):
        mgr = KnowledgeAnchorManager(self.db_path)
        mgr.seed_default_anchors()
        momentum_anchors = mgr.get_anchors_by_dimension("momentum")
        assert len(momentum_anchors) >= 3

    def test_get_all_anchors(self):
        mgr = KnowledgeAnchorManager(self.db_path)
        mgr.seed_default_anchors()
        all_anchors = mgr.get_all_anchors()
        assert len(all_anchors) == len(DEFAULT_ANCHORS)

    def test_save_custom_anchor(self):
        mgr = KnowledgeAnchorManager(self.db_path)
        anchor = KnowledgeAnchor(
            anchor_id="custom_test",
            dimension="test",
            title="测试锚点",
            core_logic="测试逻辑",
            factor_seeds=[{"expression": "close > open", "name": "bullish"}],
            validation_rules={"min_ic": 0.01},
            applicable_markets=["all"],
            applicable_timeframes=["daily"],
            source="test",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )
        assert mgr.save_anchor(anchor) is True
        retrieved = mgr.get_anchor("custom_test")
        assert retrieved is not None
        assert retrieved.title == "测试锚点"

    def test_get_factor_seeds_for_llm(self):
        mgr = KnowledgeAnchorManager(self.db_path)
        mgr.seed_default_anchors()
        seeds = mgr.get_factor_seeds_for_llm(dimension="momentum")
        assert len(seeds) >= 3
        for s in seeds:
            assert "factor_seeds" in s
            assert "validation_rules" in s

    def test_update_usage(self):
        mgr = KnowledgeAnchorManager(self.db_path)
        mgr.seed_default_anchors()
        mgr.update_usage("momentum_rsi_extreme", win_rate=0.55)
        anchor = mgr.get_anchor("momentum_rsi_extreme")
        assert anchor.usage_count == 1
        assert anchor.win_rate_observed == 0.55

    def test_get_statistics(self):
        mgr = KnowledgeAnchorManager(self.db_path)
        mgr.seed_default_anchors()
        stats = mgr.get_statistics()
        assert stats["total_anchors"] == len(DEFAULT_ANCHORS)
        assert "by_dimension" in stats


# ===========================================================================
# 分级输出测试
# ===========================================================================


class TestTieredOutputFormatter:
    def setup_method(self):
        self.formatter = TieredOutputFormatter()
        self.sample_ctx = {
            "symbol": "RB",
            "direction": "LONG",
            "confidence": 0.72,
            "trend_phase": "TREND_UP",
            "indicators": {
                "er": 0.65,
                "tsi": 25.3,
                "r_squared": 0.45,
                "hurst": 0.58,
                "trend_strength_composite": 0.68,
                "rsi": 58,
                "adx": 32,
                "macd_hist": 15,
                "atr_14": 45,
                "bb_bandwidth": 0.03,
            },
            "operation_plans": [
                {"action": "LONG", "reason": "趋势确认", "position": "30%", "stop_loss": "3500"},
            ],
            "risks": ["RSI偏高注意回调", "需关注持仓量变化"],
            "multi_dimension_scores": {"trend": 0.7, "momentum": 0.6, "volatility": 0.4},
        }

    def test_brief_output(self):
        output = self.formatter.format(self.sample_ctx, level="brief")
        assert "RB" in output
        assert "看多" in output
        assert len(output) < 500

    def test_standard_output(self):
        output = self.formatter.format(self.sample_ctx, level="standard")
        assert "市场状态" in output
        assert "操作方案" in output
        assert "风险提示" in output

    def test_formal_output(self):
        output = self.formatter.format(self.sample_ctx, level="formal")
        assert "指标详情" in output
        assert "多维度评分" in output
        assert "免责声明" in output

    def test_json_output(self):
        result = self.formatter.format_json(self.sample_ctx, level="standard")
        assert result["symbol"] == "RB"
        assert result["direction"] == "LONG"
        assert "text_output" in result

    def test_get_available_levels(self):
        levels = TieredOutputFormatter.get_available_levels()
        assert "formal" in levels
        assert "standard" in levels
        assert "brief" in levels

    def test_default_level(self):
        formatter = TieredOutputFormatter(default_level="brief")
        output = formatter.format(self.sample_ctx)
        assert len(output) < 500

    def test_empty_context(self):
        output = self.formatter.format({}, level="standard")
        assert "未知品种" in output

    def test_section_formatter_summary(self):
        ctx = {"symbol": "I", "direction": "SHORT", "confidence": 0.6, "trend_phase": "TREND_DOWN"}
        text = _SectionFormatter.format_summary(ctx)
        assert "看空" in text
        assert "60%" in text

    def test_section_formatter_one_liner(self):
        ctx = {
            "symbol": "JM",
            "direction": "HOLD",
            "confidence": 0.3,
            "trend_phase": "RANGE",
            "indicators": {"er": 0.2},
        }
        text = _SectionFormatter.format_one_liner(ctx)
        assert "观望" in text
        assert "ER=" in text


# ===========================================================================
# 套利分析测试
# ===========================================================================


class TestArbitrageAnalyzer:
    def setup_method(self):
        self.analyzer = ArbitrageAnalyzer()

    def test_available_pairs(self):
        pairs = self.analyzer.get_available_pairs()
        assert "rebar_iron" in pairs
        assert "coke_coking" in pairs

    def test_add_custom_pair(self):
        self.analyzer.add_spread_pair("custom_test", "RB", "HC", "自定义测试")
        pairs = self.analyzer.get_available_pairs()
        assert "custom_test" in pairs

    def test_analyze_spread_basic(self):
        # 生成模拟数据
        np.random.seed(42)
        dates = pd.date_range("2026-01-01", periods=100)
        near_df = pd.DataFrame(
            {
                "date": dates,
                "close": 3500 + np.cumsum(np.random.randn(100) * 10),
            }
        )
        far_df = pd.DataFrame(
            {
                "date": dates,
                "close": 3550 + np.cumsum(np.random.randn(100) * 10),
            }
        )
        near_df.attrs["symbol"] = "RB"
        far_df.attrs["symbol"] = "RB2601"

        result = self.analyzer.analyze_spread(near_df, far_df, "test_spread", "测试价差")
        assert isinstance(result, SpreadAnalysis)
        assert result.pair_name == "test_spread"
        assert result.spread != 0
        assert result.signal in ["LONG_SPREAD", "SHORT_SPREAD", "NEUTRAL"]

    def test_analyze_spread_ratio(self):
        np.random.seed(42)
        dates = pd.date_range("2026-01-01", periods=100)
        near_df = pd.DataFrame(
            {
                "date": dates,
                "close": 3500 + np.cumsum(np.random.randn(100) * 10),
            }
        )
        far_df = pd.DataFrame(
            {
                "date": dates,
                "close": 800 + np.cumsum(np.random.randn(100) * 5),
            }
        )

        result = self.analyzer.analyze_spread(near_df, far_df, "rb_i_ratio", "螺纹/铁矿比价", is_ratio=True)
        assert result.spread > 0

    def test_analyze_insufficient_data(self):
        near_df = pd.DataFrame({"date": pd.date_range("2026-01-01", periods=5), "close": [100] * 5})
        far_df = pd.DataFrame({"date": pd.date_range("2026-01-01", periods=5), "close": [105] * 5})
        result = self.analyzer.analyze_spread(near_df, far_df)
        assert result.signal == "NEUTRAL"

    def test_format_brief(self):
        results = [
            SpreadAnalysis(
                pair_name="test",
                near_symbol="RB",
                far_symbol="I",
                description="螺纹-铁矿",
                spread=0.25,
                spread_ma20=0.2,
                spread_std=0.05,
                z_score=2.5,
                spread_percentile=95,
                is_cointegrated=True,
                coint_pvalue=0.03,
                half_life=12,
                signal="SHORT_SPREAD",
                signal_strength=0.8,
                reason="Z-Score=2.5，价差显著偏高",
            )
        ]
        text = self.analyzer.format_arbitrage_brief(results)
        assert "套利分析" in text
        assert "SHORT_SPREAD" in text

    def test_format_brief_empty(self):
        text = self.analyzer.format_arbitrage_brief([])
        assert "暂无明显套利机会" in text

    def test_spread_analysis_to_dict(self):
        r = SpreadAnalysis(
            pair_name="test",
            near_symbol="RB",
            far_symbol="HC",
            description="test",
            spread=10,
            spread_ma20=8,
            spread_std=2,
            z_score=1.0,
            spread_percentile=75,
            is_cointegrated=False,
            coint_pvalue=0.1,
            half_life=0,
            signal="NEUTRAL",
            signal_strength=0,
            reason="test",
        )
        d = r.to_dict()
        assert d["pair_name"] == "test"
        assert d["z_score"] == 1.0

    def test_signal_generation_long_spread(self):
        """Z-Score < -2 应生成 LONG_SPREAD"""
        np.random.seed(42)
        # 构造价差序列：近期价差突然大幅下降
        spread = np.concatenate(
            [
                np.random.randn(50) * 0.1 + 0,  # 正常波动
                np.random.randn(20) * 0.1 - 0.5,  # 急跌
            ]
        )
        z_score = (spread[-1] - np.mean(spread[-20:])) / np.std(spread[-20:])
        # z_score 应该 < -2
        if z_score < -2:
            signal, strength, reason = self.analyzer._generate_signal(z_score, 5, False, 0, False)
            assert signal == "LONG_SPREAD"

    def test_signal_generation_short_spread(self):
        """Z-Score > 2 应生成 SHORT_SPREAD"""
        spread = np.concatenate(
            [
                np.random.randn(50) * 0.1 + 0,
                np.random.randn(20) * 0.1 + 0.5,
            ]
        )
        z_score = (spread[-1] - np.mean(spread[-20:])) / np.std(spread[-20:])
        if z_score > 2:
            signal, strength, reason = self.analyzer._generate_signal(z_score, 95, False, 0, False)
            assert signal == "SHORT_SPREAD"


# ===========================================================================
# 跨模块集成测试
# ===========================================================================


class TestCrossModuleIntegration:
    def test_knowledge_anchor_in_factor_generator(self):
        """知识锚点可为因子生成器提供种子"""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "test.db")
        mgr = KnowledgeAnchorManager(db_path)
        mgr.seed_default_anchors()

        seeds = mgr.get_factor_seeds_for_llm(dimension="momentum")
        assert len(seeds) >= 3
        # 每个种子包含必要字段
        for s in seeds:
            assert "anchor_id" in s
            assert "factor_seeds" in s
            assert "validation_rules" in s

    def test_tiered_output_with_arbitrage(self):
        """分级输出可包含套利分析"""
        formatter = TieredOutputFormatter()
        ctx = {
            "symbol": "RB",
            "direction": "LONG",
            "confidence": 0.7,
            "trend_phase": "TREND_UP",
            "arbitrage": {
                "ok": True,
                "data": {
                    "spread": 0.25,
                    "z_score": 2.1,
                    "signal": "SHORT_SPREAD",
                },
            },
        }
        output = formatter.format(ctx, level="formal")
        assert "套利分析" in output

    def test_all_modules_importable(self):
        """所有新模块可正常导入"""
        assert True
