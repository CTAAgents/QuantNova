"""
多周期 VGRSI 一致性因子测试模块

测试 MultiTimeframeVGRSIFactor 类。
覆盖：
1. 共识信号生成
2. 因子封装
3. 多时间框架对齐
4. 边界条件

创建日期：2026-06-17
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import numpy as np
import pandas as pd
from scripts.trend_scanner.visibility_graph import (
    MultiTimeframeVGRSIFactor,
    consensus_factor
)


class TestMultiTimeframeVGRSIFactor:
    """测试多周期 VGRSI 一致性因子"""
    
    def test_factor_initialization(self):
        """测试因子初始化"""
        factor = MultiTimeframeVGRSIFactor()
        
        assert 'M1' in factor.timeframe_configs
        assert 'M5' in factor.timeframe_configs
        assert 'M30' in factor.timeframe_configs
        assert factor.threshold_upper == 70.0
        assert factor.threshold_lower == 30.0
    
    def test_custom_config(self):
        """测试自定义配置"""
        configs = {
            'M1': {'window_size': 30, 'aggregation_mode': 'A0'},
            'M5': {'window_size': 60, 'aggregation_mode': 'A1'}
        }
        factor = MultiTimeframeVGRSIFactor(
            timeframe_configs=configs,
            threshold_upper=80.0,
            threshold_lower=20.0
        )
        
        assert 'M1' in factor.timeframe_configs
        assert 'M5' in factor.timeframe_configs
        assert 'M30' not in factor.timeframe_configs
        assert factor.threshold_upper == 80.0
        assert factor.threshold_lower == 20.0
    
    def test_calculate_basic(self):
        """测试基本的因子计算"""
        # 创建测试数据
        np.random.seed(42)
        dates_m1 = pd.date_range('2024-01-01', periods=200, freq='D')
        dates_m5 = pd.date_range('2024-01-01', periods=40, freq='5D')
        dates_m30 = pd.date_range('2024-01-01', periods=7, freq='30D')
        
        prices_dict = {
            'M1': pd.Series(np.cumsum(np.random.randn(200) * 0.1) + 100, index=dates_m1),
            'M5': pd.Series(np.cumsum(np.random.randn(40) * 0.1) + 100, index=dates_m5),
            'M30': pd.Series(np.cumsum(np.random.randn(7) * 0.1) + 100, index=dates_m30)
        }
        
        factor = MultiTimeframeVGRSIFactor()
        result = factor.calculate(prices_dict)
        
        assert isinstance(result, pd.Series)
        assert len(result) > 0
        # 共识因子值应该在 {-1, 0, 1} 中
        assert all(v in [-1, 0, 1] for v in result.unique())
    
    def test_generate_signals(self):
        """测试信号生成"""
        # 创建共识因子值
        consensus_values = pd.Series([0, 0, 1, 1, 1, 0, -1, -1, 0, 1])
        
        factor = MultiTimeframeVGRSIFactor()
        signals = factor.generate_signals(consensus_values)
        
        assert isinstance(signals, pd.Series)
        assert len(signals) == len(consensus_values)
        # 信号应该在 {-1, 0, 1} 中
        assert all(v in [-1, 0, 1] for v in signals.unique())
    
    def test_signal_generation_logic(self):
        """测试信号生成逻辑"""
        # 创建明确的共识因子序列
        consensus_values = pd.Series([0, 1, 1, 0, -1, -1, 0, 1])
        
        factor = MultiTimeframeVGRSIFactor()
        signals = factor.generate_signals(consensus_values)
        
        # 买入信号：从 0 或 -1 变为 1
        assert signals.iloc[1] == 1  # 0 -> 1
        # 卖出信号：从 0 或 1 变为 -1
        assert signals.iloc[4] == -1  # 0 -> -1
        # 无信号：保持不变
        assert signals.iloc[2] == 0  # 1 -> 1
        assert signals.iloc[5] == 0  # -1 -> -1


class TestConsensusFactorFunction:
    """测试共识因子便捷函数"""
    
    def test_consensus_factor_basic(self):
        """测试基本的共识因子计算"""
        # 创建测试数据
        np.random.seed(42)
        dates_m1 = pd.date_range('2024-01-01', periods=200, freq='D')
        dates_m5 = pd.date_range('2024-01-01', periods=40, freq='5D')
        dates_m30 = pd.date_range('2024-01-01', periods=7, freq='30D')
        
        prices_dict = {
            'M1': pd.Series(np.cumsum(np.random.randn(200) * 0.1) + 100, index=dates_m1),
            'M5': pd.Series(np.cumsum(np.random.randn(40) * 0.1) + 100, index=dates_m5),
            'M30': pd.Series(np.cumsum(np.random.randn(7) * 0.1) + 100, index=dates_m30)
        }
        
        result = consensus_factor(prices_dict)
        
        assert isinstance(result, pd.DataFrame)
        assert 'consensus' in result.columns
        assert 'signal' in result.columns
    
    def test_consensus_factor_with_config(self):
        """测试带配置的共识因子计算"""
        # 创建测试数据
        np.random.seed(42)
        dates_m1 = pd.date_range('2024-01-01', periods=200, freq='D')
        dates_m5 = pd.date_range('2024-01-01', periods=40, freq='5D')
        
        prices_dict = {
            'M1': pd.Series(np.cumsum(np.random.randn(200) * 0.1) + 100, index=dates_m1),
            'M5': pd.Series(np.cumsum(np.random.randn(40) * 0.1) + 100, index=dates_m5)
        }
        
        configs = {
            'M1': {'window_size': 30, 'aggregation_mode': 'A0'},
            'M5': {'window_size': 60, 'aggregation_mode': 'A0'}
        }
        
        result = consensus_factor(prices_dict, timeframe_configs=configs)
        
        assert isinstance(result, pd.DataFrame)
        assert 'consensus' in result.columns
        assert 'signal' in result.columns


class TestEdgeCases:
    """测试边界条件"""
    
    def test_empty_prices_dict(self):
        """测试空价格字典"""
        factor = MultiTimeframeVGRSIFactor()
        
        prices_dict = {}
        result = factor.calculate(prices_dict)
        
        assert isinstance(result, pd.Series)
        assert len(result) == 0
    
    def test_single_timeframe(self):
        """测试单个时间框架"""
        # 创建测试数据
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        prices_dict = {
            'M1': pd.Series(np.cumsum(np.random.randn(100) * 0.1) + 100, index=dates)
        }
        
        factor = MultiTimeframeVGRSIFactor()
        result = factor.calculate(prices_dict)
        
        assert isinstance(result, pd.Series)
        # 单时间框架时，共识因子应该等于该框架的信号
        assert len(result) > 0
    
    def test_constant_prices(self):
        """测试常数价格序列"""
        # 创建测试数据
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        prices_dict = {
            'M1': pd.Series([100.0] * 100, index=dates)
        }
        
        factor = MultiTimeframeVGRSIFactor()
        result = factor.calculate(prices_dict)
        
        assert isinstance(result, pd.Series)
        # 常数价格应该产生中性信号
        assert all(v == 0 for v in result.dropna())


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
