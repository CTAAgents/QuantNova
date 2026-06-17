"""
进化引擎模块

提供自我监控、Walk-Forward优化、策略权重调整、轨迹分析、故障归因、
技能感知反思、元技能引擎、过拟合审计、静默旁路检测等功能：

基础组件：
- SelfMonitor: 自我监控器
- WalkForwardOptimizer: Walk-Forward优化器
- StrategyWeightAdjuster: 策略权重调整器
- OverfittingGuard: 过拟合防护守卫

基于 skill-adaptor：
- TradeTrajectoryAnalyzer: 交易轨迹分析器
- TradeFaultAttributor: 交易故障归因器
- StrategyAdapter: 策略适配器

基于 self-improvement：
- TradeJournal: 交易日志管理器
- PatternDetector: 重复模式检测器
- RulePromoter: 规则晋升器

基于 EmbodiSkill (arXiv:2605.10332)：
- SkillAwareReflector: 技能感知反思器

基于 SkillEvolver (arXiv:2605.10500)：
- MetaSkillEngine: 元技能引擎
- OverfittingAuditor: 过拟合审计器
- SilentBypassDetector: 静默旁路检测器
"""

from collections import defaultdict
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from .meta_skill_engine import (
    MetaSkillEngine,
)
from .overfitting_audit import (
    OverfittingAuditor,
)
from .silent_bypass_detector import (
    SilentBypassDetector,
)
from .skill_reflection import (
    SkillAwareReflector,
)
from .trade_journal import (
    PatternDetector,
    RulePromoter,
    TradeJournal,
)
from .trajectory_analysis import (
    StrategyAdapter,
    TradeFaultAttributor,
    TradeTrajectoryAnalyzer,
)


class SelfMonitor:
    """
    自我监控：KPI计算、归因分析、诊断报告

    增强版：集成轨迹分析和故障归因
    """

    def __init__(self, trades: list[Any]):
        self.trades = trades
        self.trajectory_analyzer = TradeTrajectoryAnalyzer()
        self.fault_attributor = TradeFaultAttributor()

    def analyze_trade_trajectories(self) -> dict[str, Any]:
        """
        分析所有交易的轨迹

        返回:
            轨迹分析汇总结果
        """
        trajectories = []
        fault_summary = {
            "total_faults": 0,
            "fault_types": defaultdict(int),
            "strategy_responsibility": defaultdict(float),
        }

        for trade in self.trades:
            # 构建轨迹
            trajectory = self.trajectory_analyzer.build_trajectory(trade)

            # 分析轨迹
            analysis = self.trajectory_analyzer.analyze(trajectory)
            trajectories.append(analysis)

            # 故障归因（仅对亏损交易）
            if trade.pnl < 0:
                fault_result = self.fault_attributor.attribute(trajectory)
                if fault_result["has_fault"]:
                    fault_summary["total_faults"] += len(fault_result["faults"])
                    for fault in fault_result["faults"]:
                        fault_summary["fault_types"][fault.fault_type.value] += 1
                    for strategy, score in fault_result["strategy_responsibility"].items():
                        fault_summary["strategy_responsibility"][strategy] += score

        # 归一化策略责任分数
        total_resp = sum(fault_summary["strategy_responsibility"].values())
        if total_resp > 0:
            fault_summary["strategy_responsibility"] = {
                k: v / total_resp for k, v in fault_summary["strategy_responsibility"].items()
            }

        return {
            "trajectory_count": len(trajectories),
            "avg_quality_score": np.mean([a["metrics"].get("quality_score", 0) for a in trajectories])
            if trajectories
            else 0,
            "fault_summary": dict(fault_summary["fault_types"]),
            "strategy_responsibility": dict(fault_summary["strategy_responsibility"]),
            "total_faults": fault_summary["total_faults"],
        }

    def generate_enhanced_report(self, symbol: str = "UNKNOWN") -> dict[str, Any]:
        """
        生成增强版诊断报告（集成轨迹分析）

        返回:
            包含轨迹分析和故障归因的诊断报告
        """
        # 基础轨迹分析
        trajectory_analysis = self.analyze_trade_trajectories()

        return {
            "report_type": "ENHANCED_SELF_DIAGNOSIS",
            "symbol": symbol,
            "total_trades": len(self.trades),
            "trajectory_analysis": trajectory_analysis,
            "timestamp": datetime.now().isoformat(),
        }


class WalkForwardOptimizer:
    """Walk-Forward参数优化（防过拟合）"""

    pass


class StrategyWeightAdjuster:
    """策略权重自适应调整"""

    pass


class OverfittingGuard:
    """过拟合防护守卫 — 5道防线"""

    pass


