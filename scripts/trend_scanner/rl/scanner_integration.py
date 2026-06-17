"""
RL Scanner 集成模块

将训练好的 RL 策略作为新的决策来源集成到 Scanner：
1. 加载训练好的 RL Agent
2. 基于当前市场状态生成 RL 信号
3. 与传统技术指标信号融合

版本：v1.0
创建日期：2026-06-17
"""

import logging
import os
from typing import Dict, Any, Optional, List

import numpy as np
import torch as th

from .agent_ppo import AgentPPO
from .base import RLAction
from ..trend_scanner_config import RLConfig

logger = logging.getLogger(__name__)


class RLSignalGenerator:
    """
    RL 信号生成器
    
    将训练好的 RL Agent 集成为信号来源：
    1. 加载训练好的模型
    2. 基于技术指标状态生成仓位建议
    3. 输出信号强度和方向
    
    使用方式：
        generator = RLSignalGenerator("models/rl/RB_best.pth")
        signal = generator.generate_signal(state_features)
    """
    
    def __init__(self,
                 model_path: str,
                 state_dim: int = 6,
                 rl_config: Optional[RLConfig] = None):
        """
        初始化 RL 信号生成器
        
        Args:
            model_path: 模型文件路径
            state_dim: 状态维度
            rl_config: RL 配置
        """
        self.model_path = model_path
        self.state_dim = state_dim
        self.rl_config = rl_config or RLConfig()
        
        # 加载 Agent
        self.agent = self._load_agent()
        
        logger.info(f"RL 信号生成器初始化: model={model_path}")
    
    def _load_agent(self) -> AgentPPO:
        """加载训练好的 Agent"""
        if not os.path.exists(self.model_path):
            logger.warning(f"模型文件不存在: {self.model_path}")
            # 返回一个未训练的 Agent
            return AgentPPO(state_dim=self.state_dim, rl_config=self.rl_config)
        
        agent = AgentPPO(state_dim=self.state_dim, rl_config=self.rl_config)
        agent.load(self.model_path)
        
        logger.info(f"已加载 RL 模型: {self.model_path}")
        return agent
    
    def generate_signal(self, 
                       state_features: np.ndarray,
                       current_position: float = 0.0) -> Dict[str, Any]:
        """
        生成 RL 信号
        
        Args:
            state_features: 状态特征向量
            current_position: 当前持仓 [-1, 1]
        
        Returns:
            信号字典
        """
        # 构建完整状态（技术指标 + 持仓 + 未实现盈亏）
        full_state = np.zeros(self.state_dim)
        full_state[:len(state_features)] = state_features
        full_state[len(state_features)] = current_position
        full_state[len(state_features) + 1] = 0.0  # 未实现盈亏（简化）
        
        # 使用 Agent 生成动作
        action = self.agent.reason(full_state)
        
        # 解析信号
        target_position = action.action
        position_change = target_position - current_position
        
        # 生成信号
        signal = {
            'source': 'rl',
            'target_position': target_position,
            'current_position': current_position,
            'position_change': position_change,
            'direction': 'LONG' if position_change > 0.1 else ('SHORT' if position_change < -0.1 else 'NEUTRAL'),
            'strength': abs(position_change),
            'confidence': min(abs(position_change) * 2, 1.0),  # 简化的置信度
            'log_prob': action.log_prob,
            'value': action.value,
        }
        
        return signal
    
    def batch_generate_signals(self,
                              states: np.ndarray,
                              positions: np.ndarray) -> List[Dict[str, Any]]:
        """
        批量生成信号
        
        Args:
            states: 状态特征数组 (n, feature_dim)
            positions: 持仓数组 (n,)
        
        Returns:
            信号列表
        """
        signals = []
        
        for i in range(len(states)):
            signal = self.generate_signal(states[i], positions[i])
            signals.append(signal)
        
        return signals


