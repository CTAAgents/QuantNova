"""
过拟合检测模块

检测策略是否过拟合：
- 蒙特卡洛模拟：打乱收益序列，检查原始夏普是否异常
- 参数敏感性测试：参数微调后收益变化大 = 过拟合
- 样本内外对比：训练集 vs 测试集表现差异
- 夏普比率检验：夏普 > 3 且无法解释 = 99% 过拟合

设计原则：
- 过拟合是量化策略的最大敌人
- 宁可错过机会，也不要相信虚假收益
- 多维度交叉验证，避免单一检验遗漏

文件：scripts/trend_scanner/overfitting_detector.py
"""

import logging
from collections.abc import Callable
from typing import Any

import numpy as np


logger = logging.getLogger(__name__)


class OverfittingDetector:
    """
    过拟合检测器

    多维度检测策略是否过拟合。
    """

    def __init__(
        self, sharpe_suspicious_threshold: float = 3.0, mc_simulations: int = 1000, sensitivity_threshold: float = 0.5
    ):
        """
        初始化过拟合检测器

        Args:
            sharpe_suspicious_threshold: 夏普可疑阈值（> 3 则高度怀疑）
            mc_simulations: 蒙特卡洛模拟次数
            sensitivity_threshold: 参数敏感性阈值
        """
        self.sharpe_suspicious_threshold = sharpe_suspicious_threshold
        self.mc_simulations = mc_simulations
        self.sensitivity_threshold = sensitivity_threshold

    def monte_carlo_test(self, returns: list[float]) -> dict[str, Any]:
        """
        蒙特卡洛模拟检验

        打乱收益序列，检查原始夏普是否异常。
        如果原始夏普在随机排列中很少出现（p < 0.05），则可能过拟合。

        Args:
            returns: 收益序列

        Returns:
            检验结果
        """
        if len(returns) < 20:
            return {"p_value": 1.0, "is_overfit": False, "reason": "样本量不足（< 20 笔）"}

        returns_array = np.array(returns)
        original_sharpe = np.mean(returns_array) / max(np.std(returns_array), 1e-8)

        # 蒙特卡洛模拟
        simulated_sharpes = []
        for _ in range(self.mc_simulations):
            shuffled = np.random.permutation(returns_array)
            sim_sharpe = np.mean(shuffled) / max(np.std(shuffled), 1e-8)
            simulated_sharpes.append(sim_sharpe)

        simulated_sharpes = np.array(simulated_sharpes)

        # 计算 p 值：随机排列中夏普 >= 原始夏普的比例
        p_value = float(np.mean(simulated_sharpes >= original_sharpe))

        # 判断是否过拟合
        is_overfit = p_value < 0.05

        return {
            "original_sharpe": round(original_sharpe, 3),
            "simulated_sharpe_mean": round(float(np.mean(simulated_sharpes)), 3),
            "simulated_sharpe_std": round(float(np.std(simulated_sharpes)), 3),
            "p_value": round(p_value, 4),
            "is_overfit": is_overfit,
            "confidence": f"{(1 - p_value) * 100:.1f}%",
            "reason": "夏普比率显著高于随机水平" if is_overfit else "夏普比率在正常范围内",
        }

    def sharpe_sanity_check(self, returns: list[float]) -> dict[str, Any]:
        """
        夏普比率合理性检验

        经验法则：回测夏普 > 3 且无法解释 → 99% 过拟合

        Args:
            returns: 收益序列

        Returns:
            检验结果
        """
        if not returns:
            return {"is_suspicious": False, "reason": "无数据"}

        returns_array = np.array(returns)
        sharpe = np.mean(returns_array) / max(np.std(returns_array), 1e-8)

        is_suspicious = sharpe > self.sharpe_suspicious_threshold

        return {
            "sharpe_ratio": round(sharpe, 3),
            "threshold": self.sharpe_suspicious_threshold,
            "is_suspicious": is_suspicious,
            "reason": f"夏普比率 {sharpe:.2f} 超过 {self.sharpe_suspicious_threshold}，高度怀疑过拟合"
            if is_suspicious
            else "夏普比率在合理范围内",
        }

    def parameter_sensitivity(
        self, strategy_fn: Callable, base_params: dict[str, Any], param_ranges: dict[str, list[float]], data: Any
    ) -> dict[str, Any]:
        """
        参数敏感性测试

        如果参数微调后收益变化很大，说明策略对参数敏感，容易过拟合。

        Args:
            strategy_fn: 策略函数
            base_params: 基础参数
            param_ranges: 参数范围 {参数名: [测试值列表]}
            data: 测试数据

        Returns:
            敏感性测试结果
        """
        # 计算基础收益
        try:
            base_result = strategy_fn(data, **base_params)
            base_return = base_result.get("total_return", 0) if isinstance(base_result, dict) else base_result
        except Exception as e:
            return {"error": f"策略执行失败: {e}"}

        sensitivities = {}

        for param_name, test_values in param_ranges.items():
            param_returns = []

            for test_value in test_values:
                test_params = base_params.copy()
                test_params[param_name] = test_value

                try:
                    result = strategy_fn(data, **test_params)
                    ret = result.get("total_return", 0) if isinstance(result, dict) else result
                    param_returns.append(ret)
                except Exception:
                    param_returns.append(0)

            # 计算敏感性：参数变化导致的收益标准差
            if param_returns:
                sensitivity = np.std(param_returns) / max(abs(base_return), 0.01)
                sensitivities[param_name] = {
                    "sensitivity": round(sensitivity, 3),
                    "returns": [round(r, 3) for r in param_returns],
                    "is_sensitive": sensitivity > self.sensitivity_threshold,
                }

        # 综合敏感性
        avg_sensitivity = np.mean([s["sensitivity"] for s in sensitivities.values()]) if sensitivities else 0
        is_overfit = avg_sensitivity > self.sensitivity_threshold

        return {
            "base_return": round(base_return, 3),
            "parameter_sensitivities": sensitivities,
            "average_sensitivity": round(avg_sensitivity, 3),
            "threshold": self.sensitivity_threshold,
            "is_overfit": is_overfit,
            "reason": f"参数敏感性 {avg_sensitivity:.2f} 超过阈值，策略对参数过于敏感"
            if is_overfit
            else "参数敏感性在可接受范围内",
        }

    def sample_split_test(self, returns: list[float], train_ratio: float = 0.7) -> dict[str, Any]:
        """
        样本内外对比检验

        如果训练集表现远好于测试集，说明过拟合。

        Args:
            returns: 收益序列
            train_ratio: 训练集比例

        Returns:
            检验结果
        """
        if len(returns) < 20:
            return {"error": "样本量不足（< 20 笔）"}

        split_idx = int(len(returns) * train_ratio)
        train_returns = returns[:split_idx]
        test_returns = returns[split_idx:]

        # 计算训练集和测试集的夏普
        train_sharpe = np.mean(train_returns) / max(np.std(train_returns), 1e-8)
        test_sharpe = np.mean(test_returns) / max(np.std(test_returns), 1e-8)

        # 计算衰减率
        decay_rate = (train_sharpe - test_sharpe) / max(abs(train_sharpe), 0.01)

        is_overfit = decay_rate > 0.5  # 衰减超过 50% 则怀疑过拟合

        return {
            "train_sharpe": round(train_sharpe, 3),
            "test_sharpe": round(test_sharpe, 3),
            "decay_rate": round(decay_rate, 3),
            "train_size": len(train_returns),
            "test_size": len(test_returns),
            "is_overfit": is_overfit,
            "reason": f"样本外夏普衰减 {decay_rate:.1%}，可能过拟合" if is_overfit else "样本内外表现一致",
        }

    def comprehensive_check(self, returns: list[float]) -> dict[str, Any]:
        """
        综合过拟合检测

        同时运行多种检测方法，综合判断。

        Args:
            returns: 收益序列

        Returns:
            综合检测结果
        """
        results = {
            "monte_carlo": self.monte_carlo_test(returns),
            "sharpe_check": self.sharpe_sanity_check(returns),
            "sample_split": self.sample_split_test(returns),
        }

        # 统计过拟合信号数
        overfit_signals = 0
        reasons = []

        if results["monte_carlo"].get("is_overfit"):
            overfit_signals += 1
            reasons.append(results["monte_carlo"]["reason"])

        if results["sharpe_check"].get("is_suspicious"):
            overfit_signals += 1
            reasons.append(results["sharpe_check"]["reason"])

        if results["sample_split"].get("is_overfit"):
            overfit_signals += 1
            reasons.append(results["sample_split"]["reason"])

        # 综合判断
        if overfit_signals >= 2:
            verdict = "高度怀疑过拟合"
            risk_level = "HIGH"
        elif overfit_signals == 1:
            verdict = "可能过拟合，需进一步验证"
            risk_level = "MEDIUM"
        else:
            verdict = "未检测到明显过拟合信号"
            risk_level = "LOW"

        return {
            "verdict": verdict,
            "risk_level": risk_level,
            "overfit_signals": overfit_signals,
            "total_checks": 3,
            "reasons": reasons,
            "details": results,
            "recommendation": self._get_recommendation(risk_level),
        }

    def _get_recommendation(self, risk_level: str) -> str:
        """获取建议"""
        if risk_level == "HIGH":
            return "高度怀疑过拟合，建议：1) 重新审视策略逻辑；2) 增加样本外测试；3) 降低仓位或暂停使用"
        elif risk_level == "MEDIUM":
            return "可能过拟合，建议：1) 进行参数敏感性测试；2) 增加蒙特卡洛模拟；3) 降低仓位观察"
        else:
            return "未检测到过拟合，继续观察"
