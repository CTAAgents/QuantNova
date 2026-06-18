"""
趋势跟踪策略

基于技术指标和趋势分析的交易策略：
- Scanner: 主扫描器
- Strategy: 策略池

风险管理模块已迁移到 core/risk/
交易执行模块已迁移到 core/trading/
"""

from .scanner import TrendScanner
from .strategy import StrategyPool

# 从 core 层导入通用模块
from core.risk import RiskManager, PositionSizer, StopLossCalculator
from core.trading import ExecutionEngine, PortfolioManager

__all__ = [
    "TrendScanner",
    "StrategyPool",
    "RiskManager",
    "ExecutionEngine",
    "PositionSizer",
    "StopLossCalculator",
    "PortfolioManager",
]
