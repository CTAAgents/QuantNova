"""
Walk-Forward RL 验证器

扩展 WalkForwardValidator 支持 RL 策略的验证：
1. 在 IS 窗口训练 RL Agent
2. 在 OOS 窗口评估 RL Agent
3. 检查 IS/OOS 一致性
4. 集成到 Evolver 诊断流程

版本：v1.0
创建日期：2026-06-17
"""

import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from pathlib import Path

import numpy as np
import pandas as pd

from .base import AgentBase
from .futures_env import FuturesTradingEnv
from .agent_ppo import AgentPPO
from .trainer import RLTrainer, evaluate_agent
from ..trend_scanner_config import RLConfig, TrendScannerConfig
from ..walk_forward_validator import WalkForwardConfig, WalkForwardResult

logger = logging.getLogger(__name__)


@dataclass
class RLWindowResult:
    """单个窗口的 RL 验证结果"""
    
    window_idx: int
    is_start: pd.Timestamp
    is_end: pd.Timestamp
    oos_start: pd.Timestamp
    oos_end: pd.Timestamp
    
    # IS 指标
    is_reward: float
    is_sharpe: float
    is_win_rate: float
    is_max_drawdown: float
    is_trades: int
    
    # OOS 指标
    oos_reward: float
    oos_sharpe: float
    oos_win_rate: float
    oos_max_drawdown: float
    oos_trades: int
    
    # 一致性检查
    reward_ratio: float  # OOS/IS reward ratio
    sharpe_ratio: float  # OOS/IS sharpe ratio
    
    # 诊断结果
    passed: bool
    diagnosis: Dict[str, Any]


@dataclass
class RLWalkForwardResult:
    """Walk-Forward RL 验证的完整结果"""
    
    total_windows: int
    passed_windows: int
    pass_rate: float
    
    # OOS 汇总指标
    avg_oos_reward: float
    avg_oos_sharpe: float
    avg_oos_win_rate: float
    max_oos_drawdown: float
    
    # IS/OOS 一致性
    avg_reward_ratio: float
    avg_sharpe_ratio: float
    
    # 窗口结果
    window_results: List[RLWindowResult]
    
    # 诊断建议
    recommendations: List[str]


