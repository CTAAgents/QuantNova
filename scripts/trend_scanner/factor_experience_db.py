"""
因子经验数据库

记录因子演化的完整轨迹（成功+失败），实现"从失败中学习"。
基于 FactorEngine 论文的轨迹感知优化思想。

核心功能：
1. 记录每次因子评估的完整轨迹
2. 提取失败模式和成功模式
3. 生成反馈注入因子生成器

版本：v1.0
创建日期：2026-06-16
"""

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime


logger = logging.getLogger(__name__)


@dataclass
class EvolutionStep:
    """演化步骤"""

    round: int
    factor_name: str
    logic: str  # 因子逻辑描述
    params: dict  # 参数
    icir: float
    t_stat: float
    decision: str  # promote/observe/eliminate
    reasons: list[str]  # 决策原因
    timestamp: str = ""


@dataclass
class FactorExperience:
    """因子经验记录"""

    factor_id: str
    trajectory: list[EvolutionStep]
    failure_patterns: list[str]  # 提取的失败模式
    success_patterns: list[str]  # 提取的成功模式
    lessons: list[str]  # 提炼的教训
    category: str = "unknown"  # 因子分类
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "factor_id": self.factor_id,
            "trajectory": [asdict(s) for s in self.trajectory],
            "failure_patterns": self.failure_patterns,
            "success_patterns": self.success_patterns,
            "lessons": self.lessons,
            "category": self.category,
            "created_at": self.created_at,
        }


