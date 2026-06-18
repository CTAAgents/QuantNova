"""
多源数据冲突裁决引擎

基于 V3.0 方案第一章的数据冲突裁决规则：
- 最新数据优先
- 高可信度数据源优先
- 统计口径匹配数据优先
- 冲突数据自动标记分歧
- 强制AI在报告中披露数据矛盾

核心功能：
1. 多源数据对齐
2. 冲突检测
3. 优先级裁决
4. 分歧标记
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DataCredibility(Enum):
    """数据可信度等级"""
    LEVEL_1 = 1  # 交易所、统计局官方数据
    LEVEL_2 = 2  # 头部券商研报、产业调研
    LEVEL_3 = 3  # Wind、Bloomberg终端数据
    LEVEL_4 = 4  # 自媒体、散户舆情


@dataclass
class DataPoint:
    """数据点"""
    value: float
    source: str
    credibility: DataCredibility
    timestamp: str
    data_type: str  # price/volume/inventory/supply_demand/etc
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConflictResult:
    """冲突裁决结果"""
    has_conflict: bool
    resolved_value: float
    resolution_method: str
    conflicting_sources: List[str]
    confidence: float
    notes: str = ""


class DataConflictResolver:
    """
    多源数据冲突裁决引擎
    
    基于 V3.0 方案的冲突裁决规则
    """
    
    # 可信度权重
    CREDIBILITY_WEIGHTS = {
        DataCredibility.LEVEL_1: 1.0,
        DataCredibility.LEVEL_2: 0.8,
        DataCredibility.LEVEL_3: 0.6,
        DataCredibility.LEVEL_4: 0.3,
    }
    
    # 冲突阈值（百分比）
    CONFLICT_THRESHOLD = 0.05  # 5%偏差视为冲突
    
    def __init__(self, conflict_threshold: float = 0.05):
        """
        初始化冲突裁决引擎
        
        Args:
            conflict_threshold: 冲突判定阈值（百分比）
        """
        self.conflict_threshold = conflict_threshold
    
    def resolve(self, data_points: List[DataPoint]) -> ConflictResult:
        """
        裁决多源数据冲突
        
        Args:
            data_points: 多个数据点
            
        Returns:
            ConflictResult: 裁决结果
        """
        if not data_points:
            return ConflictResult(
                has_conflict=False,
                resolved_value=0.0,
                resolution_method="no_data",
                conflicting_sources=[],
                confidence=0.0,
                notes="无数据输入"
            )
        
        if len(data_points) == 1:
            return ConflictResult(
                has_conflict=False,
                resolved_value=data_points[0].value,
                resolution_method="single_source",
                conflicting_sources=[],
                confidence=self.CREDIBILITY_WEIGHTS[data_points[0].credibility],
                notes="单数据源，无需裁决"
            )
        
        # 检测冲突
        conflicts = self._detect_conflicts(data_points)
        
        if not conflicts:
            # 无冲突，使用加权平均
            resolved = self._weighted_average(data_points)
            return ConflictResult(
                has_conflict=False,
                resolved_value=resolved,
                resolution_method="weighted_average",
                conflicting_sources=[],
                confidence=self._calculate_confidence(data_points),
                notes="多源数据一致"
            )
        
        # 有冲突，执行裁决
        resolved = self._resolve_conflict(data_points, conflicts)
        
        return ConflictResult(
            has_conflict=True,
            resolved_value=resolved,
            resolution_method="credibility_weighted",
            conflicting_sources=[dp.source for dp in data_points],
            confidence=self._calculate_confidence(data_points),
            notes=f"检测到{len(conflicts)}处冲突，已按可信度裁决"
        )
    
    def _detect_conflicts(self, data_points: List[DataPoint]) -> List[Dict]:
        """检测数据冲突"""
        conflicts = []
        
        values = [dp.value for dp in data_points]
        mean_value = sum(values) / len(values)
        
        for i, dp in enumerate(data_points):
            deviation = abs(dp.value - mean_value) / mean_value if mean_value != 0 else 0
            if deviation > self.conflict_threshold:
                conflicts.append({
                    "index": i,
                    "source": dp.source,
                    "value": dp.value,
                    "deviation": deviation,
                })
        
        return conflicts
    
    def _weighted_average(self, data_points: List[DataPoint]) -> float:
        """计算可信度加权平均"""
        total_weight = 0
        weighted_sum = 0
        
        for dp in data_points:
            weight = self.CREDIBILITY_WEIGHTS[dp.credibility]
            weighted_sum += dp.value * weight
            total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0
    
    def _resolve_conflict(self, data_points: List[DataPoint], conflicts: List[Dict]) -> float:
        """裁决冲突"""
        # 按可信度排序，取最高可信度的数据
        sorted_points = sorted(data_points, key=lambda dp: dp.credibility.value)
        return sorted_points[0].value
    
    def _calculate_confidence(self, data_points: List[DataPoint]) -> float:
        """计算裁决置信度"""
        if not data_points:
            return 0.0
        
        # 基于最高可信度和数据源数量
        max_credibility = max(self.CREDIBILITY_WEIGHTS[dp.credibility] for dp in data_points)
        source_factor = min(len(data_points) / 3, 1.0)  # 3个以上数据源满分
        
        return max_credibility * source_factor
    
    def create_conflict_report(self, result: ConflictResult, data_points: List[DataPoint]) -> str:
        """创建冲突报告"""
        lines = [
            "=== 数据冲突裁决报告 ===",
            "",
            f"冲突状态：{'存在冲突' if result.has_conflict else '无冲突'}",
            f"裁决方法：{result.resolution_method}",
            f"裁决结果：{result.resolved_value:.4f}",
            f"置信度：{result.confidence:.2%}",
            "",
            "数据源详情：",
        ]
        
        for dp in data_points:
            lines.append(f"  - {dp.source}: {dp.value:.4f} (可信度: {dp.credibility.name})")
        
        if result.has_conflict:
            lines.append("")
            lines.append(f"冲突说明：{result.notes}")
        
        return "\n".join(lines)


def create_credibility_tag(credibility: DataCredibility) -> str:
    """创建可信度标签"""
    tags = {
        DataCredibility.LEVEL_1: "[官方数据]",
        DataCredibility.LEVEL_2: "[研报数据]",
        DataCredibility.LEVEL_3: "[终端数据]",
        DataCredibility.LEVEL_4: "[舆情数据]",
    }
    return tags.get(credibility, "[未知]")
