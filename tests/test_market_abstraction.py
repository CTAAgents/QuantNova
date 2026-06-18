"""
市场抽象层测试

测试 MarketProvider 和 BaseRiskManager 抽象基类
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "scripts"))


class TestMarketProvider:
    """MarketProvider 抽象基类测试"""
    
    def test_cannot_instantiate_directly(self):
        """测试不能直接实例化抽象基类"""
        from core.market_provider import MarketProvider
        
        with pytest.raises(TypeError):
            MarketProvider({})
    
    def test_implemented_class_can_instantiate(self):
        """测试实现类可以实例化"""
        from core.market_provider import MarketProvider, MarketType
        
        class TestProvider(MarketProvider):
            def _get_market_type(self):
                return MarketType.FUTURES
            
            def get_kline(self, symbol, timeframe="daily", count=100):
                return pd.DataFrame()
            
            def get_realtime_quote(self, symbol):
                return {}
            
            def get_symbols(self):
                return ["RB", "I"]
            
            def get_fundamental(self, symbol):
                return {}
        
        provider = TestProvider({})
        assert provider is not None
        assert provider.market_type == MarketType.FUTURES
    
    def test_validate_symbol(self):
        """测试品种代码验证"""
        from core.market_provider import MarketProvider, MarketType
        
        class TestProvider(MarketProvider):
            def _get_market_type(self):
                return MarketType.FUTURES
            
            def get_kline(self, symbol, timeframe="daily", count=100):
                return pd.DataFrame()
            
            def get_realtime_quote(self, symbol):
                return {}
            
            def get_symbols(self):
                return ["RB", "I", "J"]
            
            def get_fundamental(self, symbol):
                return {}
        
        provider = TestProvider({})
        
        # 有效品种
        assert provider.validate_symbol("RB") is True
        assert provider.validate_symbol("I") is True
        
        # 无效品种
        assert provider.validate_symbol("XXX") is False
    
    def test_market_type_enum(self):
        """测试市场类型枚举"""
        from core.market_provider import MarketType
        
        assert MarketType.FUTURES.value == "futures"
        assert MarketType.SECURITIES.value == "securities"


class TestBaseRiskManager:
    """BaseRiskManager 抽象基类测试"""
    
    def test_cannot_instantiate_directly(self):
        """测试不能直接实例化抽象基类"""
        from core.base_risk_manager import BaseRiskManager
        
        with pytest.raises(TypeError):
            BaseRiskManager({})
    
    def test_implemented_class_can_instantiate(self):
        """测试实现类可以实例化"""
        from core.base_risk_manager import BaseRiskManager, RiskMetrics, RiskLevel
        
        class TestRiskManager(BaseRiskManager):
            def calculate_position_size(self, signal, capital, current_price):
                return capital * 0.1 / current_price
            
            def calculate_stop_loss(self, entry_price, signal):
                return entry_price * 0.95
            
            def calculate_take_profit(self, entry_price, signal):
                return entry_price * 1.1
            
            def check_stop_loss(self, position, current_price):
                return current_price <= position.get("stop_loss", 0)
            
            def check_take_profit(self, position, current_price):
                return current_price >= position.get("take_profit", float("inf"))
            
            def get_risk_metrics(self, position, current_price):
                return RiskMetrics(
                    position_size=100,
                    stop_loss_price=95,
                    take_profit_price=110,
                    risk_reward_ratio=2.0,
                    max_drawdown=0.1,
                    risk_level=RiskLevel.LOW,
                    warnings=[],
                )
        
        manager = TestRiskManager({})
        assert manager is not None
    
    def test_validate_trade(self):
        """测试交易验证"""
        from core.base_risk_manager import BaseRiskManager, RiskMetrics, RiskLevel
        
        class TestRiskManager(BaseRiskManager):
            def calculate_position_size(self, signal, capital, current_price):
                return capital * 0.1 / current_price
            
            def calculate_stop_loss(self, entry_price, signal):
                return entry_price * 0.95
            
            def calculate_take_profit(self, entry_price, signal):
                return entry_price * 1.1
            
            def check_stop_loss(self, position, current_price):
                return current_price <= position.get("stop_loss", 0)
            
            def check_take_profit(self, position, current_price):
                return current_price >= position.get("take_profit", float("inf"))
            
            def get_risk_metrics(self, position, current_price):
                return RiskMetrics(
                    position_size=100,
                    stop_loss_price=95,
                    take_profit_price=110,
                    risk_reward_ratio=2.0,
                    max_drawdown=0.1,
                    risk_level=RiskLevel.LOW,
                    warnings=[],
                )
        
        manager = TestRiskManager({})
        
        # 有效交易
        valid, msg = manager.validate_trade(0.5, 100000, 3500)
        assert valid is True
        
        # 无效信号
        valid, msg = manager.validate_trade(1.5, 100000, 3500)
        assert valid is False
        
        # 无效资金
        valid, msg = manager.validate_trade(0.5, 0, 3500)
        assert valid is False
        
        # 无效价格
        valid, msg = manager.validate_trade(0.5, 100000, -100)
        assert valid is False


class TestRiskMetrics:
    """RiskMetrics 数据类测试"""
    
    def test_creation(self):
        """测试创建"""
        from core.base_risk_manager import RiskMetrics, RiskLevel
        
        metrics = RiskMetrics(
            position_size=100,
            stop_loss_price=95,
            take_profit_price=110,
            risk_reward_ratio=2.0,
            max_drawdown=0.1,
            risk_level=RiskLevel.LOW,
            warnings=["测试警告"],
        )
        
        assert metrics.position_size == 100
        assert metrics.risk_level == RiskLevel.LOW
        assert len(metrics.warnings) == 1


class TestIntegration:
    """集成测试"""
    
    def test_provider_and_risk_manager_together(self):
        """测试 Provider 和 RiskManager 一起使用"""
        from core.market_provider import MarketProvider, MarketType
        from core.base_risk_manager import BaseRiskManager, RiskMetrics, RiskLevel
        
        class TestProvider(MarketProvider):
            def _get_market_type(self):
                return MarketType.FUTURES
            
            def get_kline(self, symbol, timeframe="daily", count=100):
                return pd.DataFrame({"close": [3500]})
            
            def get_realtime_quote(self, symbol):
                return {"price": 3500}
            
            def get_symbols(self):
                return ["RB"]
            
            def get_fundamental(self, symbol):
                return {}
        
        class TestRiskManager(BaseRiskManager):
            def calculate_position_size(self, signal, capital, current_price):
                return capital * 0.1 / current_price
            
            def calculate_stop_loss(self, entry_price, signal):
                return entry_price * 0.95
            
            def calculate_take_profit(self, entry_price, signal):
                return entry_price * 1.1
            
            def check_stop_loss(self, position, current_price):
                return current_price <= position.get("stop_loss", 0)
            
            def check_take_profit(self, position, current_price):
                return current_price >= position.get("take_profit", float("inf"))
            
            def get_risk_metrics(self, position, current_price):
                return RiskMetrics(
                    position_size=100,
                    stop_loss_price=95,
                    take_profit_price=110,
                    risk_reward_ratio=2.0,
                    max_drawdown=0.1,
                    risk_level=RiskLevel.LOW,
                    warnings=[],
                )
        
        # 使用
        provider = TestProvider({})
        risk_manager = TestRiskManager({})
        
        # 获取数据
        kline = provider.get_kline("RB")
        quote = provider.get_realtime_quote("RB")
        
        # 计算仓位
        position_size = risk_manager.calculate_position_size(0.5, 100000, 3500)
        
        # 计算止损止盈
        stop_loss = risk_manager.calculate_stop_loss(3500, 0.5)
        take_profit = risk_manager.calculate_take_profit(3500, 0.5)
        
        assert position_size > 0
        assert stop_loss < 3500
        assert take_profit > 3500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
