"""
RL 模块

提供强化学习训练能力，借鉴 ElegantRL 的设计模式。

模块结构：
- base: AgentBase 基类和 ReplayBuffer
- networks: Actor/Critic 网络
- agent_ppo: PPO 算法实现
- futures_env: 期货交易 Gym 环境
- trainer: 训练循环

版本：v1.0
创建日期：2026-06-17
"""

from .base import AgentBase, ReplayBuffer
from .futures_env import FuturesTradingEnv

__all__ = [
    "AgentBase",
    "ReplayBuffer",
    "FuturesTradingEnv",
]
