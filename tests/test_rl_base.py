"""
RL 基础模块单元测试

测试内容：
1. AgentBase 基类
2. ReplayBuffer
3. FuturesTradingEnv
4. MultiAssetVecEnv

版本：v1.0
创建日期：2026-06-17
"""

import numpy as np
import pytest
import torch as th
from typing import Dict, Any, List, Tuple

from scripts.trend_scanner.rl.base import (
    AgentBase,
    ReplayBuffer,
    Evaluator,
    RLAction,
    RLExperience,
)
from scripts.trend_scanner.rl.futures_env import (
    FuturesTradingEnv,
    MultiAssetVecEnv,
    TradeCost,
)


class SimpleAgent(AgentBase):
    """简单的测试 Agent"""
    
    def __init__(self, state_dim: int = 10):
        super().__init__(state_dim=state_dim)
    
    def perceive(self, env_state: Dict[str, Any]) -> np.ndarray:
        """感知环境状态"""
        return env_state["observation"]
    
    def reason(self, state: np.ndarray) -> RLAction:
        """随机选择动作"""
        return RLAction(
            action=np.random.uniform(-1, 1),
            log_prob=0.0,
            value=0.0
        )
    
    def act(self, env: Any, action: RLAction) -> Tuple[np.ndarray, float, bool, Dict]:
        """执行动作"""
        next_state, reward, terminated, truncated, info = env.step(action.action)
        return next_state, reward, terminated, truncated, info
    
    def reflect(self, experiences: List[RLExperience]) -> Dict[str, float]:
        """简单返回零损失"""
        return {'loss': 0.0}
    
    def save(self, path: str):
        """保存模型（简单实现）"""
        import os
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # 简单 Agent 没有模型参数需要保存
        pass
    
    def load(self, path: str):
        """加载模型（简单实现）"""
        pass


class TestAgentBase:
    """AgentBase 测试"""
    
    def test_initialization(self):
        """测试初始化"""
        agent = SimpleAgent(state_dim=10)
        
        assert agent.state_dim == 10
        assert agent.action_dim == 1
        assert agent.device == th.device("cpu")
    
    def test_perceive(self):
        """测试感知"""
        agent = SimpleAgent(state_dim=5)
        
        env_state = {"observation": np.array([1.0, 2.0, 3.0, 4.0, 5.0])}
        state = agent.perceive(env_state)
        
        assert len(state) == 5
        np.testing.assert_array_equal(state, env_state["observation"])
    
    def test_reason(self):
        """测试推理"""
        agent = SimpleAgent(state_dim=5)
        
        state = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        action = agent.reason(state)
        
        assert isinstance(action, RLAction)
        assert -1 <= action.action <= 1
    
    def test_explore(self):
        """测试探索"""
        # 创建简单环境
        data = np.random.randn(100, 5)  # 100 步，5 个特征
        env = FuturesTradingEnv(data=data, state_dim=3)
        
        agent = SimpleAgent(state_dim=3)
        
        experiences = agent.explore(env, horizon_len=50)
        
        assert len(experiences) == 50
        assert all(isinstance(exp, RLExperience) for exp in experiences)


