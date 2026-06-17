"""
Walk-Forward RL 验证器单元测试

测试内容：
1. RLWalkForwardValidator 初始化
2. 验证流程
3. 诊断建议生成
4. 结果保存

版本：v1.0
创建日期：2026-06-17
"""

import json
import numpy as np
import pytest
import tempfile
from pathlib import Path

from scripts.trend_scanner.rl.walk_forward_rl import (
    RLWalkForwardValidator,
    RLWindowResult,
    RLWalkForwardResult,
    walk_forward_validate_rl,
)
from scripts.trend_scanner.rl.agent_ppo import AgentPPO
from scripts.trend_scanner.trend_scanner_config import RLConfig
from scripts.trend_scanner.walk_forward_validator import WalkForwardConfig


class TestRLWalkForwardValidator:
    """RLWalkForwardValidator 测试"""
    
    def test_initialization(self):
        """测试初始化"""
        validator = RLWalkForwardValidator()
        
        assert validator.config.optimization_window == 30
        assert validator.config.test_window == 7
        assert validator.rl_config.algorithm == "ppo"
    
    def test_initialization_with_config(self):
        """测试带配置的初始化"""
        wf_config = WalkForwardConfig(
            optimization_window=20,
            test_window=5,
            step_size=5,
        )
        rl_config = RLConfig(
            net_dims=[64, 32],
            gamma=0.95,
        )
        
        validator = RLWalkForwardValidator(config=wf_config, rl_config=rl_config)
        
        assert validator.config.optimization_window == 20
        assert validator.config.test_window == 5
        assert validator.rl_config.net_dims == [64, 32]
    
    def test_validate_short_data(self):
        """测试数据不足的情况"""
        # 数据太短
        data = np.random.randn(10, 5)
        
        validator = RLWalkForwardValidator()
        result = validator.validate(data, state_dim=5)
        
        assert result.total_windows == 0
        assert result.pass_rate == 0.0
        assert len(result.recommendations) > 0
    
    def test_validate_basic(self):
        """测试基本验证流程"""
        # 生成足够长的数据
        data = np.random.randn(100, 5)
        
        # 使用较小的窗口
        wf_config = WalkForwardConfig(
            optimization_window=30,
            test_window=10,
            step_size=10,
        )
        
        validator = RLWalkForwardValidator(config=wf_config)
        
        # 使用较少的训练步数以加快测试
        result = validator.validate(
            data, 
            state_dim=7,  # 5 + 2 (position + pnl)
            train_steps_per_window=100,
        )
        
        assert result.total_windows > 0
        assert 0 <= result.pass_rate <= 1
        assert len(result.window_results) > 0


class TestRLWindowResult:
    """RLWindowResult 测试"""
    
    def test_creation(self):
        """测试创建"""
        result = RLWindowResult(
            window_idx=0,
            is_start=None,
            is_end=None,
            oos_start=None,
            oos_end=None,
            is_reward=1.0,
            is_sharpe=1.5,
            is_win_rate=0.6,
            is_max_drawdown=0.1,
            is_trades=10,
            oos_reward=0.8,
            oos_sharpe=1.2,
            oos_win_rate=0.55,
            oos_max_drawdown=0.15,
            oos_trades=8,
            reward_ratio=0.8,
            sharpe_ratio=0.8,
            passed=True,
            diagnosis={'oos_reward': 'PASS'},
        )
        
        assert result.window_idx == 0
        assert result.is_reward == 1.0
        assert result.oos_reward == 0.8
        assert result.passed is True


class TestRLWalkForwardResult:
    """RLWalkForwardResult 测试"""
    
    def test_creation(self):
        """测试创建"""
        result = RLWalkForwardResult(
            total_windows=5,
            passed_windows=3,
            pass_rate=0.6,
            avg_oos_reward=0.5,
            avg_oos_sharpe=1.0,
            avg_oos_win_rate=0.55,
            max_oos_drawdown=0.2,
            avg_reward_ratio=0.7,
            avg_sharpe_ratio=0.8,
            window_results=[],
            recommendations=["测试建议"],
        )
        
        assert result.total_windows == 5
        assert result.pass_rate == 0.6
        assert len(result.recommendations) == 1


class TestWalkForwardValidateRL:
    """walk_forward_validate_rl 便捷函数测试"""
    
    def test_basic_validation(self):
        """测试基本验证"""
        data = np.random.randn(80, 5)
        
        wf_config = WalkForwardConfig(
            optimization_window=20,
            test_window=10,
            step_size=10,
        )
        
        result = walk_forward_validate_rl(
            data=data,
            state_dim=7,
            wf_config=wf_config,
            train_steps_per_window=50,
        )
        
        assert isinstance(result, RLWalkForwardResult)
        assert result.total_windows > 0


