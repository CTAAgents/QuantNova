"""
波动幅度止损锚点模块

提供基于近期 K 线波动幅度中位数的止损参考锚点，用于增强 Reasoner 推理的数据支撑。

核心功能：
1. 波动幅度中位数计算
2. 止损锚点生成
3. 持仓止损计算

版本：v1.0
创建日期：2026-06-17
"""

import logging
from typing import Any

import numpy as np
import pandas as pd


logger = logging.getLogger(__name__)


class VolatilityAnchor:
    """
    波动幅度止损锚点计算器

    基于近期 K 线波动幅度中位数计算止损参考锚点。
    """

    def __init__(self, window: int = 20, multiplier: float = 2.0):
        """
        初始化波动幅度锚点计算器

        Args:
            window: 回看窗口大小（K 线数量）
            multiplier: 系数 Z，控制止损距离
        """
        self.window = window
        self.multiplier = multiplier

        logger.info(f"VolatilityAnchor 初始化完成，窗口={window}，系数={multiplier}")

    def calculate(self, df: pd.DataFrame) -> pd.Series:
        """
        计算波动幅度锚点

        Args:
            df: DataFrame with 'high' and 'low' columns

        Returns:
            pd.Series: 止损锚点值
        """
        if len(df) == 0:
            return pd.Series(dtype=float)

        # 计算 K 线高度
        candle_heights = df["high"] - df["low"]

        # 计算滚动中位数
        median_heights = candle_heights.rolling(window=self.window).median()

        # 计算锚点值
        anchor_values = median_heights * self.multiplier

        return anchor_values

    def calculate_for_position(self, df: pd.DataFrame, entry_price: float, direction: str) -> float:
        """
        计算特定持仓的止损锚点

        Args:
            df: DataFrame with 'high' and 'low' columns
            entry_price: 入场价格
            direction: 方向 ('long' 或 'short')

        Returns:
            float: 止损价格
        """
        if len(df) < self.window:
            logger.warning(f"数据长度 {len(df)} 不足窗口大小 {self.window}")
            return np.nan

        # 计算锚点值
        anchor_values = self.calculate(df)

        # 获取最新的锚点值
        latest_anchor = anchor_values.iloc[-1]

        if pd.isna(latest_anchor):
            return np.nan

        # 根据方向计算止损价格
        if direction == "long":
            # 多头止损 = 入场价 - 锚点值
            stop_loss = entry_price - latest_anchor
        elif direction == "short":
            # 空头止损 = 入场价 + 锚点值
            stop_loss = entry_price + latest_anchor
        else:
            raise ValueError(f"未知方向: {direction}，应为 'long' 或 'short'")

        return stop_loss

    def get_anchor_info(self, df: pd.DataFrame, entry_price: float, direction: str) -> dict[str, Any]:
        """
        获取锚点详细信息

        Args:
            df: DataFrame with 'high' and 'low' columns
            entry_price: 入场价格
            direction: 方向 ('long' 或 'short')

        Returns:
            Dict[str, Any]: 锚点详细信息
        """
        if len(df) < self.window:
            return {
                "anchor_value": np.nan,
                "stop_loss": np.nan,
                "candle_height_median": np.nan,
                "distance": np.nan,
                "distance_pct": np.nan,
            }

        # 计算锚点值
        anchor_values = self.calculate(df)
        latest_anchor = anchor_values.iloc[-1]

        # 计算 K 线高度中位数
        candle_heights = df["high"] - df["low"]
        median_height = candle_heights.rolling(window=self.window).median().iloc[-1]

        # 计算止损价格
        stop_loss = self.calculate_for_position(df, entry_price, direction)

        # 计算止损距离
        if direction == "long":
            distance = entry_price - stop_loss
        else:
            distance = stop_loss - entry_price

        # 计算止损距离百分比
        distance_pct = distance / entry_price * 100 if entry_price != 0 else 0

        return {
            "anchor_value": latest_anchor,
            "stop_loss": stop_loss,
            "candle_height_median": median_height,
            "distance": distance,
            "distance_pct": distance_pct,
            "window": self.window,
            "multiplier": self.multiplier,
        }


def volatility_anchor(df: pd.DataFrame, window: int = 20, multiplier: float = 2.0) -> pd.DataFrame:
    """
    便捷函数：计算波动幅度锚点

    Args:
        df: DataFrame with 'high' and 'low' columns
        window: 回看窗口大小
        multiplier: 系数 Z

    Returns:
        pd.DataFrame: 包含锚点值的 DataFrame
    """
    calculator = VolatilityAnchor(window=window, multiplier=multiplier)

    # 计算 K 线高度
    candle_heights = df["high"] - df["low"]

    # 计算锚点值
    anchor_values = calculator.calculate(df)

    result = pd.DataFrame({"candle_height": candle_heights, "anchor": anchor_values}, index=df.index)

    return result