class RLEnsembleSignalGenerator:
    """
    RL 集成信号生成器
    
    使用多个 RL Agent 的集成来生成更稳定的信号：
    1. 加载多个训练好的模型
    2. 对每个模型的输出取平均
    3. 提供信号的一致性度量
    
    使用方式：
        generator = RLEnsembleSignalGenerator([
            "models/rl/RB_best.pth",
            "models/rl/RB_final.pth",
        ])
        signal = generator.generate_signal(state_features)
    """
    
    def __init__(self,
                 model_paths: List[str],
                 state_dim: int = 6,
                 rl_config: Optional[RLConfig] = None):
        """
        初始化集成信号生成器
        
        Args:
            model_paths: 模型文件路径列表
            state_dim: 状态维度
            rl_config: RL 配置
        """
        self.model_paths = model_paths
        self.state_dim = state_dim
        self.rl_config = rl_config or RLConfig()
        
        # 加载所有 Agent
        self.agents = self._load_agents()
        
        logger.info(f"RL 集成信号生成器初始化: {len(self.agents)} 个模型")
    
    def _load_agents(self) -> List[AgentPPO]:
        """加载所有 Agent"""
        agents = []
        
        for path in self.model_paths:
            if not os.path.exists(path):
                logger.warning(f"模型文件不存在: {path}")
                continue
            
            agent = AgentPPO(state_dim=self.state_dim, rl_config=self.rl_config)
            agent.load(path)
            agents.append(agent)
        
        if not agents:
            logger.warning("没有可用的模型，创建默认 Agent")
            agents.append(AgentPPO(state_dim=self.state_dim, rl_config=self.rl_config))
        
        return agents
    
    def generate_signal(self,
                       state_features: np.ndarray,
                       current_position: float = 0.0) -> Dict[str, Any]:
        """
        生成集成信号
        
        Args:
            state_features: 状态特征向量
            current_position: 当前持仓
        
        Returns:
            信号字典
        """
        # 构建完整状态
        full_state = np.zeros(self.state_dim)
        full_state[:len(state_features)] = state_features
        full_state[len(state_features)] = current_position
        full_state[len(state_features) + 1] = 0.0
        
        # 收集所有 Agent 的输出
        actions = []
        log_probs = []
        values = []
        
        for agent in self.agents:
            action = agent.reason(full_state)
            actions.append(action.action)
            log_probs.append(action.log_prob or 0)
            values.append(action.value or 0)
        
        # 计算集成结果
        mean_action = np.mean(actions)
        std_action = np.std(actions)
        mean_log_prob = np.mean(log_probs)
        mean_value = np.mean(values)
        
        # 计算一致性（标准差越小，一致性越高）
        consistency = 1.0 - min(std_action, 1.0)
        
        # 生成信号
        target_position = mean_action
        position_change = target_position - current_position
        
        signal = {
            'source': 'rl_ensemble',
            'target_position': target_position,
            'current_position': current_position,
            'position_change': position_change,
            'direction': 'LONG' if position_change > 0.1 else ('SHORT' if position_change < -0.1 else 'NEUTRAL'),
            'strength': abs(position_change),
            'confidence': consistency * min(abs(position_change) * 2, 1.0),
            'consistency': consistency,
            'std_action': std_action,
            'n_models': len(self.agents),
            'mean_log_prob': mean_log_prob,
            'mean_value': mean_value,
            'individual_actions': actions,
        }
        
        return signal


def integrate_rl_signal_to_scanner(scanner_result: Dict[str, Any],
                                   rl_signal: Dict[str, Any],
                                   rl_weight: float = 0.3) -> Dict[str, Any]:
    """
    将 RL 信号集成到 Scanner 结果中
    
    Args:
        scanner_result: Scanner 原始结果
        rl_signal: RL 信号
        rl_weight: RL 信号权重 (0-1)
    
    Returns:
        集成后的结果
    """
    # 复制原始结果
    result = scanner_result.copy()
    
    # 获取原始信号
    original_direction = result.get('direction', 'NEUTRAL')
    original_strength = result.get('strength', 0)
    
    # RL 信号
    rl_direction = rl_signal.get('direction', 'NEUTRAL')
    rl_strength = rl_signal.get('strength', 0)
    rl_confidence = rl_signal.get('confidence', 0)
    
    # 方向编码
    direction_map = {'LONG': 1, 'SHORT': -1, 'NEUTRAL': 0}
    original_score = direction_map.get(original_direction, 0) * original_strength
    rl_score = direction_map.get(rl_direction, 0) * rl_strength * rl_confidence
    
    # 加权融合
    combined_score = (1 - rl_weight) * original_score + rl_weight * rl_score
    
    # 解析融合后的方向和强度
    if combined_score > 0.1:
        combined_direction = 'LONG'
    elif combined_score < -0.1:
        combined_direction = 'SHORT'
    else:
        combined_direction = 'NEUTRAL'
    
    combined_strength = abs(combined_score)
    
    # 更新结果
    result['direction'] = combined_direction
    result['strength'] = combined_strength
    result['rl_signal'] = rl_signal
    result['original_direction'] = original_direction
    result['original_strength'] = original_strength
    result['rl_weight'] = rl_weight
    result['combined_score'] = combined_score
    
    # 添加 RL 诊断信息
    if rl_signal.get('source') == 'rl_ensemble':
        result['rl_consistency'] = rl_signal.get('consistency', 0)
        result['rl_n_models'] = rl_signal.get('n_models', 0)
    
    return result
