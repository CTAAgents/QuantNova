"""
幻觉检测模块

基于 V3.0 方案第二章的幻觉硬约束：
1. 严禁编造未提供的数据
2. 关键数据缺失直接说明
3. 严格分块输出事实与观点
4. 禁止100%确定性结论
5. 引用低可信度数据必须标注风险

核心功能：
1. 数据一致性检查
2. 确定性结论检测
3. 缺失数据识别
4. 低可信度数据标注检查
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

logger = logging.getLogger(__name__)


class HallucinationType(Enum):
    """幻觉类型"""
    DATA_FABRICATION = "data_fabrication"  # 编造数据
    CERTAINTY_CLAIM = "certainty_claim"  # 确定性结论
    MISSING_DATA_ACK = "missing_data_ack"  # 缺失数据未说明
    LOW_CREDIBILITY = "low_credibility"  # 低可信度数据未标注
    LOGIC_CONTRADICTION = "logic_contradiction"  # 逻辑矛盾
    NONE = "none"  # 无幻觉


@dataclass
class HallucinationCheckResult:
    """幻觉检测结果"""
    hallucination_type: HallucinationType
    is_hallucination: bool
    severity: str  # high/medium/low
    description: str
    suggestion: str = ""
    confidence: float = 0.0


class HallucinationDetector:
    """
    幻觉检测器
    
    基于 V3.0 方案的幻觉硬约束
    """
    
    # 确定性结论关键词
    CERTAINTY_PATTERNS = [
        r"100%",
        r"绝对",
        r"必然",
        r"肯定",
        r"一定",
        r"毫无疑问",
        r"必然上涨",
        r"必然下跌",
        r"必涨",
        r"必跌",
        r"确定性",
        r"必将",
        r"势必",
    ]
    
    # 缺失数据标识
    MISSING_DATA_PATTERNS = [
        r"暂无数据",
        r"数据缺失",
        r"未获取到",
        r"数据不可用",
        r"无法获取",
    ]
    
    def __init__(self):
        """初始化幻觉检测器"""
        pass
    
    def check(self, text: str, provided_data: Optional[dict] = None) -> List[HallucinationCheckResult]:
        """
        检测文本中的幻觉
        
        Args:
            text: 待检测文本
            provided_data: 提供给模型的数据（可选）
            
        Returns:
            List[HallucinationCheckResult]: 检测结果列表
        """
        results = []
        
        # 1. 检测确定性结论
        certainty_results = self._check_certainty_claims(text)
        results.extend(certainty_results)
        
        # 2. 检测缺失数据说明
        missing_results = self._check_missing_data_ack(text)
        results.extend(missing_results)
        
        # 3. 检测低可信度数据标注
        credibility_results = self._check_credibility_labels(text)
        results.extend(credibility_results)
        
        # 4. 检测数据一致性（如果有提供数据）
        if provided_data:
            consistency_results = self._check_data_consistency(text, provided_data)
            results.extend(consistency_results)
        
        return results
    
    def _check_certainty_claims(self, text: str) -> List[HallucinationCheckResult]:
        """检测确定性结论"""
        results = []
        
        for pattern in self.CERTAINTY_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # 获取匹配的上下文
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end]
                
                results.append(HallucinationCheckResult(
                    hallucination_type=HallucinationType.CERTAINTY_CLAIM,
                    is_hallucination=True,
                    severity="high",
                    description=f"检测到确定性结论: '{match.group()}'",
                    suggestion="建议改为概率表述，如'概率较大'或'有较高可能性'",
                    confidence=0.9
                ))
        
        return results
    
    def _check_missing_data_ack(self, text: str) -> List[HallucinationCheckResult]:
        """检测缺失数据说明"""
        results = []
        
        # 检查是否包含缺失数据标识
        has_missing_ack = any(re.search(p, text, re.IGNORECASE) for p in self.MISSING_DATA_PATTERNS)
        
        if not has_missing_ack:
            # 没有缺失数据说明，可能存在问题
            # 这里简化处理，实际应该检查数据完整性
            pass
        
        return results
    
    def _check_credibility_labels(self, text: str) -> List[HallucinationCheckResult]:
        """检测低可信度数据标注"""
        results = []
        
        # 检测是否引用了4级数据源
        low_credibility_sources = ["自媒体", "散户", "股吧", "微博", "抖音"]
        
        for source in low_credibility_sources:
            if source in text:
                # 检查是否标注了风险
                risk_indicators = ["风险", "谨慎", "低可信度", "仅供参考", "需验证"]
                has_risk_label = any(indicator in text for indicator in risk_indicators)
                
                if not has_risk_label:
                    results.append(HallucinationCheckResult(
                        hallucination_type=HallucinationType.LOW_CREDIBILITY,
                        is_hallucination=True,
                        severity="medium",
                        description=f"引用低可信度数据源 '{source}' 但未标注风险",
                        suggestion="建议添加风险提示，如'该数据来源为自媒体，可信度较低'",
                        confidence=0.8
                    ))
        
        return results
    
    def _check_data_consistency(self, text: str, provided_data: dict) -> List[HallucinationCheckResult]:
        """检测数据一致性"""
        results = []
        
        # 检查是否编造了未提供的数据
        # 这里简化实现，实际应该更复杂的文本分析
        
        return results
    
    def get_hallucination_rate(self, results_list: List[List[HallucinationCheckResult]]) -> float:
        """计算幻觉率"""
        if not results_list:
            return 0.0
        
        total_checks = len(results_list)
        hallucination_count = sum(1 for results in results_list if any(r.is_hallucination for r in results))
        
        return hallucination_count / total_checks if total_checks > 0 else 0.0
    
    def create_hallucination_report(self, results: List[HallucinationCheckResult]) -> str:
        """创建幻觉检测报告"""
        if not results:
            return "未检测到幻觉"
        
        lines = [
            "=== 幻觉检测报告 ===",
            "",
            f"检测到 {len(results)} 个问题:",
        ]
        
        for i, result in enumerate(results, 1):
            severity_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(result.severity, "⚪")
            lines.append(f"{i}. {severity_emoji} [{result.hallucination_type.value}] {result.description}")
            if result.suggestion:
                lines.append(f"   建议: {result.suggestion}")
        
        return "\n".join(lines)


def create_hallucination_constraint_prompt() -> str:
    """创建幻觉约束提示词"""
    return """
## 幻觉硬约束（强制执行）

1. **严禁编造数据**：不得编造任何未提供的价格、库存、产量、政策、财报数据
2. **缺失数据说明**：关键数据缺失时直接说明缺失项，禁止自行估算
3. **事实与观点分离**：严格分块输出「客观数据事实」和「主观推演观点」
4. **禁止确定性结论**：所有预判必须附带概率区间与风控参考
5. **低可信度标注**：引用4级数据源必须单独标注风险

违反以上任何一条将导致报告被驳回重推。
"""
