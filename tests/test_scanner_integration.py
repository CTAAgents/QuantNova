"""
Scanner 集成测试

测试 RL 信号生成器和集成逻辑

版本：v1.0
创建日期：2026-06-17
"""

import numpy as np
import pytest
from typing import Dict, Any

from scripts.trend_scanner.rl.scanner_integration import (
    RLSignalGenerator,
    RLEnsembleSignalGenerator,
    integrate_rl_signal_to_scanner,
)
from scripts.trend_scanner.rl.agent_ppo import AgentPPO
from scripts.trend_scanner.trend_scanner_config import RLConfig


class TestRLSignalGenerator:
    """RLSignalGenerator 测试"""
    
    def test_initialization_without_model(self):
        """测试无模型时的初始化"""
        generator = RLSignalGenerator(
            model_path="nonexistent.pth",
            state_dim=6,
        )
        
        assert generator.state_dim == 6
        assert generator.agent is not None
    
    def test_generate_signal(self):
        """测试信号生成"""
        generator = RLSignalGenerator(
            model_path="nonexistent.pth",
            state_dim=6,
        )
        
        state_features = np.random.randn(4)  # 4 个技术指标
        signal = generator.generate_signal(state_features, current_position=0.0)
        
        assert 'source' in signal
        assert 'target_position' in signal
        assert 'direction' in signal
        assert 'strength' in signal
        assert 'confidence' in signal
        assert signal['source'] == 'rl'
    
    def test_signal_directions(self):
        """测试信号方向"""
        generator = RLSignalGenerator(
            model_path="nonexistent.pth",
            state_dim=6,
        )
        
        state_features = np.random.randn(4)
        
        # 测试不同持仓
        for position in [-1.0, -0.5, 0.0, 0.5, 1.0]:
            signal = generator.generate_signal(state_features, current_position=position)
            assert signal['direction'] in ['LONG', 'SHORT', 'NEUTRAL']
    
    def test_batch_generate_signals(self):
        """测试批量信号生成"""
        generator = RLSignalGenerator(
            model_path="nonexistent.pth",
            state_dim=6,
        )
        
        states = np.random.randn(10, 4)
        positions = np.zeros(10)
        
        signals = generator.batch_generate_signals(states, positions)
        
        assert len(signals) == 10
        for signal in signals:
            assert 'source' in signal


class TestRLEnsembleSignalGenerator:
    """RLEnsembleSignalGenerator 测试"""
    
    def test_initialization_without_models(self):
        """测试无模型时的初始化"""
        generator = RLEnsembleSignalGenerator(
            model_paths=["nonexistent1.pth", "nonexistent2.pth"],
            state_dim=6,
        )
        
        assert len(generator.agents) >= 1  # 至少有一个默认 Agent
    
    def test_generate_signal(self):
        """测试集成信号生成"""
        generator = RLEnsembleSignalGenerator(
            model_paths=["nonexistent.pth"],
            state_dim=6,
        )
        
        state_features = np.random.randn(4)
        signal = generator.generate_signal(state_features, current_position=0.0)
        
        assert signal['source'] == 'rl_ensemble'
        assert 'consistency' in signal
        assert 'n_models' in signal
        assert 'individual_actions' in signal
    
    def test_consistency_calculation(self):
        """测试一致性计算"""
        generator = RLEnsembleSignalGenerator(
            model_paths=["nonexistent1.pth", "nonexistent2.pth"],
            state_dim=6,
        )
        
        state_features = np.random.randn(4)
        signal = generator.generate_signal(state_features, current_position=0.0)
        
        assert 0 <= signal['consistency'] <= 1


class TestIntegrateRLSignal:
    """integrate_rl_signal_to_scanner 测试"""
    
    def test_basic_integration(self):
        """测试基本集成"""
        scanner_result = {
            'direction': 'LONG',
            'strength': 0.8,
            'symbol': 'RB',
        }
        
        rl_signal = {
            'source': 'rl',
            'direction': 'LONG',
            'strength': 0.6,
            'confidence': 0.7,
        }
        
        result = integrate_rl_signal_to_scanner(
            scanner_result, rl_signal, rl_weight=0.3
        )
        
        assert 'rl_signal' in result
        assert 'original_direction' in result
        assert 'rl_weight' in result
        assert 'combined_score' in result
    
    def test_direction_consistency(self):
        """测试方向一致性"""
        # 原始信号和 RL 信号方向一致
        scanner_result = {
            'direction': 'LONG',
            'strength': 0.8,
        }
        
        rl_signal = {
            'source': 'rl',
            'direction': 'LONG',
            'strength': 0.6,
            'confidence': 0.7,
        }
        
        result = integrate_rl_signal_to_scanner(
            scanner_result, rl_signal, rl_weight=0.3
        )
        
        # 方向应该保持一致
        assert result['direction'] == 'LONG'
    
    def test_direction_conflict(self):
        """测试方向冲突"""
        # 原始信号和 RL 信号方向冲突
        scanner_result = {
            'direction': 'LONG',
            'strength': 0.8,
        }
        
        rl_signal = {
            'source': 'rl',
            'direction': 'SHORT',
            'strength': 0.6,
            'confidence': 0.7,
        }
        
        result = integrate_rl_signal_to_scanner(
            scanner_result, rl_signal, rl_weight=0.5
        )
        
        # 应该有冲突信息
        assert 'combined_score' in result
    
    def test_ensemble_integration(self):
        """测试集成信号集成"""
        scanner_result = {
            'direction': 'LONG',
            'strength': 0.8,
        }
        
        rl_signal = {
            'source': 'rl_ensemble',
            'direction': 'LONG',
            'strength': 0.6,
            'confidence': 0.8,
            'consistency': 0.9,
            'n_models': 3,
        }
        
        result = integrate_rl_signal_to_scanner(
            scanner_result, rl_signal, rl_weight=0.3
        )
        
        assert 'rl_consistency' in result
        assert 'rl_n_models' in result
        assert result['rl_n_models'] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
