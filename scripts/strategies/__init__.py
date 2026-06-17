"""
交易策略模块

包含各种独立的交易策略，与趋势跟踪策略并行运行：
- carry: Carry 策略（期限结构套利）
"""

from .carry import CarryAnalyzer, CarrySignal, analyze_carry

__all__ = [
    "CarryAnalyzer",
    "CarrySignal",
    "analyze_carry",
]