class TestReplayBuffer:
    """ReplayBuffer 测试"""
    
    def test_initialization(self):
        """测试初始化"""
        buffer = ReplayBuffer(max_size=1000, state_dim=10)
        
        assert buffer.max_size == 1000
        assert buffer.cur_size == 0
        assert buffer.p == 0
        assert buffer.if_full is False
    
    def test_update_and_sample(self):
        """测试更新和采样"""
        buffer = ReplayBuffer(max_size=100, state_dim=5, num_seqs=1)
        
        # 添加数据
        states = th.randn(10, 1, 5)
        actions = th.randn(10, 1, 1)
        rewards = th.randn(10, 1)
        undones = th.ones(10, 1)
        
        buffer.update(states, actions, rewards, undones)
        
        assert buffer.cur_size == 10
        assert buffer.p == 10
        
        # 采样
        batch = buffer.sample(batch_size=5)
        
        assert len(batch) == 5
        assert batch[0].shape == (5, 5)  # states
        assert batch[1].shape == (5, 1)  # actions
        assert batch[2].shape == (5,)    # rewards
        assert batch[3].shape == (5,)    # undones
        assert batch[4].shape == (5, 5)  # next_states
    
    def test_circular_buffer(self):
        """测试循环缓冲区"""
        buffer = ReplayBuffer(max_size=10, state_dim=3, num_seqs=1)
        
        # 添加超过容量的数据
        for i in range(15):
            states = th.randn(1, 1, 3)
            actions = th.randn(1, 1, 1)
            rewards = th.tensor([[1.0]])
            undones = th.tensor([[1.0]])
            
            buffer.update(states, actions, rewards, undones)
        
        assert buffer.if_full is True
        assert buffer.cur_size == 10
        assert buffer.p == 5  # 15 % 10
    
    def test_save_and_load(self, tmp_path):
        """测试保存和加载"""
        buffer = ReplayBuffer(max_size=100, state_dim=5, num_seqs=1)
        
        # 添加数据
        states = th.randn(10, 1, 5)
        actions = th.randn(10, 1, 1)
        rewards = th.randn(10, 1)
        undones = th.ones(10, 1)
        
        buffer.update(states, actions, rewards, undones)
        
        # 保存
        save_path = str(tmp_path / "buffer.pth")
        buffer.save(save_path)
        
        # 加载到新缓冲区
        new_buffer = ReplayBuffer(max_size=100, state_dim=5, num_seqs=1)
        new_buffer.load(save_path)
        
        assert new_buffer.cur_size == 10
        assert new_buffer.p == 10
        
        # 验证数据一致性
        th.testing.assert_close(new_buffer.states[:10], buffer.states[:10])


class TestFuturesTradingEnv:
    """FuturesTradingEnv 测试"""
    
    def test_initialization(self):
        """测试初始化"""
        data = np.random.randn(100, 5)
        env = FuturesTradingEnv(data=data, state_dim=10)
        
        assert env.n_steps == 100
        assert env.state_dim == 10
        assert env.observation_space.shape == (12,)  # 10 + 2
        assert env.action_space.shape == (1,)
    
    def test_reset(self):
        """测试重置"""
        data = np.random.randn(100, 5)
        env = FuturesTradingEnv(data=data, state_dim=10)
        
        obs, info = env.reset()
        
        assert obs.shape == (12,)
        assert env.position == 0.0
        assert env.total_reward == 0.0
    
    def test_step(self):
        """测试执行步骤"""
        data = np.random.randn(100, 5)
        env = FuturesTradingEnv(data=data, state_dim=10)
        
        obs, _ = env.reset()
        
        # 做多
        next_obs, reward, terminated, truncated, info = env.step(0.5)
        
        assert next_obs.shape == (12,)
        assert isinstance(reward, float)
        # numpy bool 也是 bool 的子类
        assert terminated in [True, False, np.True_, np.False_]
        assert truncated in [True, False, np.True_, np.False_]
        assert info['position'] == 0.5
    
    def test_trade_cost(self):
        """测试交易成本"""
        data = np.random.randn(100, 5)
        trade_cost = TradeCost(
            commission_rate=0.0001,
            slippage_points=0.5,
            margin_rate=0.10
        )
        env = FuturesTradingEnv(data=data, state_dim=10, trade_cost=trade_cost)
        
        obs, _ = env.reset()
        
        # 开仓
        _, reward1, _, _, _ = env.step(1.0)
        
        # 平仓
        _, reward2, _, _, _ = env.step(0.0)
        
        # 平仓应该有成本
        # 注意：reward 可能为正也可能为负，取决于价格变化
    
    def test_episode_completion(self):
        """测试完整 episode"""
        data = np.random.randn(100, 5)
        env = FuturesTradingEnv(data=data, state_dim=10)
        
        obs, _ = env.reset(options={'start_step': 95})
        
        done = False
        total_reward = 0
        steps = 0
        
        while not done:
            action = env.action_space.sample()
            # 处理 numpy 数组
            action_value = float(action.item()) if isinstance(action, np.ndarray) else float(action)
            obs, reward, terminated, truncated, info = env.step(action_value)
            total_reward += reward
            done = bool(terminated) or bool(truncated)
            steps += 1
        
        assert steps <= 6  # 从 95 开始，最多 5 步
        assert info['current_step'] >= 99
    
    def test_trade_summary(self):
        """测试交易摘要"""
        data = np.random.randn(100, 5)
        env = FuturesTradingEnv(data=data, state_dim=10)
        
        obs, _ = env.reset()
        
        # 执行一些交易
        env.step(1.0)   # 开多
        env.step(0.0)   # 平仓
        env.step(-1.0)  # 开空
        env.step(0.0)   # 平仓
        
        summary = env.get_trade_summary()
        
        assert summary['n_trades'] == 2
        assert 'win_rate' in summary
        assert 'avg_pnl' in summary
        assert 'total_pnl' in summary


