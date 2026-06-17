"""
套利策略

基于价差的套利交易策略：
- ArbitrageAnalyzer: 套利分析器
- SpreadData: 价差数据
- ArbitrageSignal: 套利信号
"""

from .arbitrage_analyzer import ArbitrageAnalyzer

__all__ = [
    "ArbitrageAnalyzer",
]
