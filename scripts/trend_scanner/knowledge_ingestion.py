"""
知识摄取流水线

参考 SkillWiki 的 Knowledge Ingestion Pipeline，将异构知识源转化为因子候选。

支持的知识源类型：
- paper      — 论文（arXiv、研究报告）
- trajectory — 交易轨迹（回测日志、执行记录）
- document   — 文档（策略手册、技术指标说明）
- script     — 脚本（量化因子代码片段）
- past_skill — 历史因子（已有因子库）

流水线流程：
1. 解析原始知识源
2. 提取可复用的因子模式
3. 生成因子候选
4. 注册到生命周期系统
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from trend_scanner.factor_lifecycle import FactorAsset, FactorLifecycleManager, LifecycleState


class SourceType(str, Enum):
    """知识源类型"""

    PAPER = "paper"
    TRAJECTORY = "trajectory"
    DOCUMENT = "document"
    SCRIPT = "script"
    PAST_SKILL = "past_skill"


@dataclass
class KnowledgeSource:
    """知识源"""

    id: str
    source_type: SourceType
    title: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class ExtractedPattern:
    """提取的因子模式"""

    pattern_id: str
    source_id: str
    pattern_type: str  # momentum / volume / volatility / trend / composite
    name: str
    description: str
    logic: str
    code: str
    confidence: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class KnowledgeIngestionPipeline:
    """
    知识摄取流水线

    将异构知识源转化为因子候选，注册到生命周期系统。
    """

    def __init__(self, lifecycle_manager: FactorLifecycleManager = None):
        self.lifecycle_manager = lifecycle_manager or FactorLifecycleManager()
        self._pattern_counter = 0

    def _next_pattern_id(self) -> str:
        """生成下一个模式ID"""
        self._pattern_counter += 1
        return f"pattern_{self._pattern_counter:04d}"

    def ingest(self, source: KnowledgeSource) -> list[FactorAsset]:
        """
        摄入知识源，生成因子候选

        Args:
            source: 知识源

        Returns:
            生成的因子候选列表
        """
        # 1. 解析知识源
        patterns = self._extract_patterns(source)

        # 2. 生成因子候选
        factors = []
        for pattern in patterns:
            factor = self._pattern_to_factor(source, pattern)
            if factor:
                factors.append(factor)
                self.lifecycle_manager.register_factor(factor)

        return factors

    def _extract_patterns(self, source: KnowledgeSource) -> list[ExtractedPattern]:
        """
        从知识源中提取因子模式

        Args:
            source: 知识源

        Returns:
            提取的模式列表
        """
        if source.source_type == SourceType.PAPER:
            return self._extract_from_paper(source)
        elif source.source_type == SourceType.TRAJECTORY:
            return self._extract_from_trajectory(source)
        elif source.source_type == SourceType.DOCUMENT:
            return self._extract_from_document(source)
        elif source.source_type == SourceType.SCRIPT:
            return self._extract_from_script(source)
        elif source.source_type == SourceType.PAST_SKILL:
            return self._extract_from_past_skill(source)
        return []

    def _extract_from_paper(self, source: KnowledgeSource) -> list[ExtractedPattern]:
        """
        从论文中提取因子模式

        论文通常包含：
        - 指标定义和计算方法
        - 信号生成逻辑
        - 参数设置建议
        """
        patterns = []
        content = source.content.lower()

        # 基于关键词检测因子类型
        momentum_keywords = ["momentum", "动量", "趋势", "trend", "突破", "breakout"]
        volume_keywords = ["volume", "成交量", "量比", "放量", "缩量"]
        volatility_keywords = ["volatility", "波动率", "atr", "标准差", "std"]
        mean_reversion_keywords = ["mean reversion", "均值回归", "超买", "超卖", "rsi", "cci"]

        detected_types = []

        for kw in momentum_keywords:
            if kw in content:
                detected_types.append("momentum")
                break

        for kw in volume_keywords:
            if kw in content:
                detected_types.append("volume")
                break

        for kw in volatility_keywords:
            if kw in content:
                detected_types.append("volatility")
                break

        for kw in mean_reversion_keywords:
            if kw in content:
                detected_types.append("mean_reversion")
                break

        # 为每个检测到的类型生成模式
        for i, ptype in enumerate(detected_types):
            pattern = ExtractedPattern(
                pattern_id=self._next_pattern_id(),
                source_id=source.id,
                pattern_type=ptype,
                name=f"{source.title}_{ptype}_{i+1}",
                description=f"从论文《{source.title}》提取的{ptype}因子模式",
                logic=f"基于论文描述的{ptype}逻辑",
                code=f"# TODO: 从论文内容生成具体实现\ndef factor(df):\n    pass",
                confidence=0.5,
                metadata={"paper_title": source.title, "extracted_type": ptype},
            )
            patterns.append(pattern)

        # 如果没有检测到特定类型，创建一个通用模式
        if not detected_types:
            pattern = ExtractedPattern(
                pattern_id=self._next_pattern_id(),
                source_id=source.id,
                pattern_type="unknown",
                name=f"{source.title}_generic",
                description=f"从论文《{source.title}》提取的通用因子模式",
                logic="需要人工分析论文内容确定具体逻辑",
                code="# TODO: 需要人工分析论文内容",
                confidence=0.3,
                metadata={"paper_title": source.title},
            )
            patterns.append(pattern)

        return patterns

    def _extract_from_trajectory(self, source: KnowledgeSource) -> list[ExtractedPattern]:
        """
        从交易轨迹中提取因子模式

        轨迹通常包含：
        - 入场/出场条件
        - 持仓时间
        - 盈亏记录
        """
        patterns = []
        content = source.content

        # 尝试从轨迹中提取入场条件
        entry_conditions = self._parse_entry_conditions(content)

        for i, condition in enumerate(entry_conditions):
            pattern = ExtractedPattern(
                pattern_id=self._next_pattern_id(),
                source_id=source.id,
                pattern_type="trajectory_based",
                name=f"trajectory_{source.id}_{i+1}",
                description=f"从交易轨迹提取的入场条件: {condition.get('description', '')}",
                logic=condition.get("logic", ""),
                code=condition.get("code", "# TODO: 从轨迹逻辑生成代码"),
                confidence=condition.get("confidence", 0.4),
                metadata={"trajectory_id": source.id},
            )
            patterns.append(pattern)

        return patterns

    def _extract_from_document(self, source: KnowledgeSource) -> list[ExtractedPattern]:
        """
        从文档中提取因子模式

        文档通常包含：
        - 指标说明
        - 使用方法
        - 参数设置
        """
        patterns = []
        content = source.content

        # 检测文档中提到的指标
        indicators = self._detect_indicators(content)

        for i, indicator in enumerate(indicators):
            pattern = ExtractedPattern(
                pattern_id=self._next_pattern_id(),
                source_id=source.id,
                pattern_type=indicator.get("type", "indicator"),
                name=f"doc_{indicator['name']}",
                description=f"从文档提取的{indicator['name']}指标",
                logic=indicator.get("logic", ""),
                code=indicator.get("code", f"# {indicator['name']} 实现"),
                confidence=0.6,
                metadata={"document_title": source.title},
            )
            patterns.append(pattern)

        return patterns

    def _extract_from_script(self, source: KnowledgeSource) -> list[ExtractedPattern]:
        """
        从脚本中提取因子模式

        脚本通常包含：
        - 完整的因子实现
        - 计算逻辑
        """
        patterns = []

        # 尝试解析脚本中的因子函数
        if "def factor" in source.content or "def calculate" in source.content:
            pattern = ExtractedPattern(
                pattern_id=self._next_pattern_id(),
                source_id=source.id,
                pattern_type="script_based",
                name=f"script_{source.id}",
                description=f"从脚本提取的因子实现",
                logic="脚本直接实现",
                code=source.content,
                confidence=0.7,
                metadata={"script_path": source.metadata.get("path", "")},
            )
            patterns.append(pattern)

        return patterns

    def _extract_from_past_skill(self, source: KnowledgeSource) -> list[ExtractedPattern]:
        """
        从历史因子中提取模式

        用于因子迁移或重组
        """
        patterns = []

        pattern = ExtractedPattern(
            pattern_id=self._next_pattern_id(),
            source_id=source.id,
            pattern_type="migration",
            name=f"migrated_{source.id}",
            description=f"从历史因子迁移: {source.title}",
            logic=source.metadata.get("logic", ""),
            code=source.content,
            confidence=0.8,
            metadata={"original_id": source.metadata.get("original_id", "")},
        )
        patterns.append(pattern)

        return patterns

    def _parse_entry_conditions(self, content: str) -> list[dict[str, Any]]:
        """解析入场条件"""
        conditions = []
        content_lower = content.lower()

        # 简单的关键词匹配
        if any(kw in content_lower for kw in ["ema", "均线", "ma"]):
            conditions.append(
                {
                    "description": "均线交叉信号",
                    "logic": "EMA快线上穿EMA慢线",
                    "code": "def factor(df):\n    ema_fast = df['close'].ewm(span=20).mean()\n    ema_slow = df['close'].ewm(span=60).mean()\n    return (ema_fast - ema_slow) / ema_slow",
                    "confidence": 0.5,
                }
            )

        if any(kw in content_lower for kw in ["rsi", "超买", "超卖"]):
            conditions.append(
                {
                    "description": "RSI超买超卖信号",
                    "logic": "RSI<30超卖做多，RSI>70超买做空",
                    "code": "def factor(df):\n    delta = df['close'].diff()\n    gain = delta.where(delta>0,0).rolling(14).mean()\n    loss = (-delta.where(delta<0,0)).rolling(14).mean()\n    rs = gain/loss\n    rsi = 100 - 100/(1+rs)\n    return (50 - rsi) / 50",
                    "confidence": 0.5,
                }
            )

        if any(kw in content_lower for kw in ["breakout", "突破", "新高"]):
            conditions.append(
                {
                    "description": "突破信号",
                    "logic": "价格突破N日高点",
                    "code": "def factor(df):\n    high_n = df['high'].rolling(20).max()\n    return (df['close'] - high_n) / high_n",
                    "confidence": 0.4,
                }
            )

        return conditions

    def _detect_indicators(self, content: str) -> list[dict[str, Any]]:
        """检测文档中提到的指标"""
        indicators = []
        content_lower = content.lower()

        indicator_map = {
            "rsi": {"name": "RSI", "type": "momentum", "logic": "相对强弱指标"},
            "macd": {"name": "MACD", "type": "momentum", "logic": "移动平均收敛发散"},
            "atr": {"name": "ATR", "type": "volatility", "logic": "平均真实波幅"},
            "adx": {"name": "ADX", "type": "trend", "logic": "平均趋向指标"},
            "bollinger": {"name": "Bollinger", "type": "volatility", "logic": "布林带"},
            "stochastic": {"name": "Stochastic", "type": "momentum", "logic": "随机指标"},
            "cci": {"name": "CCI", "type": "momentum", "logic": "商品通道指标"},
            "williams": {"name": "Williams %R", "type": "momentum", "logic": "威廉指标"},
        }

        for key, info in indicator_map.items():
            if key in content_lower:
                indicators.append(info)

        return indicators

    def _pattern_to_factor(
        self, source: KnowledgeSource, pattern: ExtractedPattern
    ) -> Optional[FactorAsset]:
        """
        将模式转换为因子资产

        Args:
            source: 知识源
            pattern: 提取的模式

        Returns:
            FactorAsset 或 None
        """
        factor_id = f"factor_{source.source_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{pattern.pattern_id}"

        factor = FactorAsset(
            id=factor_id,
            name=pattern.name,
            code=pattern.code,
            description=pattern.description,
            logic=pattern.logic,
            category=pattern.pattern_type,
            lifecycle_state=LifecycleState.RAW,
            source_type=source.source_type.value,
            source_ref=source.id,
            evaluation={},
        )

        # 设置来源元数据
        factor.metadata = {
            "pattern_id": pattern.pattern_id,
            "confidence": pattern.confidence,
            "source_title": source.title,
        }

        return factor

    def batch_ingest(self, sources: list[KnowledgeSource]) -> dict[str, Any]:
        """
        批量摄入知识源

        Args:
            sources: 知识源列表

        Returns:
            摄入结果统计
        """
        stats = {
            "total_sources": len(sources),
            "total_factors": 0,
            "by_source_type": {},
        }

        for source in sources:
            factors = self.ingest(source)
            stats["total_factors"] += len(factors)

            st = source.source_type.value
            stats["by_source_type"][st] = stats["by_source_type"].get(st, 0) + len(factors)

        return stats

    def get_statistics(self) -> dict[str, Any]:
        """获取摄取统计"""
        lifecycle_stats = self.lifecycle_manager.get_statistics()
        return {
            "pattern_counter": self._pattern_counter,
            "lifecycle_stats": lifecycle_stats,
        }
