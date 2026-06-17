"""
策略层

包含各种独立的交易策略：
- trend_following: 趋势跟踪策略
- carry: Carry 策略（期限结构套利）
- arbitrage: 套利策略
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trend_scanner.scanner import TrendScanner
from trend_scanner.arbitrage_analyzer import ArbitrageAnalyzer

# Carry 策略是独立模块，直接导入
from .carry import CarryAnalyzer

__all__ = [
    "TrendScanner",
    "ArbitrageAnalyzer",
    "CarryAnalyzer",
]