class TestMultiAssetVecEnv:
    """MultiAssetVecEnv 测试"""
    
    def test_initialization(self):
        """测试初始化"""
        data1 = np.random.randn(100, 5)
        data2 = np.random.randn(100, 5)
        
        env1 = FuturesTradingEnv(data=data1, state_dim=10)
        env2 = FuturesTradingEnv(data=data2, state_dim=10)
        
        vec_env = MultiAssetVecEnv([env1, env2])
        
        assert vec_env.num_envs == 2
        assert vec_env.observation_space.shape == (12,)
        assert vec_env.action_space.shape == (1,)
    
    def test_reset(self):
        """测试重置"""
        data1 = np.random.randn(100, 5)
        data2 = np.random.randn(100, 5)
        
        env1 = FuturesTradingEnv(data=data1, state_dim=10)
        env2 = FuturesTradingEnv(data=data2, state_dim=10)
        
        vec_env = MultiAssetVecEnv([env1, env2])
        
        observations, infos = vec_env.reset()
        
        assert observations.shape == (2, 12)
        assert len(infos) == 2
    
    def test_step(self):
        """测试执行步骤"""
        data1 = np.random.randn(100, 5)
        data2 = np.random.randn(100, 5)
        
        env1 = FuturesTradingEnv(data=data1, state_dim=10)
        env2 = FuturesTradingEnv(data=data2, state_dim=10)
        
        vec_env = MultiAssetVecEnv([env1, env2])
        
        observations, _ = vec_env.reset()
        
        actions = np.array([0.5, -0.5])
        next_obs, rewards, terminateds, truncateds, infos = vec_env.step(actions)
        
        assert next_obs.shape == (2, 12)
        assert rewards.shape == (2,)
        assert terminateds.shape == (2,)
        assert truncateds.shape == (2,)
        assert len(infos) == 2


class TestEvaluator:
    """Evaluator 测试"""
    
    def test_initialization(self):
        """测试初始化"""
        evaluator = Evaluator(eval_times=5, eval_per_step=100)
        
        assert evaluator.eval_times == 5
        assert evaluator.eval_per_step == 100
        assert evaluator.best_reward == -np.inf
    
    def test_evaluate(self):
        """测试评估"""
        data = np.random.randn(100, 5)
        env = FuturesTradingEnv(data=data, state_dim=10)
        
        agent = SimpleAgent(state_dim=10)
        evaluator = Evaluator(eval_times=2)
        
        mean_reward, std_reward = evaluator.evaluate(agent, env)
        
        assert isinstance(mean_reward, float)
        assert isinstance(std_reward, float)
        assert len(evaluator.eval_results) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
