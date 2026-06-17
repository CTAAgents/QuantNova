"""
Carry 策略分析模块

基于 Carry 策略深度解析，实现：
- 展期收益率计算
- 期限结构斜率分析
- 库存数据分析（三层加速度框架）
- 品种 Carry 信号生成

核心思想：
Carry 策略的本质是赚取期货曲线形态（Contango/Backwardation）带来的展期收益，
而非押注价格方向。成功的 Carry 交易需要精确量化曲线形态、用库存数据验证结构
持续性，并严格遵守交割规则。

版本：v1.0
创建日期：2026-06-18
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class TermStructure:
    """期限结构数据"""

    symbol: str
    near_month: str  # 近月合约代码
    far_month: str  # 远月合约代码
    near_price: float  # 近月价格
    far_price: float  # 远月价格
    months_interval: int  # 月数间隔

    @property
    def spread(self) -> float:
        """价差 = 近月 - 远月"""
        return self.near_price - self.far_price

    @property
    def structure_type(self) -> str:
        """结构类型：Backwardation 或 Contango"""
        return "Backwardation" if self.spread > 0 else "Contango"

    @property
    def roll_yield(self) -> float:
        """
        展期收益率（年化）

        公式：Roll Yield (%) = [(F1 - F2) / F2] × (12 / n) × 100%
        """
        if self.far_price <= 0:
            return 0.0
        return (self.spread / self.far_price) * (12 / self.months_interval) * 100

    @property
    def slope(self) -> float:
        """
        期限结构斜率

        公式：Slope = (F2 - F1) / F1
        - Slope > 0: Contango（升水）
        - Slope < 0: Backwardation（贴水）
        """
        if self.near_price <= 0:
            return 0.0
        return (self.far_price - self.near_price) / self.near_price

    @property
    def normalized_rank(self) -> float:
        """
        标准化排序（用于跨品种比较）

        公式：R ≈ (F1 - F2) / F2
        """
        if self.far_price <= 0:
            return 0.0
        return self.spread / self.far_price


@dataclass
class InventoryData:
    """库存数据"""

    symbol: str
    current_level: float  # 当前库存水平
    historical_min: float  # 历史最低库存
    historical_max: float  # 历史最高库存
    change_rate: float = 0.0  # 库存变化率（Δ库存）
    acceleration: float = 0.0  # 库存加速度（d²库存）
    warehouse_receipts: float = 0.0  # 交易所仓单
    social_inventory: float = 0.0  # 社会库存

    @property
    def percentile(self) -> float:
        """
        库存分位数

        公式：分位数 = (当前库存 - 历史最低库存) / (历史最高库存 - 历史最低库存) × 100%
        """
        if self.historical_max <= self.historical_min:
            return 50.0
        return (self.current_level - self.historical_min) / (
            self.historical_max - self.historical_min
        ) * 100

    @property
    def inventory_zone(self) -> str:
        """库存区间"""
        p = self.percentile
        if p < 30:
            return "LOW"
        elif p > 70:
            return "HIGH"
        else:
            return "MEDIUM"


@dataclass
class CarrySignal:
    """Carry 信号"""

    symbol: str
    term_structure: TermStructure
    inventory: Optional[InventoryData]

    # 信号强度
    roll_yield_score: float = 0.0  # 展期收益率得分 (-1 ~ +1)
    inventory_score: float = 0.0  # 库存得分 (-1 ~ +1)
    trend_score: float = 0.0  # 趋势得分 (-1 ~ +1)
    composite_score: float = 0.0  # 综合得分 (-1 ~ +1)

    # 信号方向
    signal_direction: str = "NEUTRAL"  # LONG_CARRY / SHORT_CARRY / NEUTRAL
    signal_strength: str = "WEAK"  # STRONG / MEDIUM / WEAK

    # 风险提示
    warnings: list[str] = field(default_factory=list)
    interpretation: str = ""

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "structure_type": self.term_structure.structure_type,
            "roll_yield": round(self.term_structure.roll_yield, 2),
            "slope": round(self.term_structure.slope, 4),
            "inventory_zone": self.inventory.inventory_zone if self.inventory else "UNKNOWN",
            "roll_yield_score": round(self.roll_yield_score, 3),
            "inventory_score": round(self.inventory_score, 3),
            "trend_score": round(self.trend_score, 3),
            "composite_score": round(self.composite_score, 3),
            "signal_direction": self.signal_direction,
            "signal_strength": self.signal_strength,
            "warnings": self.warnings,
            "interpretation": self.interpretation,
        }


class CarryAnalyzer:
    """
    Carry 策略分析器

    基于 Carry 策略深度解析，提供：
    1. 期限结构分析
    2. 展期收益率计算
    3. 库存数据分析（三层加速度框架）
    4. Carry 信号生成
    """

    # 品种 Carry 适配性评级
    CARRY_COMPATIBILITY = {
        # 第一梯队：月差最有"定力"
        "M": {"tier": 1, "name": "豆粕", "reason": "榨季周期带来清晰季节性"},
        "CU": {"tier": 1, "name": "铜", "reason": "LME+SHFE双盘定价，库存透明"},
        "AL": {"tier": 1, "name": "铝", "reason": "Back结构稳定，展期收益波动率小"},
        "ZN": {"tier": 1, "name": "锌", "reason": "Back结构稳定，展期收益波动率小"},
        "C": {"tier": 1, "name": "玉米", "reason": "季节性规律教科书级"},
        # 第二梯队：结构有持续性，但波动更凶
        "I": {"tier": 2, "name": "铁矿石", "reason": "Back结构持续性强，但受宏观影响大"},
        "J": {"tier": 2, "name": "焦炭", "reason": "Back结构持久，但流动性可能收缩"},
        "JM": {"tier": 2, "name": "焦煤", "reason": "Back结构持久，政策风险大"},
        # 不适合"被动拿Carry"的品种
        "RB": {"tier": 3, "name": "螺纹钢", "reason": "月差结构易受短期事件驱动翻转"},
        "HC": {"tier": 3, "name": "热卷", "reason": "月差结构易受短期事件驱动翻转"},
        "SC": {"tier": 3, "name": "原油", "reason": "月差结构易受短期事件驱动翻转"},
        "TA": {"tier": 3, "name": "PTA", "reason": "月差结构易受短期事件驱动翻转"},
        "RU": {"tier": 3, "name": "橡胶", "reason": "月差结构易受短期事件驱动翻转"},
        "SP": {"tier": 3, "name": "纸浆", "reason": "月差结构易受短期事件驱动翻转"},
    }

    def __init__(self, curve_vol_threshold: float = 0.03):
        """
        初始化 Carry 分析器

        Args:
            curve_vol_threshold: 曲线波动率阈值，超过此值需更保守仓位
        """
        self.curve_vol_threshold = curve_vol_threshold

    def analyze(
        self,
        term_structure: TermStructure,
        inventory: Optional[InventoryData] = None,
        historical_spreads: Optional[list[float]] = None,
    ) -> CarrySignal:
        """
        执行 Carry 分析

        Args:
            term_structure: 期限结构数据
            inventory: 库存数据（可选）
            historical_spreads: 历史价差序列（可选，用于计算趋势）

        Returns:
            CarrySignal 信号
        """
        warnings = []

        # 1. 计算展期收益率得分
        roll_yield_score = self._calculate_roll_yield_score(term_structure)

        # 2. 计算库存得分
        inventory_score = 0.0
        if inventory:
            inventory_score = self._calculate_inventory_score(inventory, term_structure)
        else:
            warnings.append("库存数据缺失，库存得分默认为0")

        # 3. 计算趋势得分
        trend_score = 0.0
        if historical_spreads and len(historical_spreads) >= 5:
            trend_score = self._calculate_trend_score(historical_spreads)
        else:
            warnings.append("历史价差数据不足，趋势得分默认为0")

        # 4. 计算综合得分
        composite_score = (
            roll_yield_score * 0.5 + inventory_score * 0.3 + trend_score * 0.2
        )

        # 5. 生成信号
        signal_direction, signal_strength = self._generate_signal(
            composite_score, term_structure
        )

        # 6. 生成解读
        interpretation = self._generate_interpretation(
            term_structure, inventory, composite_score, signal_direction
        )

        # 7. 检查风险
        risk_warnings = self._check_risks(term_structure, inventory, historical_spreads)
        warnings.extend(risk_warnings)

        return CarrySignal(
            symbol=term_structure.symbol,
            term_structure=term_structure,
            inventory=inventory,
            roll_yield_score=roll_yield_score,
            inventory_score=inventory_score,
            trend_score=trend_score,
            composite_score=composite_score,
            signal_direction=signal_direction,
            signal_strength=signal_strength,
            warnings=warnings,
            interpretation=interpretation,
        )

    def _calculate_roll_yield_score(self, ts: TermStructure) -> float:
        """
        计算展期收益率得分

        正Carry（Backwardation）→ 正得分
        负Carry（Contango）→ 负得分
        """
        roll_yield = ts.roll_yield

        # 归一化到 [-1, 1]
        # 假设年化展期收益率在 -20% ~ +20% 之间
        score = max(-1.0, min(1.0, roll_yield / 20.0))

        return score

    def _calculate_inventory_score(
        self, inventory: InventoryData, ts: TermStructure
    ) -> float:
        """
        计算库存得分

        基于三层加速度框架：
        - 第0层（库存水位）：低水位是结构存在的基础
        - 第1层（库存一阶导数Δ）：去库/累库的速度
        - 第2层（库存二阶导数d²）：去库/累库的加速度
        """
        score = 0.0
        percentile = inventory.percentile

        # 第0层：库存水位
        if ts.structure_type == "Backwardation":
            # Back结构下，低库存是正面信号
            if percentile < 30:
                score += 0.4
            elif percentile < 50:
                score += 0.2
            elif percentile > 70:
                score -= 0.3  # 高库存下Back结构不可靠
        else:
            # Contango结构下，高库存是正面信号
            if percentile > 70:
                score += 0.4
            elif percentile > 50:
                score += 0.2
            elif percentile < 30:
                score -= 0.3  # 低库存下Contango不可靠

        # 第1层：库存变化率
        if inventory.change_rate < 0:
            # 去库
            if ts.structure_type == "Backwardation":
                score += 0.3  # 去库支持Back结构
            else:
                score -= 0.2  # 去库不利于Contango
        elif inventory.change_rate > 0:
            # 累库
            if ts.structure_type == "Contango":
                score += 0.3  # 累库支持Contango结构
            else:
                score -= 0.2  # 累库不利于Back结构

        # 第2层：库存加速度
        if inventory.acceleration < 0:
            # 去库加速
            if ts.structure_type == "Backwardation":
                score += 0.3
        elif inventory.acceleration > 0:
            # 去库减速（加速度为正，但变化率为负）
            if ts.structure_type == "Backwardation" and inventory.change_rate < 0:
                score -= 0.2  # Back结构见顶预警

        # 仓单与社会库存是否"分裂"
        if inventory.warehouse_receipts > 0 and inventory.social_inventory > 0:
            receipt_ratio = inventory.warehouse_receipts / inventory.social_inventory
            if receipt_ratio < 0.1 and ts.structure_type == "Backwardation":
                score -= 0.2  # 警惕"社库累、仓单低"的虚假Back

        return max(-1.0, min(1.0, score))

    def _calculate_trend_score(self, historical_spreads: list[float]) -> float:
        """
        计算趋势得分

        基于历史价差序列的变化趋势
        """
        if len(historical_spreads) < 5:
            return 0.0

        # 计算最近5个价差的线性趋势
        recent = historical_spreads[-5:]
        n = len(recent)
        x_mean = (n - 1) / 2
        y_mean = sum(recent) / n

        # 线性回归斜率
        numerator = sum((i - x_mean) * (recent[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0

        slope = numerator / denominator

        # 归一化到 [-1, 1]
        # 假设斜率在 -10 ~ +10 之间
        score = max(-1.0, min(1.0, slope / 10.0))

        return score

    def _generate_signal(
        self, composite_score: float, ts: TermStructure
    ) -> tuple[str, str]:
        """生成信号方向和强度"""
        # 信号方向
        if composite_score > 0.2:
            signal_direction = "LONG_CARRY"
        elif composite_score < -0.2:
            signal_direction = "SHORT_CARRY"
        else:
            signal_direction = "NEUTRAL"

        # 信号强度
        abs_score = abs(composite_score)
        if abs_score > 0.5:
            signal_strength = "STRONG"
        elif abs_score > 0.25:
            signal_strength = "MEDIUM"
        else:
            signal_strength = "WEAK"

        # 检查品种适配性
        compatibility = self.CARRY_COMPATIBILITY.get(ts.symbol, {})
        tier = compatibility.get("tier", 3)
        if tier == 3:
            # 不适合Carry的品种，降级信号强度
            if signal_strength == "STRONG":
                signal_strength = "MEDIUM"
            elif signal_strength == "MEDIUM":
                signal_strength = "WEAK"

        return signal_direction, signal_strength

    def _generate_interpretation(
        self,
        ts: TermStructure,
        inventory: Optional[InventoryData],
        composite_score: float,
        signal_direction: str,
    ) -> str:
        """生成解读"""
        parts = []

        # 结构类型
        parts.append(f"期限结构: {ts.structure_type}")

        # 展期收益率
        roll_yield = ts.roll_yield
        if roll_yield > 0:
            parts.append(f"正Carry({roll_yield:+.2f}%)，持有多头有利")
        else:
            parts.append(f"负Carry({roll_yield:+.2f}%)，持有空头有利")

        # 库存情况
        if inventory:
            parts.append(f"库存水位: {inventory.inventory_zone}({inventory.percentile:.0f}分位)")

        # 品种适配性
        compatibility = self.CARRY_COMPATIBILITY.get(ts.symbol, {})
        tier = compatibility.get("tier", 3)
        if tier == 1:
            parts.append("品种适合Carry策略")
        elif tier == 2:
            parts.append("品种适合Carry但波动较大")
        else:
            parts.append("品种不适合被动Carry")

        return "；".join(parts)

    def _check_risks(
        self,
        ts: TermStructure,
        inventory: Optional[InventoryData],
        historical_spreads: Optional[list[float]],
    ) -> list[str]:
        """检查风险"""
        warnings = []

        # 1. Curve Flip 风险
        if historical_spreads and len(historical_spreads) >= 3:
            recent = historical_spreads[-3:]
            if ts.spread > 0 and all(s < 0 for s in recent):
                warnings.append("⚠️ Curve Flip风险：当前Back但近期历史为Contango")
            elif ts.spread < 0 and all(s > 0 for s in recent):
                warnings.append("⚠️ Curve Flip风险：当前Contango但近期历史为Back")

        # 2. 流动性风险
        if inventory and inventory.warehouse_receipts < 100:
            warnings.append("⚠️ 流动性风险：仓单数量较低，注意近月流动性")

        # 3. 库存与结构背离
        if inventory:
            if ts.structure_type == "Backwardation" and inventory.percentile > 70:
                warnings.append("⚠️ 结构风险：Back结构但库存高，结构可能不可靠")
            elif ts.structure_type == "Contango" and inventory.percentile < 30:
                warnings.append("⚠️ 结构风险：Contango结构但库存低，结构可能不可靠")

        # 4. 曲线波动率
        if historical_spreads and len(historical_spreads) >= 10:
            import statistics

            try:
                vol = statistics.stdev(historical_spreads[-10:])
                if vol > self.curve_vol_threshold * ts.near_price:
                    warnings.append(f"⚠️ 曲线波动率较高({vol:.2f})，建议更保守仓位")
            except statistics.StatisticsError:
                pass

        return warnings

    def rank_products(
        self, signals: list[CarrySignal]
    ) -> list[CarrySignal]:
        """
        对品种进行 Carry 排序

        Args:
            signals: 多个品种的 Carry 信号列表

        Returns:
            按综合得分排序的信号列表
        """
        return sorted(signals, key=lambda s: s.composite_score, reverse=True)

    def get_top_carry_opportunities(
        self, signals: list[CarrySignal], top_n: int = 3
    ) -> dict[str, list[CarrySignal]]:
        """
        获取最佳 Carry 机会

        Args:
            signals: 多个品种的 Carry 信号列表
            top_n: 返回前N个

        Returns:
            {"long_carry": [...], "short_carry": [...]}
        """
        # 筛选正Carry信号
        long_carry = [s for s in signals if s.signal_direction == "LONG_CARRY"]
        long_carry.sort(key=lambda s: s.composite_score, reverse=True)

        # 筛选负Carry信号
        short_carry = [s for s in signals if s.signal_direction == "SHORT_CARRY"]
        short_carry.sort(key=lambda s: s.composite_score)

        return {
            "long_carry": long_carry[:top_n],
            "short_carry": short_carry[:top_n],
        }

    def format_analysis(self, signal: CarrySignal) -> str:
        """格式化分析结果"""
        ts = signal.term_structure
        lines = [
            f"=== Carry 分析 — {signal.symbol} ===",
            f"期限结构: {ts.structure_type} ({ts.near_month} vs {ts.far_month})",
            f"近月价格: {ts.near_price:.2f}  远月价格: {ts.far_price:.2f}",
            f"价差: {ts.spread:+.2f}  展期收益率: {ts.roll_yield:+.2f}%",
            f"期限结构斜率: {ts.slope:+.4f}",
            "",
        ]

        if signal.inventory:
            inv = signal.inventory
            lines.extend(
                [
                    f"库存水位: {inv.inventory_zone} ({inv.percentile:.0f}分位)",
                    f"库存变化率: {inv.change_rate:+.2f}  加速度: {inv.acceleration:+.2f}",
                    "",
                ]
            )

        lines.extend(
            [
                "信号得分:",
                f"  展期收益率得分: {signal.roll_yield_score:+.3f}",
                f"  库存得分: {signal.inventory_score:+.3f}",
                f"  趋势得分: {signal.trend_score:+.3f}",
                f"  综合得分: {signal.composite_score:+.3f}",
                "",
                f"信号方向: {signal.signal_direction}",
                f"信号强度: {signal.signal_strength}",
            ]
        )

        if signal.warnings:
            lines.append("")
            lines.append("风险提示:")
            for w in signal.warnings:
                lines.append(f"  {w}")

        if signal.interpretation:
            lines.append("")
            lines.append(f"解读: {signal.interpretation}")

        return "\n".join(lines)


def analyze_carry(
    symbol: str,
    near_price: float,
    far_price: float,
    near_month: str = "",
    far_month: str = "",
    months_interval: int = 1,
    inventory_level: Optional[float] = None,
    historical_min: Optional[float] = None,
    historical_max: Optional[float] = None,
    change_rate: float = 0.0,
    acceleration: float = 0.0,
) -> CarrySignal:
    """
    便捷函数：分析 Carry 信号

    Args:
        symbol: 品种代码
        near_price: 近月价格
        far_price: 远月价格
        near_month: 近月合约代码
        far_month: 远月合约代码
        months_interval: 月数间隔
        inventory_level: 当前库存水平
        historical_min: 历史最低库存
        historical_max: 历史最高库存
        change_rate: 库存变化率
        acceleration: 库存加速度

    Returns:
        CarrySignal
    """
    ts = TermStructure(
        symbol=symbol,
        near_month=near_month,
        far_month=far_month,
        near_price=near_price,
        far_price=far_price,
        months_interval=months_interval,
    )

    inventory = None
    if inventory_level is not None and historical_min is not None and historical_max is not None:
        inventory = InventoryData(
            symbol=symbol,
            current_level=inventory_level,
            historical_min=historical_min,
            historical_max=historical_max,
            change_rate=change_rate,
            acceleration=acceleration,
        )

    analyzer = CarryAnalyzer()
    return analyzer.analyze(ts, inventory)