class RLWalkForwardValidator:
    """
    Walk-Forward RL 验证器
    
    扩展现有 WalkForwardValidator 支持 RL 策略的验证。
    核心流程：
    1. 在 IS 窗口训练 RL Agent
    2. 在 OOS 窗口评估 RL Agent
    3. 检查 IS/OOS 一致性
    4. 生成诊断建议
    
    与 Evolver 集成：
    - 当 pass_rate < 50% 时，建议重新设计状态空间或奖励函数
    - 当 avg_reward_ratio < 0.5 时，建议减少训练步数或增加正则化
    - 当 max_oos_drawdown > 20% 时，建议增加风险约束
    """
    
    def __init__(self,
                 config: Optional[WalkForwardConfig] = None,
                 rl_config: Optional[RLConfig] = None):
        """
        初始化 RL Walk-Forward 验证器
        
        Args:
            config: Walk-Forward 配置
            rl_config: RL 配置
        """
        self.config = config or WalkForwardConfig()
        self.rl_config = rl_config or RLConfig()
        
        # 诊断阈值
        self.reward_ratio_threshold = 0.5  # OOS/IS reward ratio 最小值
        self.sharpe_ratio_threshold = 0.6  # OOS/IS sharpe ratio 最小值
        self.pass_rate_threshold = 0.5     # 最小通过率
        
        logger.info(
            f"RLWalkForwardValidator 初始化: "
            f"优化窗口={self.config.optimization_window}天, "
            f"测试窗口={self.config.test_window}天"
        )
    
    def validate(self,
                 data: np.ndarray,
                 state_dim: int,
                 train_steps_per_window: int = 5000) -> RLWalkForwardResult:
        """
        执行 Walk-Forward RL 验证
        
        Args:
            data: K线数据，shape=(n_steps, n_features)
            state_dim: 状态维度
            train_steps_per_window: 每个窗口的训练步数
        
        Returns:
            RLWalkForwardResult: 验证结果
        """
        n_steps = len(data)
        window_size = self.config.optimization_window + self.config.test_window
        
        if n_steps < window_size:
            logger.warning(f"数据长度 {n_steps} 不足一个窗口 {window_size}")
            return self._empty_result()
        
        # 计算窗口
        window_starts = list(range(0, n_steps - window_size + 1, self.config.step_size))
        
        logger.info(f"开始 Walk-Forward RL 验证: {len(window_starts)} 个窗口")
        
        window_results = []
        
        for i, start_idx in enumerate(window_starts):
            logger.info(f"处理窗口 {i + 1}/{len(window_starts)}")
            
            # 计算窗口边界
            is_start_idx = start_idx
            is_end_idx = start_idx + self.config.optimization_window
            oos_start_idx = is_end_idx
            oos_end_idx = min(oos_start_idx + self.config.test_window, n_steps)
            
            # 提取数据
            is_data = data[is_start_idx:is_end_idx]
            oos_data = data[oos_start_idx:oos_end_idx]
            
            # 训练 RL Agent（IS 窗口）
            agent = self._train_agent(is_data, state_dim, train_steps_per_window)
            
            # 评估 IS 和 OOS
            is_metrics = self._evaluate_agent(agent, is_data, state_dim)
            oos_metrics = self._evaluate_agent(agent, oos_data, state_dim)
            
            # 计算一致性指标
            reward_ratio = oos_metrics['mean_reward'] / (is_metrics['mean_reward'] + 1e-8)
            sharpe_ratio = oos_metrics.get('sharpe', 0) / (is_metrics.get('sharpe', 1) + 1e-8)
            
            # 检查是否通过
            passed, diagnosis = self._check_pass_criteria(is_metrics, oos_metrics, reward_ratio, sharpe_ratio)
            
            # 记录结果
            window_result = RLWindowResult(
                window_idx=i,
                is_start=pd.Timestamp('2024-01-01') + pd.Timedelta(days=is_start_idx),
                is_end=pd.Timestamp('2024-01-01') + pd.Timedelta(days=is_end_idx),
                oos_start=pd.Timestamp('2024-01-01') + pd.Timedelta(days=oos_start_idx),
                oos_end=pd.Timestamp('2024-01-01') + pd.Timedelta(days=oos_end_idx),
                is_reward=is_metrics['mean_reward'],
                is_sharpe=is_metrics.get('sharpe', 0),
                is_win_rate=is_metrics.get('win_rate', 0),
                is_max_drawdown=is_metrics.get('max_drawdown', 0),
                is_trades=is_metrics.get('trades', 0),
                oos_reward=oos_metrics['mean_reward'],
                oos_sharpe=oos_metrics.get('sharpe', 0),
                oos_win_rate=oos_metrics.get('win_rate', 0),
                oos_max_drawdown=oos_metrics.get('max_drawdown', 0),
                oos_trades=oos_metrics.get('trades', 0),
                reward_ratio=reward_ratio,
                sharpe_ratio=sharpe_ratio,
                passed=passed,
                diagnosis=diagnosis,
            )
            
            window_results.append(window_result)
            
            logger.info(
                f"窗口 {i + 1}: IS Reward={is_metrics['mean_reward']:.4f}, "
                f"OOS Reward={oos_metrics['mean_reward']:.4f}, "
                f"Ratio={reward_ratio:.2f}, 通过={passed}"
            )
        
        # 汇总结果
        result = self._aggregate_results(window_results)
        
        # 生成建议
        result.recommendations = self._generate_recommendations(result)
        
        logger.info(
            f"Walk-Forward RL 验证完成: "
            f"通过率={result.pass_rate:.2%}, "
            f"平均 OOS Reward={result.avg_oos_reward:.4f}, "
            f"平均 Reward Ratio={result.avg_reward_ratio:.2f}"
        )
        
        return result
    
    def _train_agent(self, 
                     data: np.ndarray, 
                     state_dim: int,
                     train_steps: int) -> AgentBase:
        """
        在 IS 窗口训练 RL Agent
        
        Args:
            data: IS 窗口数据
            state_dim: 状态维度
            train_steps: 训练步数
        
        Returns:
            训练好的 Agent
        """
        # 创建环境
        env = FuturesTradingEnv(data=data, state_dim=state_dim - 2)  # -2 for position and pnl
        
        # 创建 Agent
        agent = AgentPPO(state_dim=state_dim, rl_config=self.rl_config)
        
        # 简单训练循环
        for step in range(0, train_steps, self.rl_config.horizon_len):
            experiences = agent.explore(env, self.rl_config.horizon_len)
            agent.reflect(experiences)
        
        return agent
    
    def _evaluate_agent(self, 
                        agent: AgentBase,
                        data: np.ndarray,
                        state_dim: int) -> Dict[str, float]:
        """
        评估 RL Agent
        
        Args:
            agent: RL Agent
            data: 评估数据
            state_dim: 状态维度
        
        Returns:
            评估指标
        """
        # 创建环境
        env = FuturesTradingEnv(data=data, state_dim=state_dim - 2)
        
        # 评估
        results = evaluate_agent(agent, env, n_episodes=3)
        
        # 计算额外指标
        rewards = []
        state, _ = env.reset()
        episode_reward = 0
        
        while True:
            action = agent.reason(state)
            state, reward, terminated, truncated, _ = agent.execute_action(env, action)
            episode_reward += reward
            
            if terminated or truncated:
                rewards.append(episode_reward)
                episode_reward = 0
                state, done = env.reset()
                if done:
                    break
        
        # 计算 Sharpe
        if len(rewards) > 1:
            results['sharpe'] = np.mean(rewards) / (np.std(rewards) + 1e-8)
        else:
            results['sharpe'] = 0.0
        
        # 计算胜率
        results['win_rate'] = sum(1 for r in rewards if r > 0) / (len(rewards) + 1e-8)
        
        # 计算最大回撤
        cumulative = np.cumsum(rewards)
        peak = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - peak) / (peak + 1e-8)
        results['max_drawdown'] = abs(np.min(drawdown))
        
        # 交易次数
        results['trades'] = len(env.trades)
        
        return results
    
    def _check_pass_criteria(self,
                            is_metrics: Dict[str, float],
                            oos_metrics: Dict[str, float],
                            reward_ratio: float,
                            sharpe_ratio: float) -> tuple[bool, Dict[str, Any]]:
        """
        检查是否通过验证标准
        
        Returns:
            (是否通过, 诊断结果)
        """
        diagnosis = {}
        passed = True
        
        # 检查 OOS 最小奖励
        if oos_metrics['mean_reward'] < 0:
            diagnosis['oos_reward'] = 'FAIL: OOS reward < 0'
            passed = False
        else:
            diagnosis['oos_reward'] = 'PASS'
        
        # 检查 Reward Ratio
        if reward_ratio < self.reward_ratio_threshold:
            diagnosis['reward_ratio'] = f'FAIL: OOS/IS ratio = {reward_ratio:.2f} < {self.reward_ratio_threshold}'
            passed = False
        else:
            diagnosis['reward_ratio'] = 'PASS'
        
        # 检查最大回撤
        if oos_metrics.get('max_drawdown', 0) > self.config.max_drawdown:
            diagnosis['max_drawdown'] = f'FAIL: OOS drawdown = {oos_metrics["max_drawdown"]:.2%} > {self.config.max_drawdown:.2%}'
            passed = False
        else:
            diagnosis['max_drawdown'] = 'PASS'
        
        # 检查交易次数
        if oos_metrics.get('trades', 0) < self.config.min_trades:
            diagnosis['trades'] = f'FAIL: OOS trades = {oos_metrics["trades"]} < {self.config.min_trades}'
            passed = False
        else:
            diagnosis['trades'] = 'PASS'
        
        return passed, diagnosis
    
    def _aggregate_results(self, window_results: List[RLWindowResult]) -> RLWalkForwardResult:
        """汇总窗口结果"""
        if not window_results:
            return self._empty_result()
        
        passed_windows = sum(1 for r in window_results if r.passed)
        pass_rate = passed_windows / len(window_results)
        
        # OOS 汇总指标
        oos_rewards = [r.oos_reward for r in window_results]
        oos_sharpes = [r.oos_sharpe for r in window_results if r.oos_sharpe != 0]
        oos_win_rates = [r.oos_win_rate for r in window_results]
        oos_drawdowns = [r.oos_max_drawdown for r in window_results]
        
        # 一致性指标
        reward_ratios = [r.reward_ratio for r in window_results]
        sharpe_ratios = [r.sharpe_ratio for r in window_results]
        
        return RLWalkForwardResult(
            total_windows=len(window_results),
            passed_windows=passed_windows,
            pass_rate=pass_rate,
            avg_oos_reward=np.mean(oos_rewards),
            avg_oos_sharpe=np.mean(oos_sharpes) if oos_sharpes else 0,
            avg_oos_win_rate=np.mean(oos_win_rates),
            max_oos_drawdown=np.max(oos_drawdowns),
            avg_reward_ratio=np.mean(reward_ratios),
            avg_sharpe_ratio=np.mean(sharpe_ratios),
            window_results=window_results,
            recommendations=[],
        )
    
    def _generate_recommendations(self, result: RLWalkForwardResult) -> List[str]:
        """生成诊断建议"""
        recommendations = []
        
        # 检查通过率
        if result.pass_rate < self.pass_rate_threshold:
            recommendations.append(
                f"通过率过低 ({result.pass_rate:.2%} < {self.pass_rate_threshold:.2%}): "
                "建议重新设计状态空间或奖励函数"
            )
        
        # 检查 Reward Ratio
        if result.avg_reward_ratio < self.reward_ratio_threshold:
            recommendations.append(
                f"IS/OOS 一致性差 (avg ratio = {result.avg_reward_ratio:.2f} < {self.reward_ratio_threshold}): "
                "建议减少训练步数、增加正则化或使用更简单的网络"
            )
        
        # 检查最大回撤
        if result.max_oos_drawdown > self.config.max_drawdown:
            recommendations.append(
                f"OOS 最大回撤过大 ({result.max_oos_drawdown:.2%} > {self.config.max_drawdown:.2%}): "
                "建议增加风险约束、使用更保守的策略或调整奖励函数"
            )
        
        # 检查 OOS 平均奖励
        if result.avg_oos_reward < 0:
            recommendations.append(
                f"OOS 平均奖励为负 ({result.avg_oos_reward:.4f}): "
                "建议检查数据质量、调整奖励函数或使用更保守的策略"
            )
        
        # 检查 OOS Sharpe
        if result.avg_oos_sharpe < self.config.min_sharpe:
            recommendations.append(
                f"OOS 平均 Sharpe 过低 ({result.avg_oos_sharpe:.2f} < {self.config.min_sharpe}): "
                "建议优化奖励函数、增加趋势约束或使用更稳定的策略"
            )
        
        if not recommendations:
            recommendations.append("验证通过，RL 策略泛化能力良好")
        
        return recommendations
    
    def _empty_result(self) -> RLWalkForwardResult:
        """返回空结果"""
        return RLWalkForwardResult(
            total_windows=0,
            passed_windows=0,
            pass_rate=0.0,
            avg_oos_reward=0.0,
            avg_oos_sharpe=0.0,
            avg_oos_win_rate=0.0,
            max_oos_drawdown=0.0,
            avg_reward_ratio=0.0,
            avg_sharpe_ratio=0.0,
            window_results=[],
            recommendations=["数据不足，无法进行验证"],
        )
    
    def save_result(self, result: RLWalkForwardResult, filepath: str):
        """保存验证结果"""
        output = {
            "total_windows": result.total_windows,
            "passed_windows": result.passed_windows,
            "pass_rate": result.pass_rate,
            "avg_oos_reward": result.avg_oos_reward,
            "avg_oos_sharpe": result.avg_oos_sharpe,
            "avg_oos_win_rate": result.avg_oos_win_rate,
            "max_oos_drawdown": result.max_oos_drawdown,
            "avg_reward_ratio": result.avg_reward_ratio,
            "avg_sharpe_ratio": result.avg_sharpe_ratio,
            "recommendations": result.recommendations,
            "windows": [],
        }
        
        for window in result.window_results:
            output["windows"].append({
                "window_idx": window.window_idx,
                "is_reward": window.is_reward,
                "oos_reward": window.oos_reward,
                "is_sharpe": window.is_sharpe,
                "oos_sharpe": window.oos_sharpe,
                "reward_ratio": window.reward_ratio,
                "sharpe_ratio": window.sharpe_ratio,
                "passed": window.passed,
                "diagnosis": window.diagnosis,
            })
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        logger.info(f"RL Walk-Forward 验证结果已保存到: {filepath}")


def walk_forward_validate_rl(
    data: np.ndarray,
    state_dim: int,
    rl_config: Optional[RLConfig] = None,
    wf_config: Optional[WalkForwardConfig] = None,
    train_steps_per_window: int = 5000,
) -> RLWalkForwardResult:
    """
    便捷函数：执行 Walk-Forward RL 验证
    
    Args:
        data: K线数据
        state_dim: 状态维度
        rl_config: RL 配置
        wf_config: Walk-Forward 配置
        train_steps_per_window: 每个窗口的训练步数
    
    Returns:
        RLWalkForwardResult: 验证结果
    """
    validator = RLWalkForwardValidator(config=wf_config, rl_config=rl_config)
    return validator.validate(data, state_dim, train_steps_per_window)