class TestDiagnosis:
    """诊断功能测试"""
    
    def test_reward_ratio_diagnosis(self):
        """测试 Reward Ratio 诊断"""
        validator = RLWalkForwardValidator()
        
        # 模拟 IS/OOS 指标
        is_metrics = {'mean_reward': 1.0, 'sharpe': 1.5, 'win_rate': 0.6, 'max_drawdown': 0.1, 'trades': 10}
        oos_metrics = {'mean_reward': 0.3, 'sharpe': 0.5, 'win_rate': 0.5, 'max_drawdown': 0.15, 'trades': 8}
        
        reward_ratio = 0.3
        sharpe_ratio = 0.33
        
        passed, diagnosis = validator._check_pass_criteria(
            is_metrics, oos_metrics, reward_ratio, sharpe_ratio
        )
        
        # 应该失败，因为 reward_ratio < 0.5
        assert passed is False
        assert 'reward_ratio' in diagnosis
        assert 'FAIL' in diagnosis['reward_ratio']
    
    def test_pass_criteria(self):
        """测试通过标准"""
        validator = RLWalkForwardValidator()
        
        # 模拟良好的 IS/OOS 指标
        is_metrics = {'mean_reward': 1.0, 'sharpe': 1.5, 'win_rate': 0.6, 'max_drawdown': 0.1, 'trades': 10}
        oos_metrics = {'mean_reward': 0.8, 'sharpe': 1.2, 'win_rate': 0.55, 'max_drawdown': 0.12, 'trades': 8}
        
        reward_ratio = 0.8
        sharpe_ratio = 0.8
        
        passed, diagnosis = validator._check_pass_criteria(
            is_metrics, oos_metrics, reward_ratio, sharpe_ratio
        )
        
        assert passed is True
        assert all('PASS' in v for v in diagnosis.values())
    
    def test_recommendations_generation(self):
        """测试建议生成"""
        validator = RLWalkForwardValidator()
        
        # 模拟失败的结果
        result = RLWalkForwardResult(
            total_windows=5,
            passed_windows=1,
            pass_rate=0.2,
            avg_oos_reward=-0.1,
            avg_oos_sharpe=0.3,
            avg_oos_win_rate=0.4,
            max_oos_drawdown=0.25,
            avg_reward_ratio=0.3,
            avg_sharpe_ratio=0.4,
            window_results=[],
            recommendations=[],
        )
        
        recommendations = validator._generate_recommendations(result)
        
        # 应该有多个建议
        assert len(recommendations) > 0
        
        # 检查是否包含关键建议
        has_pass_rate = any("通过率" in r for r in recommendations)
        has_reward_ratio = any("IS/OOS 一致性" in r for r in recommendations)
        has_drawdown = any("回撤" in r for r in recommendations)
        
        assert has_pass_rate
        assert has_reward_ratio
        assert has_drawdown


class TestSaveResult:
    """结果保存测试"""
    
    def test_save_result(self, tmp_path):
        """测试保存结果"""
        validator = RLWalkForwardValidator()
        
        result = RLWalkForwardResult(
            total_windows=3,
            passed_windows=2,
            pass_rate=0.67,
            avg_oos_reward=0.5,
            avg_oos_sharpe=1.0,
            avg_oos_win_rate=0.55,
            max_oos_drawdown=0.15,
            avg_reward_ratio=0.7,
            avg_sharpe_ratio=0.8,
            window_results=[
                RLWindowResult(
                    window_idx=0,
                    is_start=None,
                    is_end=None,
                    oos_start=None,
                    oos_end=None,
                    is_reward=1.0,
                    is_sharpe=1.5,
                    is_win_rate=0.6,
                    is_max_drawdown=0.1,
                    is_trades=10,
                    oos_reward=0.8,
                    oos_sharpe=1.2,
                    oos_win_rate=0.55,
                    oos_max_drawdown=0.12,
                    oos_trades=8,
                    reward_ratio=0.8,
                    sharpe_ratio=0.8,
                    passed=True,
                    diagnosis={'oos_reward': 'PASS'},
                ),
            ],
            recommendations=["验证通过"],
        )
        
        filepath = str(tmp_path / "rl_wf_result.json")
        validator.save_result(result, filepath)
        
        # 验证文件存在
        assert Path(filepath).exists()
        
        # 验证文件内容
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        assert data['total_windows'] == 3
        assert data['passed_windows'] == 2
        assert len(data['windows']) == 1
        assert len(data['recommendations']) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
