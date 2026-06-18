"""
异常值分层加权机制

基于 V3.0 方案第一章的异常值处理规则：
- 制度性异常：交割日、涨跌停、换月前后 → 权重降低50%
- 短期脉冲异常：单日消息冲击导致的极端波动 → 权重降低30%
- 长期趋势断裂异常：政策突变、疫情、战争 → 重点分析

核心功能：
1. 异常类型识别
2. 异常值标记
3. 权重调整
4. 异常报告生成
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class AnomalyType(Enum):
    """异常类型"""
    INSTITUTIONAL = "institutional"  # 制度性异常（交割日、涨跌停、换月）
    SHORT_TERM_PULSE = "short_term_pulse"  # 短期脉冲异常
    LONG_TERM_BREAK = "long_term_break"  # 长期趋势断裂
    NORMAL = "normal"  # 正常数据


@dataclass
class AnomalyResult:
    """异常检测结果"""
    anomaly_type: AnomalyType
    weight_factor: float  # 权重调整因子 (0-1)
    is_anomaly: bool
    reason: str = ""
    confidence: float = 0.0


class AnomalyWeighter:
    """
    异常值分层加权机制
    
    基于 V3.0 方案的异常值处理规则
    """
    
    # 权重调整因子
    WEIGHT_FACTORS = {
        AnomalyType.INSTITUTIONAL: 0.5,  # 权重降低50%
        AnomalyType.SHORT_TERM_PULSE: 0.7,  # 权重降低30%
        AnomalyType.LONG_TERM_BREAK: 1.0,  # 不降权，重点分析
        AnomalyType.NORMAL: 1.0,  # 正常权重
    }
    
    def __init__(self, 
                 price_change_threshold: float = 0.05,
                 volume_spike_threshold: float = 3.0):
        """
        初始化异常值检测器
        
        Args:
            price_change_threshold: 价格变化阈值（5%视为异常）
            volume_spike_threshold: 成交量突增阈值（3倍视为异常）
        """
        self.price_change_threshold = price_change_threshold
        self.volume_spike_threshold = volume_spike_threshold
    
    def detect(self, df: pd.DataFrame, idx: int) -> AnomalyResult:
        """
        检测单个数据点的异常类型
        
        Args:
            df: 包含OHLCV数据的DataFrame
            idx: 数据点索引
            
        Returns:
            AnomalyResult: 异常检测结果
        """
        if idx < 0 or idx >= len(df):
            return AnomalyResult(
                anomaly_type=AnomalyType.NORMAL,
                weight_factor=1.0,
                is_anomaly=False,
                reason="索引越界"
            )
        
        row = df.iloc[idx]
        
        # 检测制度性异常
        institutional = self._check_institutional_anomaly(df, idx)
        if institutional.is_anomaly:
            return institutional
        
        # 检测短期脉冲异常
        pulse = self._check_pulse_anomaly(df, idx)
        if pulse.is_anomaly:
            return pulse
        
        # 检测长期趋势断裂
        break_result = self._check_trend_break(df, idx)
        if break_result.is_anomaly:
            return break_result
        
        # 正常数据
        return AnomalyResult(
            anomaly_type=AnomalyType.NORMAL,
            weight_factor=1.0,
            is_anomaly=False,
            reason="正常数据"
        )
    
    def _check_institutional_anomaly(self, df: pd.DataFrame, idx: int) -> AnomalyResult:
        """检测制度性异常（涨跌停）"""
        if idx < 1:
            return AnomalyResult(
                anomaly_type=AnomalyType.NORMAL,
                weight_factor=1.0,
                is_anomaly=False
            )
        
        row = df.iloc[idx]
        prev_close = df.iloc[idx - 1]["close"]
        
        if prev_close == 0:
            return AnomalyResult(
                anomaly_type=AnomalyType.NORMAL,
                weight_factor=1.0,
                is_anomaly=False
            )
        
        # 计算涨跌幅
        change_pct = abs(row["close"] - prev_close) / prev_close
        
        # 涨跌停检测（10%阈值，适配A股）
        if change_pct >= 0.095:
            return AnomalyResult(
                anomaly_type=AnomalyType.INSTITUTIONAL,
                weight_factor=self.WEIGHT_FACTORS[AnomalyType.INSTITUTIONAL],
                is_anomaly=True,
                reason=f"涨跌停异常: {change_pct:.2%}",
                confidence=0.9
            )
        
        return AnomalyResult(
            anomaly_type=AnomalyType.NORMAL,
            weight_factor=1.0,
            is_anomaly=False
        )
    
    def _check_pulse_anomaly(self, df: pd.DataFrame, idx: int) -> AnomalyResult:
        """检测短期脉冲异常"""
        if idx < 5:
            return AnomalyResult(
                anomaly_type=AnomalyType.NORMAL,
                weight_factor=1.0,
                is_anomaly=False
            )
        
        row = df.iloc[idx]
        
        # 计算近期平均价格变化
        recent_changes = []
        for i in range(max(0, idx-5), idx):
            if i > 0:
                prev = df.iloc[i-1]["close"]
                curr = df.iloc[i]["close"]
                if prev > 0:
                    recent_changes.append(abs(curr - prev) / prev)
        
        if not recent_changes:
            return AnomalyResult(
                anomaly_type=AnomalyType.NORMAL,
                weight_factor=1.0,
                is_anomaly=False
            )
        
        avg_change = np.mean(recent_changes)
        
        # 当前价格变化
        prev_close = df.iloc[idx - 1]["close"]
        if prev_close > 0:
            current_change = abs(row["close"] - prev_close) / prev_close
            
            # 短期脉冲检测（超过平均变化的3倍）
            if current_change > avg_change * 3 and current_change > self.price_change_threshold:
                return AnomalyResult(
                    anomaly_type=AnomalyType.SHORT_TERM_PULSE,
                    weight_factor=self.WEIGHT_FACTORS[AnomalyType.SHORT_TERM_PULSE],
                    is_anomaly=True,
                    reason=f"短期脉冲异常: {current_change:.2%} (平均: {avg_change:.2%})",
                    confidence=0.7
                )
        
        return AnomalyResult(
            anomaly_type=AnomalyType.NORMAL,
            weight_factor=1.0,
            is_anomaly=False
        )
    
    def _check_trend_break(self, df: pd.DataFrame, idx: int) -> AnomalyResult:
        """检测长期趋势断裂"""
        if idx < 20:
            return AnomalyResult(
                anomaly_type=AnomalyType.NORMAL,
                weight_factor=1.0,
                is_anomaly=False
            )
        
        # 计算20日均线
        ma20 = df.iloc[max(0, idx-20):idx]["close"].mean()
        current_price = df.iloc[idx]["close"]
        
        if ma20 == 0:
            return AnomalyResult(
                anomaly_type=AnomalyType.NORMAL,
                weight_factor=1.0,
                is_anomaly=False
            )
        
        # 计算偏离度
        deviation = abs(current_price - ma20) / ma20
        
        # 长期趋势断裂检测（偏离超过20%）
        if deviation > 0.2:
            return AnomalyResult(
                anomaly_type=AnomalyType.LONG_TERM_BREAK,
                weight_factor=self.WEIGHT_FACTORS[AnomalyType.LONG_TERM_BREAK],
                is_anomaly=True,
                reason=f"长期趋势断裂: 偏离MA20 {deviation:.2%}",
                confidence=0.8
            )
        
        return AnomalyResult(
            anomaly_type=AnomalyType.NORMAL,
            weight_factor=1.0,
            is_anomaly=False
        )
    
    def batch_detect(self, df: pd.DataFrame) -> List[AnomalyResult]:
        """
        批量检测异常
        
        Args:
            df: 包含OHLCV数据的DataFrame
            
        Returns:
            List[AnomalyResult]: 异常检测结果列表
        """
        results = []
        for idx in range(len(df)):
            results.append(self.detect(df, idx))
        return results
    
    def get_anomaly_summary(self, results: List[AnomalyResult]) -> dict:
        """获取异常统计摘要"""
        summary = {
            "total": len(results),
            "anomaly_count": sum(1 for r in results if r.is_anomaly),
            "by_type": {},
        }
        
        for anomaly_type in AnomalyType:
            count = sum(1 for r in results if r.anomaly_type == anomaly_type)
            summary["by_type"][anomaly_type.value] = count
        
        return summary


def create_anomaly_report(results: List[AnomalyResult], df: pd.DataFrame) -> str:
    """创建异常检测报告"""
    weighter = AnomalyWeighter()
    summary = weighter.get_anomaly_summary(results)
    
    lines = [
        "=== 异常值检测报告 ===",
        "",
        f"总数据点: {summary['total']}",
        f"异常数据点: {summary['anomaly_count']}",
        "",
        "异常类型分布:",
    ]
    
    for anomaly_type, count in summary["by_type"].items():
        if count > 0:
            lines.append(f"  - {anomaly_type}: {count}")
    
    # 列出异常数据点
    anomaly_indices = [i for i, r in enumerate(results) if r.is_anomaly]
    if anomaly_indices:
        lines.append("")
        lines.append("异常数据点详情:")
        for idx in anomaly_indices[:10]:  # 最多显示10个
            result = results[idx]
            if idx < len(df):
                date = df.index[idx] if hasattr(df.index[idx], 'strftime') else str(df.index[idx])
                lines.append(f"  - {date}: {result.reason}")
    
    return "\n".join(lines)
