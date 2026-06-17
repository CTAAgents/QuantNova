"""
TrendScannerConfig 单元测试

测试内容：
1. 默认配置创建
2. JSON 文件加载
3. 配置验证
4. 环境变量覆盖
5. 配置序列化

版本：v1.0
创建日期：2026-06-17
"""

import json
import os
import tempfile
import pytest
from pathlib import Path

from scripts.trend_scanner.trend_scanner_config import (
    TrendScannerConfig,
    DataConfig,
    ScannerConfig,
    ReasonerConfig,
    EvolverConfig,
    RLConfig,
    get_config,
    set_config,
    reset_config,
)


class TestDataConfig:
    """DataConfig 测试"""
    
    def test_default_values(self):
        """测试默认值"""
        config = DataConfig()
        
        assert config.primary_source == "tqsdk"
        assert "duckdb" in config.fallback_sources
        assert "tdx" in config.fallback_sources
        assert config.cache_dir == "data/cache"
        assert config.db_path == "data/market.db"
    
    def test_routing_priorities(self):
        """测试数据路由优先级"""
        config = DataConfig()
        
        assert "kline" in config.routing_priorities
        assert config.routing_priorities["kline"][0] == "duckdb"
        assert config.routing_priorities["quote"][0] == "duckdb"
    
    def test_staleness_threshold(self):
        """测试数据时效阈值"""
        config = DataConfig()
        
        assert config.staleness_threshold["kline"] == 4
        assert config.staleness_threshold["quote"] == 0.5
        assert config.staleness_threshold["seasonality"] == 168


class TestScannerConfig:
    """ScannerConfig 测试"""
    
    def test_default_values(self):
        """测试默认值"""
        config = ScannerConfig()
        
        assert config.enabled is True
        assert "SHFE.rb" in config.symbols
        assert "DCE.jm" in config.symbols
        assert len(config.schedule) == 3
    
    def test_dimension_weights(self):
        """测试维度权重"""
        config = ScannerConfig()
        
        assert abs(sum(config.dimension_weights.values()) - 1.0) < 0.01
        assert config.dimension_weights["trend"] == 0.30
        assert config.dimension_weights["momentum"] == 0.25
    
    def test_signal_thresholds(self):
        """测试信号阈值"""
        config = ScannerConfig()
        
        assert config.signal_thresholds["long"] == 0.3
        assert config.signal_thresholds["short"] == -0.3


class TestReasonerConfig:
    """ReasonerConfig 测试"""
    
    def test_default_values(self):
        """测试默认值"""
        config = ReasonerConfig()
        
        assert config.llm_type == "workbuddy"
        assert config.llm_model == "mimo-v2.5-pro"
        assert config.output_level == "standard"
        assert config.use_knowledge_anchors is True


class TestRLConfig:
    """RLConfig 测试"""
    
    def test_default_values(self):
        """测试默认值"""
        config = RLConfig()
        
        assert config.enabled is False
        assert config.algorithm == "ppo"
        assert config.net_dims == [128, 128]
        assert config.gamma == 0.99
        assert config.learning_rate == 2e-4
    
    def test_ppo_params(self):
        """测试 PPO 参数"""
        config = RLConfig()
        
        assert config.ratio_clip == 0.2
        assert config.entropy_weight == 0.001
        assert config.lambda_gae == 0.95
    
    def test_sac_params(self):
        """测试 SAC 参数"""
        config = RLConfig()
        
        assert config.alpha_init == 0.2
        assert config.tau == 0.005


