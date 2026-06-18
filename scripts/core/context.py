"""
上下文组装模块

感知层的核心组件，负责：
1. 计算技术指标
2. 组装 MarketContext
3. 集成基本面分析
4. 集成风险评估（Algometrics）
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd

from .models import (
    FundamentalContext,
    IndicatorSnapshot,
    MarketContext,
    MarketStructure,
    MomentumState,
    TrendPhase,
    VolatilityState,
)

logger = logging.getLogger(__name__)


class ContextAssembler:
    """
    上下文组装器

    将原始K线数据转换为结构化的 MarketContext，
    供推理层使用。
    """

    def __init__(self, symbol: str, timeframe: str = "daily"):
        """
        初始化上下文组装器

        Args:
            symbol: 品种代码
            timeframe: 时间周期
        """
        self.symbol = symbol
        self.timeframe = timeframe

        # 风险评估器（可选集成）
        self._crowding_detector = None
        self._deployment_risk_estimator = None

        self._init_risk_modules()

    def _init_risk_modules(self):
        """初始化风险评估模块"""
        try:
            import sys
            from pathlib import Path
            
            # 添加项目根目录到路径
            project_root = Path(__file__).parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            
            from scripts.risk import CrowdingDetector, DeploymentRiskEstimator

            self._crowding_detector = CrowdingDetector()
            self._deployment_risk_estimator = DeploymentRiskEstimator()
            logger.info("风险评估模块加载成功")
        except ImportError as e:
            logger.warning(f"风险评估模块未找到，跳过集成: {e}")

    def assemble(
        self,
        df: pd.DataFrame,
        fundamental: Optional[FundamentalContext] = None,
    ) -> MarketContext:
        """
        组装市场上下文

        Args:
            df: 包含 OHLCV 数据的 DataFrame
            fundamental: 基本面上下文（可选）

        Returns:
            MarketContext: 结构化市场上下文
        """
        # 1. 计算技术指标
        snapshot = self._calculate_indicators(df)

        # 2. 分析市场结构
        structure = self._analyze_structure(df, snapshot)

        # 3. 分析动量状态
        momentum = self._analyze_momentum(snapshot)

        # 4. 分析波动率
        volatility = self._analyze_volatility(df, snapshot)

        # 5. 判断趋势阶段
        trend_phase = self._determine_trend_phase(
            structure, momentum, volatility, df
        )

        # 6. 计算价格行为统计
        price_stats = self._calculate_price_stats(df)

        # 7. 组装 MarketContext
        context = MarketContext(
            symbol=self.symbol,
            timestamp=str(df.index[-1]) if len(df) > 0 else "",
            timeframe=self.timeframe,
            current_price=float(df["close"].iloc[-1]) if len(df) > 0 else 0.0,
            price_change_pct=float(df["close"].pct_change().iloc[-1] * 100)
            if len(df) > 1
            else 0.0,
            structure=structure,
            momentum=momentum,
            volatility=volatility,
            trend_phase=trend_phase,
            snapshot=snapshot,
            bars_since_high=price_stats.get("bars_since_high", 0),
            bars_since_low=price_stats.get("bars_since_low", 0),
            consecutive_up_days=price_stats.get("consecutive_up_days", 0),
            consecutive_down_days=price_stats.get("consecutive_down_days", 0),
            fundamental=fundamental or FundamentalContext(),
        )

        # 8. 集成风险评估（Algometrics）
        context = self._integrate_risk_assessment(context, df)

        return context

    def _calculate_indicators(self, df: pd.DataFrame) -> IndicatorSnapshot:
        """计算技术指标快照"""
        if len(df) == 0:
            return IndicatorSnapshot(
                timestamp="",
                close=0.0,
                high=0.0,
                low=0.0,
                open=0.0,
                volume=0.0,
            )

        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        volume = df["volume"].values

        snapshot = IndicatorSnapshot(
            timestamp=str(df.index[-1]),
            close=float(close[-1]),
            high=float(high[-1]),
            low=float(low[-1]),
            open=float(df["open"].iloc[-1]),
            volume=float(volume[-1]),
        )

        # 简化的指标计算
        snapshot.ema20 = float(self._ema(close, 20)[-1]) if len(close) >= 20 else 0.0
        snapshot.ema60 = float(self._ema(close, 60)[-1]) if len(close) >= 60 else 0.0
        snapshot.rsi = float(self._rsi(close, 14)[-1]) if len(close) >= 15 else 50.0
        snapshot.atr = float(self._atr(high, low, close, 14)[-1]) if len(close) >= 15 else 0.0

        return snapshot

    def _ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """计算EMA"""
        alpha = 2 / (period + 1)
        ema = np.zeros_like(data, dtype=float)
        ema[0] = data[0]
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i - 1]
        return ema

    def _rsi(self, data: np.ndarray, period: int) -> np.ndarray:
        """计算RSI"""
        deltas = np.diff(data)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.zeros(len(data))
        avg_loss = np.zeros(len(data))

        if len(gains) >= period:
            avg_gain[period] = np.mean(gains[:period])
            avg_loss[period] = np.mean(losses[:period])

            for i in range(period + 1, len(data)):
                avg_gain[i] = (avg_gain[i - 1] * (period - 1) + gains[i - 1]) / period
                avg_loss[i] = (avg_loss[i - 1] * (period - 1) + losses[i - 1]) / period

        rs = np.where(avg_loss > 0, avg_gain / avg_loss, 100)
        rsi = 100 - 100 / (1 + rs)
        return rsi

    def _atr(
        self, high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int
    ) -> np.ndarray:
        """计算ATR"""
        tr = np.maximum(high[1:] - low[1:], 
                       np.maximum(abs(high[1:] - close[:-1]), 
                                 abs(low[1:] - close[:-1])))
        tr = np.insert(tr, 0, high[0] - low[0])

        atr = np.zeros_like(tr)
        atr[period - 1] = np.mean(tr[:period])
        for i in range(period, len(tr)):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
        return atr

    def _analyze_structure(
        self, df: pd.DataFrame, snapshot: IndicatorSnapshot
    ) -> MarketStructure:
        """分析市场结构"""
        structure = MarketStructure()

        if len(df) == 0:
            return structure

        close = df["close"].values

        # 均线排列
        if snapshot.ema20 > snapshot.ema60:
            structure.ma_arrangement = "BULLISH"
        elif snapshot.ema20 < snapshot.ema60:
            structure.ma_arrangement = "BEARISH"
        else:
            structure.ma_arrangement = "NEUTRAL"

        # 价格位置
        current_price = close[-1]
        if current_price > snapshot.ema20:
            structure.price_vs_ma = "ABOVE_EMA20"
        elif current_price > snapshot.ema60:
            structure.price_vs_ma = "BETWEEN_EMA"
        else:
            structure.price_vs_ma = "BELOW_EMA60"

        return structure

    def _analyze_momentum(self, snapshot: IndicatorSnapshot) -> MomentumState:
        """分析动量状态"""
        momentum = MomentumState()

        # RSI状态
        if snapshot.rsi > 70:
            momentum.rsi_state = "OVERBOUGHT"
        elif snapshot.rsi < 30:
            momentum.rsi_state = "OVERSOLD"
        else:
            momentum.rsi_state = "NEUTRAL"

        momentum.rsi_value = snapshot.rsi

        return momentum

    def _analyze_volatility(
        self, df: pd.DataFrame, snapshot: IndicatorSnapshot
    ) -> VolatilityState:
        """分析波动率"""
        volatility = VolatilityState()

        if len(df) == 0 or snapshot.atr == 0:
            return volatility

        current_price = df["close"].iloc[-1]
        if current_price > 0:
            volatility.atr_pct = (snapshot.atr / current_price) * 100

        # 波动率状态
        if volatility.atr_pct > 3:
            volatility.regime = "HIGH"
        elif volatility.atr_pct < 1:
            volatility.regime = "LOW"
        else:
            volatility.regime = "NORMAL"

        return volatility

    def _determine_trend_phase(
        self,
        structure: MarketStructure,
        momentum: MomentumState,
        volatility: VolatilityState,
        df: pd.DataFrame,
    ) -> TrendPhase:
        """判断趋势阶段"""
        phase = TrendPhase()

        # 简化的趋势判断
        if structure.ma_arrangement == "BULLISH":
            if momentum.rsi_state == "OVERBOUGHT":
                phase.phase = "MATURE"
                phase.confidence = 0.7
            else:
                phase.phase = "DEVELOPING"
                phase.confidence = 0.6
        elif structure.ma_arrangement == "BEARISH":
            if momentum.rsi_state == "OVERSOLD":
                phase.phase = "FATIGUING"
                phase.confidence = 0.7
            else:
                phase.phase = "DEVELOPING"
                phase.confidence = 0.6
        else:
            phase.phase = "CONSOLIDATING"
            phase.confidence = 0.5

        return phase

    def _calculate_price_stats(self, df: pd.DataFrame) -> dict:
        """计算价格行为统计"""
        stats = {
            "bars_since_high": 0,
            "bars_since_low": 0,
            "consecutive_up_days": 0,
            "consecutive_down_days": 0,
        }

        if len(df) == 0:
            return stats

        close = df["close"].values

        # 距离高点
        high_idx = np.argmax(close)
        stats["bars_since_high"] = len(close) - 1 - high_idx

        # 距离低点
        low_idx = np.argmin(close)
        stats["bars_since_low"] = len(close) - 1 - low_idx

        # 连续上涨/下跌天数
        if len(close) > 1:
            for i in range(len(close) - 1, 0, -1):
                if close[i] > close[i - 1]:
                    stats["consecutive_up_days"] += 1
                else:
                    break

            for i in range(len(close) - 1, 0, -1):
                if close[i] < close[i - 1]:
                    stats["consecutive_down_days"] += 1
                else:
                    break

        return stats

    def _integrate_risk_assessment(
        self, context: MarketContext, df: pd.DataFrame
    ) -> MarketContext:
        """
        集成风险评估（Algometrics 论文实现）

        评估拥挤度和部署风险
        """
        if self._crowding_detector is None:
            return context

        try:
            # 计算风险指标
            signal = context.trend_phase.confidence * (
                1 if context.structure.ma_arrangement == "BULLISH" else -1
            )
            market_volume = float(df["volume"].iloc[-1]) if len(df) > 0 else 1000
            price_change = context.price_change_pct
            order_flow = signal * market_volume * 0.1  # 简化估算

            # 检测拥挤度
            crowding_metrics = self._crowding_detector.detect(
                signal=signal,
                market_volume=market_volume,
                price_change=price_change,
                order_flow=order_flow,
            )

            # 更新上下文
            context.crowding_score = crowding_metrics.crowding_score
            context.crowding_level = crowding_metrics.level.value

            # 估算部署风险
            if self._deployment_risk_estimator is not None:
                from .risk.deployment_risk import ModelPerformance

                model = ModelPerformance(
                    model_name="current_strategy",
                    historical_accuracy=0.6,
                    signal_strength=abs(signal),
                    trading_frequency=0.5,
                    position_size=0.3,
                )
                assessment = self._deployment_risk_estimator.assess(model)
                context.deployment_risk = assessment.deployment_risk
                context.feedback_gap = assessment.feedback_gap

            logger.debug(
                f"风险评估完成: 拥挤度={context.crowding_level}, "
                f"部署风险={context.deployment_risk:.3f}"
            )

        except Exception as e:
            logger.warning(f"风险评估失败: {e}")

        return context
