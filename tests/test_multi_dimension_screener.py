"""
MultiDimensionScreener 单元测试

覆盖:
- 五维度权重配置
- 归一化规则（bounded/directional/position/volume/channel）
- 维度评分与综合评分
- 信号分类（LONG/SHORT/NEUTRAL）
- 维度一致性计算
- 空 DataFrame 边界条件
- MultiDimensionResult.to_dict() 序列化
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import numpy as np
import pandas as pd

from scripts.trend_scanner.multi_dimension_screener import (
    MultiDimensionScreener, MultiDimensionResult, DimensionScore,
    DIMENSION_WEIGHTS, DIMENSION_INDICATORS
)


class TestDimensionWeights:
    """维度权重配置测试"""

    def test_five_dimensions(self):
        assert set(DIMENSION_WEIGHTS.keys()) == {
            "trend", "momentum", "volume", "volatility", "channel"
        }

    def test_weights_sum_to_one(self):
        total = sum(DIMENSION_WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_trend_highest_weight(self):
        assert DIMENSION_WEIGHTS["trend"] >= DIMENSION_WEIGHTS["momentum"]
        assert DIMENSION_WEIGHTS["trend"] >= DIMENSION_WEIGHTS["volume"]

    def test_channel_lowest_weight(self):
        assert DIMENSION_WEIGHTS["channel"] <= DIMENSION_WEIGHTS["volatility"]


class TestDimensionIndicators:
    """维度指标定义测试"""

    def test_all_five_dimensions_have_indicators(self):
        for dim in ["trend", "momentum", "volume", "volatility", "channel"]:
            assert dim in DIMENSION_INDICATORS
            assert len(DIMENSION_INDICATORS[dim]) >= 2

    def test_indicator_format(self):
        """每个指标定义格式正确: (name, neutral, lo, hi, scaling)"""
        for dim, indicators in DIMENSION_INDICATORS.items():
            for ind in indicators:
                assert len(ind) == 5
                name, neutral, lo, hi, scaling = ind
                assert isinstance(name, str)
                assert isinstance(neutral, (int, float))
                assert scaling in ("bounded", "directional", "position",
                                   "volume", "channel_upper", "channel_lower")


class TestNormalizationRules:
    """归一化规则测试"""

    def test_bounded_above_neutral(self):
        """有界指标：值 > 中性点 → 正分"""
        score = MultiDimensionScreener._normalize_bounded(70, 50, 0, 100)
        assert score > 0
        assert score <= 1.0

    def test_bounded_below_neutral(self):
        """有界指标：值 < 中性点 → 负分"""
        score = MultiDimensionScreener._normalize_bounded(30, 50, 0, 100)
        assert score < 0
        assert score >= -1.0

    def test_bounded_at_neutral(self):
        """有界指标：值 = 中性点 → 0"""
        score = MultiDimensionScreener._normalize_bounded(50, 50, 0, 100)
        assert score == 0.0

    def test_bounded_clamped(self):
        """有界指标：超出范围时钳位到 ±1"""
        score_high = MultiDimensionScreener._normalize_bounded(150, 50, 0, 100)
        score_low = MultiDimensionScreener._normalize_bounded(-50, 50, 0, 100)
        assert score_high == 1.0
        assert score_low == -1.0

    def test_directional_positive(self):
        """方向性指标：正值 → 正分"""
        score = MultiDimensionScreener._normalize_directional(50, -100, 100)
        assert score > 0

    def test_directional_negative(self):
        """方向性指标：负值 → 负分"""
        score = MultiDimensionScreener._normalize_directional(-50, -100, 100)
        assert score < 0

    def test_directional_zero(self):
        score = MultiDimensionScreener._normalize_directional(0, -100, 100)
        assert score == 0.0


class TestMultiDimensionScreener:
    """MultiDimensionScreener 核心功能测试"""

    def setup_method(self):
        self.screener = MultiDimensionScreener()

    def _make_df(self, rows=20):
        """构造测试用 DataFrame"""
        np.random.seed(42)
        n = rows
        df = pd.DataFrame({
            "timestamp": pd.date_range("2026-01-01", periods=n, freq="D"),
            "close": np.linspace(100, 110, n),
            "high": np.linspace(102, 112, n),
            "low": np.linspace(98, 108, n),
            "open": np.linspace(100, 110, n),
            "volume": np.random.randint(1000, 5000, n).astype(float),
            # trend
            "adx": np.linspace(20, 40, n),
            "plus_di": np.linspace(25, 35, n),
            "minus_di": np.linspace(20, 15, n),
            "sar": np.linspace(95, 105, n),
            "dkx": np.linspace(98, 108, n),
            "ema20": np.linspace(99, 109, n),
            "ema60": np.linspace(97, 107, n),
            "adxr": np.linspace(18, 38, n),
            "ma20_slope": np.linspace(0.1, 0.5, n),
            "ma60_slope": np.linspace(0.05, 0.3, n),
            "lon": np.linspace(45, 55, n),
            "spread_ma20_ma60": np.linspace(1, 3, n),
            # momentum
            "macd": np.linspace(-10, 30, n),
            "macd_hist": np.linspace(-5, 15, n),
            "rsi": np.linspace(40, 65, n),
            "kdj_k": np.linspace(35, 70, n),
            "roc": np.linspace(-2, 5, n),
            "mtm": np.linspace(-10, 20, n),
            "wr": np.linspace(60, 35, n),
            "cci": np.linspace(-50, 150, n),
            "priceosc": np.linspace(-1, 3, n),
            "b36": np.linspace(-5, 10, n),
            "b612": np.linspace(-8, 15, n),
            # volume
            "mfi": np.linspace(40, 65, n),
            "vr": np.linspace(80, 150, n),
            "vroc": np.linspace(-10, 20, n),
            "obv": np.linspace(1000, 2000, n),
            # volatility
            "atr_ratio": np.linspace(0.8, 1.5, n),
            "bb_width": np.linspace(0.02, 0.05, n),
            "mass": np.linspace(22, 28, n),
            # channel
            "dc_upper": np.linspace(102, 112, n),
            "dc_lower": np.linspace(98, 108, n),
            "bb_upper": np.linspace(103, 113, n),
            "bb_lower": np.linspace(97, 107, n),
            "hcl_upper": np.linspace(104, 114, n),
            "hcl_lower": np.linspace(96, 106, n),
            "env_upper": np.linspace(101, 111, n),
            "env_lower": np.linspace(99, 109, n),
        })
        return df

    def test_score_returns_result(self):
        df = self._make_df()
        result = self.screener.score("DCE.jm", df)
        assert isinstance(result, MultiDimensionResult)
        assert result.symbol == "DCE.jm"
        assert len(result.dimensions) == 5

    def test_score_range(self):
        """综合得分在 [-1, +1] 范围内"""
        df = self._make_df()
        result = self.screener.score("DCE.jm", df)
        assert -1.0 <= result.overall_score <= 1.0

    def test_signal_classification(self):
        """信号分类正确"""
        df = self._make_df()
        result = self.screener.score("DCE.jm", df)
        assert result.signal in ("LONG", "SHORT", "NEUTRAL")

    def test_confidence_range(self):
        """置信度在 [0, 1] 范围内"""
        df = self._make_df()
        result = self.screener.score("DCE.jm", df)
        assert 0.0 <= result.confidence <= 1.0

    def test_empty_df(self):
        """空 DataFrame 返回 NEUTRAL"""
        result = self.screener.score("DCE.jm", pd.DataFrame())
        assert result.signal == "NEUTRAL"
        assert result.overall_score == 0.0

    def test_bullish_signal(self):
        """构造明确多头场景"""
        df = self._make_df()
        # 最后一行：强势多头
        df.loc[df.index[-1], "adx"] = 60
        df.loc[df.index[-1], "plus_di"] = 50
        df.loc[df.index[-1], "minus_di"] = 10
        df.loc[df.index[-1], "rsi"] = 75
        df.loc[df.index[-1], "macd_hist"] = 40
        df.loc[df.index[-1], "mfi"] = 75

        result = self.screener.score("DCE.jm", df)
        # 应该偏多
        assert result.overall_score > 0

    def test_bearish_signal(self):
        """构造明确空头场景"""
        np.random.seed(42)
        n = 20
        df = pd.DataFrame({
            "timestamp": pd.date_range("2026-01-01", periods=n, freq="D"),
            "close": np.linspace(110, 95, n),  # 下跌趋势
            "high": np.linspace(112, 97, n),
            "low": np.linspace(108, 93, n),
            "open": np.linspace(110, 95, n),
            "volume": np.random.randint(1000, 5000, n).astype(float),
            # trend - 空头
            "adx": np.linspace(30, 55, n),
            "plus_di": np.linspace(20, 10, n),
            "minus_di": np.linspace(30, 50, n),
            "sar": np.linspace(115, 100, n),  # SAR 在价格上方
            "dkx": np.linspace(112, 97, n),
            "ema20": np.linspace(112, 97, n),
            "ema60": np.linspace(114, 99, n),
            "adxr": np.linspace(28, 50, n),
            "ma20_slope": np.linspace(-0.1, -0.8, n),
            "ma60_slope": np.linspace(-0.05, -0.5, n),
            "lon": np.linspace(55, 35, n),
            "spread_ma20_ma60": np.linspace(-1, -5, n),
            # momentum - 空头
            "macd": np.linspace(10, -40, n),
            "macd_hist": np.linspace(5, -30, n),
            "rsi": np.linspace(60, 25, n),
            "kdj_k": np.linspace(65, 30, n),
            "roc": np.linspace(3, -6, n),
            "mtm": np.linspace(15, -30, n),
            "wr": np.linspace(40, 75, n),
            "cci": np.linspace(100, -200, n),
            "priceosc": np.linspace(2, -4, n),
            "b36": np.linspace(8, -15, n),
            "b612": np.linspace(10, -20, n),
            # volume - 空头
            "mfi": np.linspace(60, 30, n),
            "vr": np.linspace(150, 60, n),
            "vroc": np.linspace(15, -20, n),
            "obv": np.linspace(2000, 500, n),
            # volatility
            "atr_ratio": np.linspace(0.9, 1.4, n),
            "bb_width": np.linspace(0.03, 0.04, n),
            "mass": np.linspace(25, 28, n),
            # channel - 价格在通道下方
            "dc_upper": np.linspace(114, 100, n),
            "dc_lower": np.linspace(106, 90, n),
            "bb_upper": np.linspace(115, 101, n),
            "bb_lower": np.linspace(105, 89, n),
            "hcl_upper": np.linspace(116, 102, n),
            "hcl_lower": np.linspace(104, 88, n),
            "env_upper": np.linspace(113, 99, n),
            "env_lower": np.linspace(107, 91, n),
        })
        result = self.screener.score("DCE.jm", df)
        assert result.overall_score < 0

    def test_custom_weights(self):
        """自定义权重不影响功能"""
        custom = MultiDimensionScreener(weights={
            "trend": 0.5, "momentum": 0.2, "volume": 0.1,
            "volatility": 0.1, "channel": 0.1,
        })
        df = self._make_df()
        result = custom.score("DCE.jm", df)
        assert isinstance(result, MultiDimensionResult)

    def test_weight_auto_normalize(self):
        """权重总和不为1时自动归一化"""
        screener = MultiDimensionScreener(weights={
            "trend": 6, "momentum": 5, "volume": 4,
            "volatility": 3, "channel": 2,
        })
        total = sum(screener.weights.values())
        assert abs(total - 1.0) < 0.01


class TestMultiDimensionResult:
    """MultiDimensionResult 数据类测试"""

    def test_to_dict(self):
        result = MultiDimensionResult(
            symbol="DCE.jm",
            timestamp="2026-01-01T00:00:00",
            dimensions=[
                DimensionScore(
                    name="trend", weight=0.3,
                    indicator_scores={"adx": 0.5, "rsi": -0.2},
                    composite=0.3, direction="BULLISH", confidence=0.7,
                ),
            ],
            overall_score=0.3,
            confidence=0.7,
            signal="LONG",
        )
        d = result.to_dict()
        assert d["symbol"] == "DCE.jm"
        assert d["signal"] == "LONG"
        assert len(d["dimensions"]) == 1
        assert d["dimensions"][0]["name"] == "trend"

    def test_to_dict_rounds_values(self):
        result = MultiDimensionResult(
            symbol="TEST",
            overall_score=0.123456,
            confidence=0.789012,
            signal="NEUTRAL",
        )
        d = result.to_dict()
        assert d["overall_score"] == 0.1235
        assert d["confidence"] == 0.789