class FactorExperienceDB:
    """
    因子经验数据库

    存储和检索因子演化经验，支持：
    - 记录演化轨迹
    - 提取失败/成功模式
    - 生成反馈注入生成器
    """

    def __init__(self, db_path: str = None):
        """
        初始化经验数据库

        Args:
            db_path: 数据库文件路径
        """
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "factor_experience.json"
            )
        self.db_path = db_path
        self.experiences: list[FactorExperience] = self._load()

    def record_trajectory(self, factor_id: str, trajectory: list[dict], category: str = "unknown"):
        """
        记录因子演化轨迹

        Args:
            factor_id: 因子 ID
            trajectory: 演化步骤列表
                [{'round': 1, 'factor_name': '...', 'logic': '...', 'icir': 0.3, ...}]
            category: 因子分类
        """
        steps = []
        for t in trajectory:
            step = EvolutionStep(
                round=t.get("round", 0),
                factor_name=t.get("factor_name", ""),
                logic=t.get("logic", ""),
                params=t.get("params", {}),
                icir=t.get("icir", 0),
                t_stat=t.get("t_stat", 0),
                decision=t.get("decision", "observe"),
                reasons=t.get("reasons", []),
                timestamp=t.get("timestamp", datetime.now().isoformat()),
            )
            steps.append(step)

        # 提取模式和教训
        failure_patterns = self._extract_failure_patterns(steps)
        success_patterns = self._extract_success_patterns(steps)
        lessons = self._extract_lessons(steps, failure_patterns, success_patterns)

        experience = FactorExperience(
            factor_id=factor_id,
            trajectory=steps,
            failure_patterns=failure_patterns,
            success_patterns=success_patterns,
            lessons=lessons,
            category=category,
            created_at=datetime.now().isoformat(),
        )

        # 检查是否已存在
        existing = [e for e in self.experiences if e.factor_id == factor_id]
        if existing:
            logger.info(f"更新已有经验: {factor_id}")
            self.experiences = [e for e in self.experiences if e.factor_id != factor_id]

        self.experiences.append(experience)
        self._save()

        logger.info(f"记录经验: {factor_id}, 步骤={len(steps)}, 教训={len(lessons)}")

    def record_from_evolution_result(self, evolution_result, category: str = "unknown"):
        """
        从进化引擎结果中自动记录经验

        Args:
            evolution_result: EvolutionResult 对象
            category: 因子分类
        """
        for round_data in evolution_result.rounds:
            for decision in round_data.decisions:
                factor_name = decision.get("factor_name", "")
                if decision.get("decision") == "eliminate":
                    # 记录被淘汰因子的轨迹
                    trajectory = [
                        {
                            "round": round_data.round_num,
                            "factor_name": factor_name,
                            "logic": "",
                            "params": {},
                            "icir": decision.get("metrics", {}).get("icir", 0) if "metrics" in decision else 0,
                            "t_stat": 0,
                            "decision": decision.get("decision", ""),
                            "reasons": decision.get("reasons", []),
                            "timestamp": round_data.timestamp,
                        }
                    ]
                    self.record_trajectory(
                        factor_id=f"{factor_name}_r{round_data.round_num}",
                        trajectory=trajectory,
                        category=category,
                    )

    def get_failure_lessons(self, limit: int = 10) -> list[str]:
        """
        获取最近的失败教训（用于注入生成器提示词）

        Args:
            limit: 最大返回数

        Returns:
            教训列表
        """
        lessons = []
        for exp in reversed(self.experiences):
            for lesson in exp.lessons:
                if lesson not in lessons:
                    lessons.append(lesson)
            if len(lessons) >= limit:
                break
        return lessons[:limit]

    def get_success_patterns(self, limit: int = 10) -> list[str]:
        """
        获取最近的成功模式

        Args:
            limit: 最大返回数

        Returns:
            成功模式列表
        """
        patterns = []
        for exp in reversed(self.experiences):
            for pattern in exp.success_patterns:
                if pattern not in patterns:
                    patterns.append(pattern)
            if len(patterns) >= limit:
                break
        return patterns[:limit]

    def get_failure_patterns(self, limit: int = 10) -> list[str]:
        """
        获取最近的失败模式

        Args:
            limit: 最大返回数

        Returns:
            失败模式列表
        """
        patterns = []
        for exp in reversed(self.experiences):
            for pattern in exp.failure_patterns:
                if pattern not in patterns:
                    patterns.append(pattern)
            if len(patterns) >= limit:
                break
        return patterns[:limit]

    def generate_feedback_prompt(self) -> str:
        """
        生成反馈提示词（用于注入因子生成器）

        Returns:
            提示词文本
        """
        failure_lessons = self.get_failure_lessons(5)
        success_patterns = self.get_success_patterns(5)
        failure_patterns = self.get_failure_patterns(5)

        lines = []

        if failure_lessons:
            lines.append("## 历史失败教训")
            for i, lesson in enumerate(failure_lessons, 1):
                lines.append(f"{i}. {lesson}")

        if failure_patterns:
            lines.append("\n## 应避免的失败模式")
            for i, pattern in enumerate(failure_patterns, 1):
                lines.append(f"{i}. {pattern}")

        if success_patterns:
            lines.append("\n## 可参考的成功模式")
            for i, pattern in enumerate(success_patterns, 1):
                lines.append(f"{i}. {pattern}")

        if not lines:
            return ""

        return "\n".join(lines)

    def get_summary(self) -> dict:
        """获取经验库摘要"""
        total_experiences = len(self.experiences)
        total_lessons = sum(len(e.lessons) for e in self.experiences)
        total_failures = sum(len(e.failure_patterns) for e in self.experiences)
        total_successes = sum(len(e.success_patterns) for e in self.experiences)

        categories = {}
        for exp in self.experiences:
            cat = exp.category
            if cat not in categories:
                categories[cat] = 0
            categories[cat] += 1

        return {
            "total_experiences": total_experiences,
            "total_lessons": total_lessons,
            "total_failure_patterns": total_failures,
            "total_success_patterns": total_successes,
            "categories": categories,
        }

    def _extract_failure_patterns(self, steps: list[EvolutionStep]) -> list[str]:
        """从演化步骤中提取失败模式"""
        patterns = []

        for step in steps:
            if step.decision == "eliminate":
                # 分析淘汰原因
                for reason in step.reasons:
                    if "ICIR" in reason:
                        patterns.append(f"ICIR 过低: {step.factor_name} 的 ICIR={step.icir:.2f}")
                    if "IC>0" in reason:
                        patterns.append(f"IC 方向不稳定: {step.factor_name}")
                    if "t=" in reason:
                        patterns.append(f"t 统计量不显著: {step.factor_name}")

                # 分析因子逻辑
                if "momentum" in step.factor_name.lower():
                    patterns.append("简单动量因子在期货市场预测力弱")
                if "volatility" in step.factor_name.lower():
                    patterns.append("简单波动率因子截面区分力不足")

        return list(set(patterns))

    def _extract_success_patterns(self, steps: list[EvolutionStep]) -> list[str]:
        """从演化步骤中提取成功模式"""
        patterns = []

        for step in steps:
            if step.decision == "promote":
                patterns.append(f"有效因子: {step.factor_name} (ICIR={step.icir:.2f})")
                if step.logic:
                    patterns.append(f"有效逻辑: {step.logic}")

        return list(set(patterns))

    def _extract_lessons(
        self, steps: list[EvolutionStep], failure_patterns: list[str], success_patterns: list[str]
    ) -> list[str]:
        """提炼教训"""
        lessons = []

        # 从失败模式中提炼教训
        if failure_patterns:
            lessons.append("简单技术因子（动量/波动率/RSI）在期货市场截面预测力弱")
            lessons.append("需要更复杂的因子逻辑或更多数据支撑")

        # 从成功模式中提炼教训
        if success_patterns:
            lessons.append("有效的因子通常结合多个维度的信息")

        # 分析参数模式
        icir_values = [s.icir for s in steps if s.icir > 0]
        if icir_values:
            avg_icir = sum(icir_values) / len(icir_values)
            if avg_icir < 0.3:
                lessons.append(f"平均 ICIR={avg_icir:.2f}，因子整体预测力不足")

        return lessons

    def _load(self) -> list[FactorExperience]:
        """加载经验数据库"""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, encoding="utf-8") as f:
                    data = json.load(f)

                experiences = []
                for item in data.get("experiences", []):
                    trajectory = [EvolutionStep(**step) for step in item.get("trajectory", [])]
                    exp = FactorExperience(
                        factor_id=item["factor_id"],
                        trajectory=trajectory,
                        failure_patterns=item.get("failure_patterns", []),
                        success_patterns=item.get("success_patterns", []),
                        lessons=item.get("lessons", []),
                        category=item.get("category", "unknown"),
                        created_at=item.get("created_at", ""),
                    )
                    experiences.append(exp)
                return experiences
            except Exception as e:
                logger.error(f"加载经验数据库失败: {e}")
        return []

    def _save(self):
        """保存经验数据库"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        data = {
            "experiences": [e.to_dict() for e in self.experiences],
            "summary": self.get_summary(),
            "updated_at": datetime.now().isoformat(),
        }

        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.debug(f"经验数据库已保存: {len(self.experiences)} 条经验")

    def clear(self):
        """清空经验数据库"""
        self.experiences = []
        self._save()