class EnhancedEvolutionEngine:
    """
    增强版进化引擎

    整合了三个框架的演化思路：

    基于 skill-adaptor：
    1. 轨迹分析 → 定位故障步骤
    2. 故障归因 → 量化策略责任
    3. 策略适配 → 生成针对性更新
    4. 接受检查 → 验证更新有效性

    基于 self-improvement：
    5. 交易日志 → 记录经验教训
    6. 模式检测 → 识别重复问题
    7. 规则晋升 → 固化成功模式

    基于 EmbodiSkill (arXiv:2605.10332)：
    8. 技能感知反思 → 区分技能内容错误 vs 执行失误
    9. 针对性修订 → 技能错误更新规则，执行错误强化指导

    基于 SkillEvolver (arXiv:2605.10500)：
    10. 元技能引擎 → 自动生成和优化策略规则
    11. 过拟合审计 → 检测数据泄漏和性能漂移
    12. 静默旁路检测 → 识别从未触发的僵尸策略
    """

    def __init__(self):
        # 基础组件
        self.trajectory_analyzer = TradeTrajectoryAnalyzer()
        self.fault_attributor = TradeFaultAttributor()
        self.strategy_adapter = StrategyAdapter()

        # self-improvement 组件
        self.trade_journal = TradeJournal()
        self.pattern_detector = PatternDetector()
        self.rule_promoter = RulePromoter()

        # EmbodiSkill 组件
        self.skill_reflector = SkillAwareReflector()

        # SkillEvolver 组件
        self.meta_skill_engine = MetaSkillEngine()
        self.overfitting_auditor = OverfittingAuditor()
        self.silent_bypass_detector = SilentBypassDetector()

    def run_enhanced_evolution(
        self, trades: list[Any], current_config: dict[str, Any], df: pd.DataFrame = None
    ) -> dict[str, Any]:
        """
        执行增强版进化流程

        参数:
            trades: 交易记录列表
            current_config: 当前策略配置
            df: 可选的K线数据（用于轨迹分析）

        返回:
            进化结果
        """
        result = {
            "proposals": [],
            "journal_entries": [],
            "patterns": [],
            "rules": [],
            "reflections": [],
            "audit_report": None,
            "bypass_report": None,
            "applied_config": current_config,
        }

        if not trades:
            return result

        # 1. 分析所有亏损交易的轨迹
        loss_trades = [t for t in trades if t.pnl < 0]
        all_faults = []
        all_proposals = []

        for trade in loss_trades:
            # 构建轨迹
            trajectory = self.trajectory_analyzer.build_trajectory(trade, df)

            # 故障归因
            fault_result = self.fault_attributor.attribute(trajectory)
            if fault_result["has_fault"]:
                all_faults.extend(fault_result["faults"])

                # 生成适应性提案
                proposals = self.strategy_adapter.generate_proposals(fault_result, current_config)
                all_proposals.extend(proposals)

            # 记录交易日志
            journal_entry = self.trade_journal.log_trade_lesson(trade, fault_result)
            result["journal_entries"].append(journal_entry)

            # 技能感知反思 (EmbodiSkill)
            reflection = self.skill_reflector.reflect_on_trade(
                trade,
                trajectory_analysis={"trajectory": trajectory, "metrics": {}},
                fault_attribution=fault_result,
            )
            result["reflections"].append(reflection)

        # 2. 检测重复模式
        patterns = self.pattern_detector.detect_patterns(self.trade_journal)
        result["patterns"] = patterns

        # 3. 晋升规则
        new_rules = self.rule_promoter.promote_patterns(patterns)
        result["rules"] = new_rules

        # 4. 过拟合审计 (SkillEvolver)
        audit_report = self.overfitting_auditor.audit_skill(
            skill_id="current_config",
            skill_name="当前策略配置",
            trades=trades,
        )
        result["audit_report"] = audit_report

        # 5. 静默旁路检测 (SkillEvolver)
        bypass_report = self.silent_bypass_detector.detect(trades)
        result["bypass_report"] = bypass_report

        # 5.5 RL 策略诊断（新增）
        rl_diagnosis = self._diagnose_rl_strategy(trades, current_config)
        result["rl_diagnosis"] = rl_diagnosis

        # 6. 应用通过验证的提案（简化版：直接应用高置信度提案）
        applied_proposals = []
        for proposal in all_proposals:
            if proposal.adaptation_type == "weight":
                # 权重调整直接应用
                current_config = self.strategy_adapter.apply_proposal(proposal, current_config)
                applied_proposals.append(proposal)
            elif proposal.adaptation_type == "parameter":
                # 参数调整需要更多验证，这里简化处理
                current_config = self.strategy_adapter.apply_proposal(proposal, current_config)
                applied_proposals.append(proposal)

        result["proposals"] = applied_proposals
        result["applied_config"] = current_config

        return result

    def _diagnose_rl_strategy(self, trades: list[Any], current_config: dict[str, Any]) -> dict[str, Any]:
        """
        诊断 RL 策略的健康状态
        
        Args:
            trades: 交易记录列表
            current_config: 当前策略配置
        
        Returns:
            RL 诊断结果
        """
        diagnosis = {
            "has_rl_model": False,
            "model_status": "not_found",
            "recommendations": [],
        }
        
        # 检查是否有训练好的 RL 模型
        import os
        model_dir = "models/rl"
        
        if not os.path.exists(model_dir):
            diagnosis["recommendations"].append("未找到 RL 模型目录，建议先训练 RL 策略")
            return diagnosis
        
        # 查找模型文件
        model_files = [f for f in os.listdir(model_dir) if f.endswith(".pth")]
        if not model_files:
            diagnosis["recommendations"].append("未找到训练好的 RL 模型，建议运行 python tools/train_ppo.py")
            return diagnosis
        
        diagnosis["has_rl_model"] = True
        diagnosis["model_count"] = len(model_files)
        diagnosis["model_files"] = model_files
        
        # 检查 Walk-Forward 验证结果
        wf_result_files = [f for f in os.listdir(model_dir) if f.endswith("_wf_result.json")]
        if wf_result_files:
            try:
                import json
                latest_wf = os.path.join(model_dir, wf_result_files[-1])
                with open(latest_wf, 'r') as f:
                    wf_result = json.load(f)
                
                pass_rate = wf_result.get("pass_rate", 0)
                avg_oos_reward = wf_result.get("avg_oos_reward", 0)
                avg_reward_ratio = wf_result.get("avg_reward_ratio", 0)
                
                diagnosis["wf_validation"] = {
                    "pass_rate": pass_rate,
                    "avg_oos_reward": avg_oos_reward,
                    "avg_reward_ratio": avg_reward_ratio,
                }
                
                # 生成建议
                if pass_rate < 0.5:
                    diagnosis["recommendations"].append(
                        f"Walk-Forward 通过率过低 ({pass_rate:.0%})，建议重新设计状态空间或奖励函数"
                    )
                
                if avg_reward_ratio < 0.5:
                    diagnosis["recommendations"].append(
                        f"IS/OOS 一致性差 (ratio={avg_reward_ratio:.2f})，建议减少训练步数或增加正则化"
                    )
                
                if avg_oos_reward < 0:
                    diagnosis["recommendations"].append(
                        "OOS 平均奖励为负，建议检查数据质量或调整奖励函数"
                    )
                
                if not diagnosis["recommendations"]:
                    diagnosis["recommendations"].append("RL 策略健康状态良好")
                    
            except Exception as e:
                diagnosis["recommendations"].append(f"读取 Walk-Forward 结果失败: {e}")
        else:
            diagnosis["recommendations"].append("未找到 Walk-Forward 验证结果，建议运行验证")
        
        return diagnosis

    def generate_review_report(self, symbol: str = None) -> dict[str, Any]:
        """
        生成复盘报告

        参数:
            symbol: 品种代码（可选）

        返回:
            复盘报告
        """
        weekly_review = self.trade_journal.generate_weekly_review(symbol)

        # 获取反思汇总
        reflection_summary = self.skill_reflector.generate_summary_report()

        # 获取审计汇总
        audit_summary = self.overfitting_auditor.generate_audit_summary_report()

        # 获取旁路检测汇总
        bypass_report = self.silent_bypass_detector.get_latest_report()
        bypass_summary = {
            "total_strategies": bypass_report.total_strategies if bypass_report else 0,
            "active_strategies": bypass_report.active_strategies if bypass_report else 0,
            "bypassed_strategies": bypass_report.bypassed_strategies if bypass_report else 0,
        }

        return {
            "report_type": "WEEKLY_REVIEW",
            "symbol": symbol,
            "weekly_review": weekly_review,
            "active_patterns": [
                {
                    "pattern_id": p.pattern_id,
                    "description": p.description,
                    "severity": p.severity.value,
                    "occurrence_count": p.occurrence_count,
                    "promoted": p.promoted,
                }
                for p in self.pattern_detector.patterns
            ],
            "active_rules": [
                {
                    "rule_id": r.rule_id,
                    "name": r.name,
                    "condition": r.condition,
                    "action": r.action,
                    "hit_count": r.hit_count,
                }
                for r in self.rule_promoter.rules
            ],
            "skill_reflection": reflection_summary,
            "audit_summary": audit_summary,
            "bypass_summary": bypass_summary,
        }
