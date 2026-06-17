"""
RL 模块

提供强化学习训练能力，借鉴 ElegantRL 的设计模式。

模块结构：
- base: AgentBase 基类和 ReplayBuffer
- networks: Actor/Critic 网络
- agent_ppo: PPO 算法实现
- futures_env: 期货交易 Gym 环境
- trainer: 训练循环
- walk_forward_rl: Walk-Forward RL 验证器

版本：v1.0
创建日期：2026-06-17
"""

from .base import AgentBase, ReplayBuffer
from .futures_env import FuturesTradingEnv
from .agent_ppo import AgentPPO, AgentPPOShared
from .networks import ActorPPO, CriticPPO, ActorCriticPPO, CriticEnsemble
from .trainer import RLTrainer, evaluate_agent
from .walk_forward_rl import RLWalkForwardValidator, walk_forward_validate_rl

__all__ = [
    # 基础
    "AgentBase",
    "ReplayBuffer",
    # 网络
    "ActorPPO",
    "CriticPPO",
    "ActorCriticPPO",
    "CriticEnsemble",
    # Agent
    "AgentPPO",
    "AgentPPOShared",
    # 环境
    "FuturesTradingEnv",
    # 训练
    "RLTrainer",
    "evaluate_agent",
    # 验证
    "RLWalkForwardValidator",
    "walk_forward_validate_rl",
]
