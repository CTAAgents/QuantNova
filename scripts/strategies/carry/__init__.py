"""
Carry 策略模块

基于 Carry 策略深度解析，实现：
- 展期收益率计算
- 期限结构斜率分析
- 库存数据分析（三层加速度框架）
- 品种 Carry 信号生成

核心思想：
Carry 策略的本质是赚取期货曲线形态（Contango/Backwardation）带来的展期收益，
而非押注价格方向。成功的 Carry 交易需要精确量化曲线形态、用库存数据验证结构
持续性，并严格遵守交割规则。
"""

from .carry_analyzer import (
    CarryAnalyzer,
    CarrySignal,
    InventoryData,
    TermStructure,
    analyze_carry,
)

__all__ = [
    "CarryAnalyzer",
    "CarrySignal",
    "InventoryData",
    "TermStructure",
    "analyze_carry",
]
