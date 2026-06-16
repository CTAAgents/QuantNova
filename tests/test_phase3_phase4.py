"""
Phase 3 & 4 测试：贝叶斯参数优化器 + 种子因子池
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))


def generate_mock_data(n_symbols: int = 20, days: int = 120) -> dict:
    """生成模拟数据"""
    symbols = [f'TEST{i:02d}' for i in range(n_symbols)]
    dates = pd.date_range(end=pd.Timestamp('2026-06-15'), periods=days, freq='B')
    data = {}
    for i, sym in enumerate(symbols):
        np.random.seed(42 + i)
        prices = 100 * np.exp(np.cumsum(np.random.normal(0.0005, 0.02, days)))
        data[sym] = pd.DataFrame({
            'date': dates,
            'open': prices * (1 + np.random.uniform(-0.01, 0.01, days)),
            'high': prices * 1.01,
            'low': prices * 0.99,
            'close': prices,
            'volume': np.random.randint(10000, 100000, days).astype(float),
            'open_interest': np.random.randint(50000, 500000, days).astype(float),
        })
    return data


# ============================================================
# Phase 3: FactorParamOptimizer 测试
# ============================================================

class TestFactorParamOptimizer:
    """FactorParamOptimizer 测试"""

    def setup_method(self):
        from trend_scanner.factor_param_optimizer import FactorParamOptimizer, ParamSpec
        self.optimizer = FactorParamOptimizer(metric='icir')
        self.mock_data = generate_mock_data()
        self.ParamSpec = ParamSpec

    def test_optimize_momentum(self):
        """测试优化动量因子参数"""
        from trend_scanner.factor_param_optimizer import parametric_momentum, PREDEFINED_SPACES

        result = self.optimizer.optimize(
            factor_name='momentum',
            factor_fn=parametric_momentum,
            param_space=PREDEFINED_SPACES['momentum'],
            kline_data=self.mock_data,
            n_trials=10,
        )

        assert result.factor_name == 'momentum'
        assert result.n_trials == 10
        assert 'window' in result.best_params
        assert result.best_score >= 0

    def test_optimize_rsi(self):
        """测试优化 RSI 因子参数"""
        from trend_scanner.factor_param_optimizer import parametric_rsi, PREDEFINED_SPACES

        result = self.optimizer.optimize(
            factor_name='rsi',
            factor_fn=parametric_rsi,
            param_space=PREDEFINED_SPACES['rsi'],
            kline_data=self.mock_data,
            n_trials=10,
        )

        assert result.factor_name == 'rsi'
        assert 'period' in result.best_params

    def test_predefined_space(self):
        """测试预定义参数空间优化"""
        from trend_scanner.factor_param_optimizer import parametric_momentum

        result = self.optimizer.optimize_with_predefined_space(
            factor_name='momentum',
            factor_fn=parametric_momentum,
            space_name='momentum',
            kline_data=self.mock_data,
            n_trials=10,
        )

        assert result.best_params is not None

    def test_custom_param_space(self):
        """测试自定义参数空间"""
        from trend_scanner.factor_param_optimizer import parametric_momentum

        custom_space = [
            self.ParamSpec('window', 'int', low=10, high=30, step=5),
        ]

        result = self.optimizer.optimize(
            factor_name='custom_momentum',
            factor_fn=parametric_momentum,
            param_space=custom_space,
            kline_data=self.mock_data,
            n_trials=10,
        )

        assert 10 <= result.best_params['window'] <= 30

    def test_result_serialization(self):
        """测试结果序列化"""
        from trend_scanner.factor_param_optimizer import parametric_momentum, PREDEFINED_SPACES

        result = self.optimizer.optimize(
            factor_name='momentum',
            factor_fn=parametric_momentum,
            param_space=PREDEFINED_SPACES['momentum'],
            kline_data=self.mock_data,
            n_trials=5,
        )

        d = result.to_dict()
        assert 'factor_name' in d
        assert 'best_params' in d
        assert 'best_score' in d

    def test_generate_optimized_code(self):
        """测试生成优化后的代码"""
        template = '''def factor(df):
    window = {window}
    return df['close'].pct_change(window).fillna(0)
'''
        optimized = self.optimizer.generate_optimized_factor_code(
            template, {'window': 30}
        )
        assert '30' in optimized
        assert '{window}' not in optimized


# ============================================================
# Phase 4: SeedFactorPool 测试
# ============================================================

class TestSeedFactorPool:
    """SeedFactorPool 测试"""

    def setup_method(self):
        from trend_scanner.seed_factor_pool import SeedFactorPool
        self.pool = SeedFactorPool(pool_path='data/test_seed_factors.json')

    def teardown_method(self):
        if os.path.exists('data/test_seed_factors.json'):
            os.remove('data/test_seed_factors.json')

    def test_add_seed(self):
        """测试添加种子因子"""
        name = self.pool.add_seed(
            name='test_factor',
            code='def factor(df): return df["close"].pct_change(5)',
            logic='5日动量',
            economic_rationale='趋势跟踪',
            source='test',
            category='momentum',
        )
        assert name == 'test_factor'
        assert len(self.pool.pool) == 1

    def test_get_pending_seeds(self):
        """测试获取待验证种子"""
        self.pool.add_seed('f1', 'def factor(df): pass', 'l1', 'r1', 'test')
        self.pool.add_seed('f2', 'def factor(df): pass', 'l2', 'r2', 'test')

        pending = self.pool.get_pending_seeds()
        assert len(pending) == 2

    def test_update_status(self):
        """测试更新状态"""
        self.pool.add_seed('f1', 'def factor(df): pass', 'l1', 'r1', 'test')
        self.pool.update_status('f1', 'validated', {'icir': 1.5})

        validated = self.pool.get_validated_seeds()
        assert len(validated) == 1
        assert validated[0].evaluation.get('icir') == 1.5

    def test_remove_seed(self):
        """测试移除种子"""
        self.pool.add_seed('f1', 'def factor(df): pass', 'l1', 'r1', 'test')
        result = self.pool.remove_seed('f1')
        assert result is True
        assert len(self.pool.pool) == 0

    def test_get_summary(self):
        """测试获取摘要"""
        self.pool.add_seed('f1', 'def factor(df): pass', 'l1', 'r1', 'test', 'momentum')
        self.pool.add_seed('f2', 'def factor(df): pass', 'l2', 'r2', 'test', 'volatility')

        summary = self.pool.get_summary()
        assert summary['total'] == 2
        assert summary['categories']['momentum'] == 1
        assert summary['categories']['volatility'] == 1

    def test_classify_factor(self):
        """测试因子分类"""
        from trend_scanner.seed_factor_pool import SeedFactorPool
        pool = SeedFactorPool()

        assert pool._classify_factor('动量因子') == 'momentum'
        assert pool._classify_factor('波动率因子') == 'volatility'
        assert pool._classify_factor('成交量因子') == 'volume'
        assert pool._classify_factor('未知因子') == 'composite'

    def test_preset_seeds(self):
        """测试预置种子因子"""
        from trend_scanner.seed_factor_pool import init_preset_seeds

        count = init_preset_seeds(self.pool)
        assert count == 5
        assert len(self.pool.pool) == 5

        # 检查所有预置种子都有有效的代码
        for seed in self.pool.pool:
            assert 'def factor' in seed.code
            assert seed.logic
            assert seed.economic_rationale

    def test_export_to_knowledge_base(self):
        """测试导出到知识库"""
        self.pool.add_seed('f1', 'def factor(df): pass', 'l1', 'r1', 'test')
        self.pool.update_status('f1', 'validated')

        exported = self.pool.export_to_knowledge_base('data/test_factor_knowledge.json')
        assert exported == 1

        # 清理
        if os.path.exists('data/test_factor_knowledge.json'):
            os.remove('data/test_factor_knowledge.json')

    def test_persistence(self):
        """测试持久化"""
        from trend_scanner.seed_factor_pool import SeedFactorPool

        self.pool.add_seed('f1', 'def factor(df): pass', 'l1', 'r1', 'test')

        # 重新加载
        pool2 = SeedFactorPool(pool_path='data/test_seed_factors.json')
        assert len(pool2.pool) == 1
        assert pool2.pool[0].name == 'f1'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
