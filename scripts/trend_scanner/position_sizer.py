"""
仓位管理模块

实现多种仓位优化算法：
- 凯利公式：基于胜率和盈亏比计算最优仓位
- 风险平价：基于波动率的资产权重分配
- 自适应仓位：根据趋势强度和波动率动态调整

设计原则：
- 仓位是策略的核心，不是附属品
- 凯利公式是理论最优，但实际使用半凯利（0.5x）降低风险
- 波动率调整：高波动时减仓，低波动时加仓

文件：scripts/trend_scanner/position_sizer.py
"""

import logging
from typing import Any

import numpy as np


logger = logging.getLogger(__name__)


class PositionSizer:
    """
    仓位优化器

    提供多种仓位计算方法，根据市场状态动态调整仓位。
    """

    def __init__(self, max_position: float = 1.0, kelly_fraction: float = 0.5):
        """
        初始化仓位优化器

        Args:
            max_position: 最大仓位比例（默认 1.0 = 100%）
            kelly_fraction: 凯利系数（默认 0.5 = 半凯利，更保守）
        """
        self.max_position = max_position
        self.kelly_fraction = kelly_fraction

    def kelly(self, win_rate: float, win_loss_ratio: float) -> float:
        """
        凯利公式计算最优仓位

        公式：f* = p - (1-p)/b
        其中 p=胜率，b=盈亏比

        Args:
            win_rate: 胜率（0-1）
            win_loss_ratio: 盈亏比（平均盈利/平均亏损）

        Returns:
            最优仓位比例（0-1）
        """
        if win_rate <= 0 or win_rate >= 1:
            return 0.0
        if win_loss_ratio <= 0:
            return 0.0

        # 凯利公式
        kelly = win_rate - (1 - win_rate) / win_loss_ratio

        # 应用凯利系数（半凯利更保守）
        position = kelly * self.kelly_fraction

        # 限制在合理范围
        return max(0.0, min(position, self.max_position))

    def risk_parity(self, volatilities: list[float]) -> list[float]:
        """
        风险平价仓位分配

        每个资产对组合风险的贡献相等。

        Args:
            volatilities: 各资产的波动率列表

        Returns:
            各资产的权重列表
        """
        if not volatilities:
            return []

        vol_array = np.array(volatilities)

        # 避免除零
        vol_array = np.maximum(vol_array, 1e-8)

        # 风险平价权重 = 1/vol 归一化
        inv_vol = 1.0 / vol_array
        weights = inv_vol / inv_vol.sum()

        return weights.tolist()

    def adaptive(
        self,
        trend_strength: float,
        volatility: float,
        base_vol: float = 0.2,
        win_rate: float = 0.55,
        win_loss_ratio: float = 1.5,
    ) -> float:
        """
        自适应仓位：综合考虑趋势强度和波动率

        逻辑：
        - 趋势强时加仓（最高 1.5x）
        - 高波动时减仓（波动率翻倍则仓位减半）
        - 基础仓位来自凯利公式

        Args:
            trend_strength: 趋势强度（0-1）
            volatility: 当前波动率
            base_vol: 基准波动率（默认 20%）
            win_rate: 胜率
            win_loss_ratio: 盈亏比

        Returns:
            建议仓位比例（0-1）
        """
        # 基础仓位（凯利公式）
        base = self.kelly(win_rate, win_loss_ratio)

        # 趋势加成：趋势越强，仓位越大
        trend_factor = min(trend_strength / 0.5, 1.5)

        # 波动率调整：高波动减仓，低波动加仓
        vol_factor = base_vol / max(volatility, 0.05)
        vol_factor = max(0.5, min(vol_factor, 2.0))  # 限制在 0.5-2.0

        # 最终仓位
        position = base * trend_factor * vol_factor

        return max(0.0, min(position, self.max_position))

    def pyramid(
        self,
        current_position: float,
        entry_price: float,
        current_price: float,
        atr: float,
        direction: str,
        max_additions: int = 3,
    ) -> dict[str, Any]:
        """
        金字塔加仓：趋势延续时逐步加仓

        Args:
            current_position: 当前仓位
            entry_price: 入场价
            current_price: 当前价
            atr: ATR 值
            direction: 方向（LONG/SHORT）
            max_additions: 最大加仓次数

        Returns:
            {'should_add': bool, 'add_size': float, 'reason': str}
        """
        # 计算已加仓次数
        if current_position <= 0:
            return {"should_add": False, "add_size": 0, "reason": "无持仓"}

        # 计算浮动盈亏（以 ATR 为单位）
        if direction == "LONG":
            profit_in_atr = (current_price - entry_price) / max(atr, 1e-8)
        else:
            profit_in_atr = (entry_price - current_price) / max(atr, 1e-8)

        # 盈利超过 1.5 倍 ATR 才考虑加仓
        if profit_in_atr < 1.5:
            return {"should_add": False, "add_size": 0, "reason": "盈利不足"}

        # 每次加仓递减：首次 50%，第二次 30%，第三次 20%
        add_ratios = [0.5, 0.3, 0.2]
        additions_done = int(current_position / 0.3)  # 估算已加仓次数

        if additions_done >= max_additions:
            return {"should_add": False, "add_size": 0, "reason": "已达最大加仓次数"}

        add_size = add_ratios[additions_done] * current_position

        return {
            "should_add": True,
            "add_size": round(add_size, 4),
            "reason": f"盈利 {profit_in_atr:.1f} ATR，第 {additions_done + 1} 次加仓",
        }

    def calculate(
        self,
        trend_strength: float,
        volatility: float,
        win_rate: float = 0.55,
        win_loss_ratio: float = 1.5,
        method: str = "adaptive",
    ) -> dict[str, Any]:
        """
        统一计算接口

        Args:
            trend_strength: 趋势强度（0-1）
            volatility: 当前波动率
            win_rate: 胜率
            win_loss_ratio: 盈亏比
            method: 计算方法（kelly/risk_parity/adaptive）

        Returns:
            仓位计算结果
        """
        if method == "kelly":
            position = self.kelly(win_rate, win_loss_ratio)
        elif method == "adaptive":
            position = self.adaptive(trend_strength, volatility, win_rate=win_rate, win_loss_ratio=win_loss_ratio)
        else:
            position = self.adaptive(trend_strength, volatility, win_rate=win_rate, win_loss_ratio=win_loss_ratio)

        return {
            "method": method,
            "position_size": round(position, 4),
            "position_pct": f"{position * 100:.1f}%",
            "inputs": {
                "trend_strength": trend_strength,
                "volatility": volatility,
                "win_rate": win_rate,
                "win_loss_ratio": win_loss_ratio,
            },
            "risk_metrics": {
                "max_loss_pct": f"{position * volatility * 2 * 100:.1f}%",  # 2 倍波动率作为最大亏损估计
                "kelly_optimal": f"{self.kelly(win_rate, win_loss_ratio) * 100:.1f}%",
            },
        }
