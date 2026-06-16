"""
因子门控决策模块

基于评估结果做出三元决策：晋升 / 观察 / 淘汰。
门控阈值预设不可调（防 p-hacking），参考 Paper 1 的透明门控机制。

版本：v1.0
创建日期：2026-06-16
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class GateDecision:
    """门控决策结果"""
    factor_name: str
    decision: str  # 'promote' / 'observe' / 'eliminate'
    score: float   # 综合评分 (0-1)
    reasons: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)


class FactorGate:
    """
    因子门控决策器

    三元决策：
    - 晋升 (promote): 因子有效，纳入因子池
    - 观察 (observe): 数据不足或效果不确定，继续观察
    - 淘汰 (eliminate): 因子无效，从候选中移除

    门控规则（参考 Paper 1）：
    - 晋升：至少 2 项指标达到晋升阈值，且无项达到淘汰阈值
    - 淘汰：任意 2 项指标达到淘汰阈值
    - 观察：其余情况
    """

    # 门控阈值（预设不可调）
    DEFAULT_THRESHOLDS = {
        'icir_promote': 1.0,
        'icir_eliminate': 0.5,
        'ic_positive_pct_promote': 0.55,
        'ic_positive_pct_eliminate': 0.45,
        't_stat_promote': 2.0,
        't_stat_eliminate': 1.0,
        'ls_sharpe_promote': 1.0,
        'ls_sharpe_eliminate': 0.5,
        'min_ic_days': 30,
    }

    def __init__(self, thresholds: Dict = None):
        """
        初始化门控决策器

        Args:
            thresholds: 自定义阈值（覆盖默认值）
        """
        self.thresholds = {**self.DEFAULT_THRESHOLDS, **(thresholds or {})}

    def decide(self, factor_name: str, evaluation: Dict) -> GateDecision:
        """
        做出门控决策

        Args:
            factor_name: 因子名称
            evaluation: 评估结果字典（来自 FactorEvaluator）

        Returns:
            GateDecision
        """
        decision = GateDecision(
            factor_name=factor_name,
            decision='observe',
            score=0.0,
            metrics={
                'icir': evaluation.get('icir', 0),
                'ic_positive_pct': evaluation.get('ic_positive_pct', 0),
                't_stat': evaluation.get('t_stat', 0),
                'long_short_sharpe': evaluation.get('long_short_sharpe', 0),
                'ic_days': evaluation.get('ic_days', 0),
            }
        )

        # 检查数据充足性
        if evaluation.get('ic_days', 0) < self.thresholds['min_ic_days']:
            decision.decision = 'observe'
            decision.reasons.append(
                f"IC 样本不足 ({evaluation.get('ic_days', 0)} < {self.thresholds['min_ic_days']})"
            )
            decision.score = 0.3
            return decision

        # 逐项评估
        promote_count = 0
        eliminate_count = 0

        # ICIR
        icir = abs(evaluation.get('icir', 0))
        if icir >= self.thresholds['icir_promote']:
            promote_count += 1
            decision.reasons.append(f"ICIR={icir:.2f} >= {self.thresholds['icir_promote']}")
        elif icir < self.thresholds['icir_eliminate']:
            eliminate_count += 1
            decision.reasons.append(f"ICIR={icir:.2f} < {self.thresholds['icir_eliminate']}")

        # IC > 0 比例
        ic_pct = evaluation.get('ic_positive_pct', 0)
        if ic_pct >= self.thresholds['ic_positive_pct_promote']:
            promote_count += 1
            decision.reasons.append(f"IC>0比例={ic_pct:.1%} >= {self.thresholds['ic_positive_pct_promote']:.0%}")
        elif ic_pct < self.thresholds['ic_positive_pct_eliminate']:
            eliminate_count += 1
            decision.reasons.append(f"IC>0比例={ic_pct:.1%} < {self.thresholds['ic_positive_pct_eliminate']:.0%}")

        # t 统计量
        t_stat = abs(evaluation.get('t_stat', 0))
        if t_stat >= self.thresholds['t_stat_promote']:
            promote_count += 1
            decision.reasons.append(f"t={t_stat:.2f} >= {self.thresholds['t_stat_promote']}")
        elif t_stat < self.thresholds['t_stat_eliminate']:
            eliminate_count += 1
            decision.reasons.append(f"t={t_stat:.2f} < {self.thresholds['t_stat_eliminate']}")

        # 多空 Sharpe
        ls_sharpe = abs(evaluation.get('long_short_sharpe', 0))
        if ls_sharpe >= self.thresholds['ls_sharpe_promote']:
            promote_count += 1
            decision.reasons.append(f"多空Sharpe={ls_sharpe:.2f} >= {self.thresholds['ls_sharpe_promote']}")
        elif ls_sharpe < self.thresholds['ls_sharpe_eliminate']:
            eliminate_count += 1
            decision.reasons.append(f"多空Sharpe={ls_sharpe:.2f} < {self.thresholds['ls_sharpe_eliminate']}")

        # 决策逻辑
        if eliminate_count >= 2:
            decision.decision = 'eliminate'
            decision.score = 0.1
        elif promote_count >= 2:
            decision.decision = 'promote'
            decision.score = 0.8 + 0.2 * min(promote_count / 4, 1.0)
        else:
            decision.decision = 'observe'
            decision.score = 0.3 + 0.4 * (promote_count / 4)

        return decision

    def decide_batch(self, evaluations: Dict[str, Dict]) -> List[GateDecision]:
        """
        批量门控决策

        Args:
            evaluations: {factor_name: evaluation_dict}

        Returns:
            决策列表
        """
        decisions = []
        for name, eval_result in evaluations.items():
            decision = self.decide(name, eval_result)
            decisions.append(decision)
            logger.info(f"门控决策: {name} → {decision.decision} (score={decision.score:.2f})")

        return decisions

    def summarize(self, decisions: List[GateDecision]) -> Dict:
        """
        汇总门控决策结果

        Args:
            decisions: 决策列表

        Returns:
            {
                'promoted': List[str],
                'observed': List[str],
                'eliminated': List[str],
                'total': int,
            }
        """
        promoted = [d.factor_name for d in decisions if d.decision == 'promote']
        observed = [d.factor_name for d in decisions if d.decision == 'observe']
        eliminated = [d.factor_name for d in decisions if d.decision == 'eliminate']

        return {
            'promoted': promoted,
            'observed': observed,
            'eliminated': eliminated,
            'total': len(decisions),
            'promote_count': len(promoted),
            'observe_count': len(observed),
            'eliminate_count': len(eliminated),
        }