class TestTrendScannerConfig:
    """TrendScannerConfig 测试"""
    
    def test_default_creation(self):
        """测试默认配置创建"""
        config = TrendScannerConfig()
        
        assert config.version == "1.0.0"
        assert isinstance(config.data, DataConfig)
        assert isinstance(config.scanner, ScannerConfig)
        assert isinstance(config.reasoner, ReasonerConfig)
        assert isinstance(config.evolver, EvolverConfig)
        assert isinstance(config.rl, RLConfig)
    
    def test_from_json(self):
        """测试从 JSON 文件加载"""
        config_data = {
            "version": "2.0.0",
            "scanner": {
                "enabled": False,
                "symbols": ["RB", "I"]
            },
            "reasoner": {
                "llm_type": "custom"
            },
            "llm": {
                "model": "gpt-4"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = TrendScannerConfig.from_json(temp_path)
            
            assert config.version == "2.0.0"
            assert config.scanner.enabled is False
            assert config.scanner.symbols == ["RB", "I"]
            assert config.reasoner.llm_type == "custom"
            assert config.reasoner.llm_model == "gpt-4"
        finally:
            os.unlink(temp_path)
    
    def test_from_json_with_data_routing(self):
        """测试从 JSON 加载数据路由配置"""
        config_data = {
            "data_routing": {
                "db_dir": "custom_data",
                "priorities": {
                    "kline": ["tqsdk", "duckdb"]
                },
                "staleness_threshold": {
                    "kline": 8
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = TrendScannerConfig.from_json(temp_path)
            
            assert config.data.routing_priorities["kline"] == ["tqsdk", "duckdb"]
            assert config.data.staleness_threshold["kline"] == 8
        finally:
            os.unlink(temp_path)
    
    def test_to_json(self):
        """测试保存到 JSON 文件"""
        config = TrendScannerConfig()
        config.version = "3.0.0"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            config.to_json(temp_path)
            
            with open(temp_path, 'r') as f:
                saved_data = json.load(f)
            
            assert saved_data["version"] == "3.0.0"
            assert "scanner" in saved_data
            assert "reasoner" in saved_data
            assert "rl" in saved_data
        finally:
            os.unlink(temp_path)
    
    def test_to_dict(self):
        """测试转换为字典"""
        config = TrendScannerConfig()
        data = config.to_dict()
        
        assert isinstance(data, dict)
        assert "version" in data
        assert "scanner" in data
        assert "reasoner" in data
    
    def test_validate_valid_config(self):
        """测试有效配置验证"""
        config = TrendScannerConfig()
        errors = config.validate()
        
        assert len(errors) == 0
    
    def test_validate_invalid_data_source(self):
        """测试无效数据源验证"""
        config = TrendScannerConfig()
        config.data.primary_source = "invalid_source"
        
        errors = config.validate()
        
        assert any("无效的主数据源" in e for e in errors)
    
    def test_validate_invalid_dimension_weights(self):
        """测试无效维度权重验证"""
        config = TrendScannerConfig()
        config.scanner.dimension_weights = {
            "trend": 0.5,
            "momentum": 0.3
        }
        
        errors = config.validate()
        
        assert any("维度权重之和" in e for e in errors)
    
    def test_validate_invalid_output_level(self):
        """测试无效输出级别验证"""
        config = TrendScannerConfig()
        config.reasoner.output_level = "invalid"
        
        errors = config.validate()
        
        assert any("无效的输出级别" in e for e in errors)
    
    def test_validate_invalid_rl_algorithm(self):
        """测试无效 RL 算法验证"""
        config = TrendScannerConfig()
        config.rl.algorithm = "invalid"
        
        errors = config.validate()
        
        assert any("无效的 RL 算法" in e for e in errors)
    
    def test_validate_invalid_gamma(self):
        """测试无效 gamma 验证"""
        config = TrendScannerConfig()
        config.rl.gamma = 1.5
        
        errors = config.validate()
        
        assert any("gamma" in e for e in errors)
    
    def test_get_summary(self):
        """测试获取配置摘要"""
        config = TrendScannerConfig()
        summary = config.get_summary()
        
        assert "TrendScannerConfig" in summary
        assert "tqsdk" in summary
        assert "mimo-v2.5-pro" in summary
        assert "standard" in summary
    
    def test_get_summary_with_rl(self):
        """测试启用 RL 时的配置摘要"""
        config = TrendScannerConfig()
        config.rl.enabled = True
        
        summary = config.get_summary()
        
        assert "启用" in summary
        assert "ppo" in summary


class TestEnvOverrides:
    """环境变量覆盖测试"""
    
    def test_env_override_tq_user(self):
        """测试 TqSdk 用户名环境变量覆盖"""
        os.environ['TQ_USER'] = 'test_user'
        
        try:
            config = TrendScannerConfig()
            config._apply_env_overrides()
            
            assert config.data.tq_user == 'test_user'
        finally:
            del os.environ['TQ_USER']
    
    def test_env_override_tq_password(self):
        """测试 TqSdk 密码环境变量覆盖"""
        os.environ['TQ_PASSWORD'] = 'test_password'
        
        try:
            config = TrendScannerConfig()
            config._apply_env_overrides()
            
            assert config.data.tq_password == 'test_password'
        finally:
            del os.environ['TQ_PASSWORD']
    
    def test_env_override_llm_api_key(self):
        """测试 LLM API Key 环境变量覆盖"""
        os.environ['LLM_API_KEY'] = 'test_api_key'
        
        try:
            config = TrendScannerConfig()
            config._apply_env_overrides()
            
            assert config.reasoner.llm_api_key == 'test_api_key'
        finally:
            del os.environ['LLM_API_KEY']


class TestGlobalConfig:
    """全局配置测试"""
    
    def setup_method(self):
        """每个测试前重置全局配置"""
        reset_config()
    
    def teardown_method(self):
        """每个测试后重置全局配置"""
        reset_config()
    
    def test_get_config_default(self):
        """测试获取默认全局配置"""
        config = get_config()
        
        assert isinstance(config, TrendScannerConfig)
    
    def test_set_config(self):
        """测试设置全局配置"""
        custom_config = TrendScannerConfig()
        custom_config.version = "custom"
        
        set_config(custom_config)
        retrieved = get_config()
        
        assert retrieved.version == "custom"
    
    def test_reset_config(self):
        """测试重置全局配置"""
        custom_config = TrendScannerConfig()
        custom_config.version = "custom"
        
        set_config(custom_config)
        reset_config()
        
        # 重置后应该返回新的默认配置
        new_config = get_config()
        assert new_config.version == "1.0.0"
    
    def test_get_config_from_env(self):
        """测试从环境变量指定的路径加载配置"""
        config_data = {"version": "env_test"}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_path = f.name
        
        os.environ['TREND_SCANNER_CONFIG'] = temp_path
        
        try:
            reset_config()
            config = get_config()
            
            assert config.version == "env_test"
        finally:
            del os.environ['TREND_SCANNER_CONFIG']
            os.unlink(temp_path)


class TestRoundTrip:
    """往返测试（序列化/反序列化）"""
    
    def test_json_roundtrip(self):
        """测试 JSON 序列化往返"""
        original = TrendScannerConfig()
        original.version = "roundtrip_test"
        original.scanner.symbols = ["RB", "I"]
        original.rl.enabled = True
        original.rl.net_dims = [256, 256]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            original.to_json(temp_path)
            loaded = TrendScannerConfig.from_json(temp_path)
            
            assert loaded.version == "roundtrip_test"
            assert loaded.scanner.symbols == ["RB", "I"]
            assert loaded.rl.enabled is True
            assert loaded.rl.net_dims == [256, 256]
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
