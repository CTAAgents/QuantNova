"""
IndicatorHub 单元测试

覆盖:
- 维度分组定义完整性
- 字段名映射正确性
- 缓存键生成
- get_latest / get_indicator_names 接口
- 宽表加载与维度分组

注意: 不测试实际 DuckDB 连接（需要 sync_indicators 运行后才有数据），
只测试纯逻辑部分。
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

from scripts.trend_scanner.indicator_hub import (
    IndicatorHub, DIMENSION_GROUPS, FIELD_NAME_MAP, REVERSE_FIELD_MAP
)


class TestDimensionGroups:
    """维度分组定义测试"""

    def test_five_dimensions_exist(self):
        assert set(DIMENSION_GROUPS.keys()) == {
            "trend", "momentum", "volume", "volatility", "channel"
        }

    def test_trend_has_core_indicators(self):
        trend = DIMENSION_GROUPS["trend"]
        assert "adx" in trend
        assert "ema20" in trend
        assert "sar" in trend
        assert "dkx" in trend

    def test_momentum_has_macd_rsi(self):
        mom = DIMENSION_GROUPS["momentum"]
        assert "macd" in mom
        assert "macd_signal" in mom
        assert "rsi" in mom
        assert "cci" in mom

    def test_volume_has_obv_mfi(self):
        vol = DIMENSION_GROUPS["volume"]
        assert "obv" in vol
        assert "mfi" in vol
        assert "vr" in vol

    def test_volatility_has_atr_bb(self):
        vol = DIMENSION_GROUPS["volatility"]
        assert "atr" in vol
        assert "bb_upper" in vol
        assert "bb_width" in vol

    def test_channel_has_donchian(self):
        ch = DIMENSION_GROUPS["channel"]
        assert "dc_upper" in ch
        assert "dc_mid" in ch
        assert "dc_lower" in ch

    def test_no_duplicate_indicators_across_dimensions(self):
        """各维度指标不重复"""
        all_indicators = []
        for indicators in DIMENSION_GROUPS.values():
            all_indicators.extend(indicators)
        assert len(all_indicators) == len(set(all_indicators))

    def test_total_indicator_count(self):
        """总指标数 >= 40（五维度筛选参与评分的指标）"""
        total = sum(len(v) for v in DIMENSION_GROUPS.values())
        assert total >= 40


class TestFieldNameMap:
    """字段名映射测试"""

    def test_reverse_map_is_consistent(self):
        """反向映射与正向映射一致"""
        for key, val in FIELD_NAME_MAP.items():
            assert REVERSE_FIELD_MAP[val] == key

    def test_key_mappings(self):
        assert FIELD_NAME_MAP["plus_di"] == "di_plus"
        assert FIELD_NAME_MAP["minus_di"] == "di_minus"
        assert FIELD_NAME_MAP["kdj_k"] == "stoch_k"
        assert FIELD_NAME_MAP["macd"] == "macd_line"
        assert FIELD_NAME_MAP["dc_upper"] == "donchian_upper"


class TestIndicatorHub:
    """IndicatorHub 核心逻辑测试"""

    def test_cache_key_generation(self):
        """缓存键基于 symbol + 最新日期"""
        hub = IndicatorHub.__new__(IndicatorHub)
        hub.db_path = ":memory:"
        hub.cache_dir = "/tmp/test_cache"
        hub._mem_cache = {}

        # mock duckdb connection
        with patch("duckdb.connect") as mock_conn:
            mock_instance = MagicMock()
            mock_instance.execute.return_value.fetchone.return_value = ("2026-01-01",)
            mock_conn.return_value = mock_instance

            key1 = hub._cache_key("DCE.jm")
            key2 = hub._cache_key("DCE.jm")
            key3 = hub._cache_key("SHFE.rb")

            assert key1 == key2  # 同品种同日期 → 相同键
            assert key1 != key3  # 不同品种 → 不同键

    def test_get_indicator_names(self):
        hub = IndicatorHub.__new__(IndicatorHub)
        hub.db_path = ":memory:"
        hub.cache_dir = "/tmp/test_cache"
        hub._mem_cache = {}

        names = hub.get_indicator_names()
        assert isinstance(names, list)
        assert len(names) >= 40
        assert "adx" in names
        assert "rsi" in names
        assert "obv" in names

    def test_get_dimensions_returns_dict(self):
        """get_dimensions 返回五个维度的 DataFrame"""
        hub = IndicatorHub.__new__(IndicatorHub)
        hub.db_path = ":memory:"
        hub.cache_dir = "/tmp/test_cache"
        hub._mem_cache = {}

        # mock load to return a DataFrame with some indicators
        mock_df = pd.DataFrame({
            "timestamp": pd.date_range("2026-01-01", periods=10),
            "adx": np.random.randn(10),
            "rsi": np.random.randn(10),
            "obv": np.random.randn(10),
            "atr": np.random.randn(10),
            "dc_upper": np.random.randn(10),
            "close": np.random.randn(10) + 100,
        })

        with patch.object(hub, "load", return_value=mock_df):
            dims = hub.get_dimensions("DCE.jm")

        assert isinstance(dims, dict)
        assert "trend" in dims
        assert "momentum" in dims
        assert "volume" in dims
        assert "volatility" in dims
        assert "channel" in dims

        # trend 维度应包含 adx
        assert "adx" in dims["trend"].columns

    def test_get_latest_returns_dict(self):
        """get_latest 返回扁平字典"""
        hub = IndicatorHub.__new__(IndicatorHub)
        hub.db_path = ":memory:"
        hub.cache_dir = "/tmp/test_cache"
        hub._mem_cache = {}

        mock_df = pd.DataFrame({
            "timestamp": pd.to_datetime(["2026-01-01"]),
            "adx": [25.0],
            "rsi": [55.0],
            "close": [100.0],
            "volume": [1000.0],
        })

        with patch.object(hub, "load", return_value=mock_df):
            latest = hub.get_latest("DCE.jm")

        assert isinstance(latest, dict)
        assert latest["adx"] == 25.0
        assert latest["rsi"] == 55.0
        assert latest["close"] == 100.0

    def test_clear_cache(self):
        hub = IndicatorHub.__new__(IndicatorHub)
        hub.db_path = ":memory:"
        hub.cache_dir = "/tmp/test_cache"
        hub._mem_cache = {("DCE.jm", "abc"): pd.DataFrame()}

        with patch("pathlib.Path.glob", return_value=[]):
            hub.clear_cache()

        assert len(hub._mem_cache) == 0


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_load_indicators_returns_dataframe(self):
        with patch.object(IndicatorHub, "load") as mock_load:
            mock_load.return_value = pd.DataFrame({"close": [100]})
            from scripts.trend_scanner.indicator_hub import load_indicators
            result = load_indicators("DCE.jm", db_path=":memory:")
            assert isinstance(result, pd.DataFrame)

    def test_get_dimensions_returns_dict(self):
        with patch.object(IndicatorHub, "get_dimensions") as mock_get:
            mock_get.return_value = {"trend": pd.DataFrame()}
            from scripts.trend_scanner.indicator_hub import get_dimensions
            result = get_dimensions("DCE.jm", db_path=":memory:")
            assert isinstance(result, dict)
            assert "trend" in result
