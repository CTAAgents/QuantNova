"""
进化工具层

提供策略进化和管理工具：
- EvolutionManager: 进化管理器
- TrajectoryAnalyzer: 轨迹分析
- TradeJournal: 交易日志
- StrategyHealthChecker: 策略健康度
- OverfittingDetector: 过拟合检测
- CircuitBreaker: 熔断器
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trend_scanner.evolution_manager import EvolutionManager
from trend_scanner.trajectory_analysis import TradeTrajectoryAnalyzer
from trend_scanner.trade_journal import TradeJournal
from trend_scanner.strategy_health import StrategyHealthChecker
from trend_scanner.overfitting_detector import OverfittingDetector
from trend_scanner.circuit_breaker import CircuitBreaker

__all__ = [
    "EvolutionManager",
    "TradeTrajectoryAnalyzer",
    "TradeJournal",
    "StrategyHealthChecker",
    "OverfittingDetector",
    "CircuitBreaker",
]
