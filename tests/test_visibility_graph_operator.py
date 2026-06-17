"""
可见图算子注入因子生成器测试模块

测试 VisibilityGraphOperator 和扩展的 FactorGenerator。
覆盖：
1. 算子注册和描述
2. Prompt 生成
3. 示例因子代码
4. 边界条件

创建日期：2026-06-17
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
import numpy as np
import pandas as pd
from scripts.trend_scanner.visibility_graph_operator import (
    VisibilityGraphOperator,
    get_visibility_operator_descriptions,
    get_visibility_example_factors
)


class TestVisibilityGraphOperator:
    """测试可见图算子管理器"""
    
    def test_operator_initialization(self):
        """测试算子初始化"""
        operator = VisibilityGraphOperator()
        assert 'backward_visibility' in operator.operators
        assert 'horizontal_visibility' in operator.operators
        assert 'visibility_matrix' in operator.operators
        assert 'visibility_aggregate_mean' in operator.operators
        assert 'visibility_aggregate_ratio' in operator.operators
    
    def test_operator_count(self):
        """测试算子数量"""
        operator = VisibilityGraphOperator()
        assert len(operator.operators) == 5
    
    def test_get_operator_descriptions(self):
        """测试获取算子描述"""
        operator = VisibilityGraphOperator()
        descriptions = operator.get_operator_descriptions()
        
        assert isinstance(descriptions, str)
        assert 'backward_visibility' in descriptions
        assert 'horizontal_visibility' in descriptions
        assert 'visibility_matrix' in descriptions
        assert 'visibility_aggregate_mean' in descriptions
        assert 'visibility_aggregate_ratio' in descriptions
    
    def test_get_example_factors(self):
        """测试获取示例因子"""
        operator = VisibilityGraphOperator()
        examples = operator.get_example_factors()
        
        assert isinstance(examples, list)
        assert len(examples) > 0
        
        # 检查示例因子代码
        for example in examples:
            assert isinstance(example, str)
            assert 'def factor' in example
    
    def test_backward_visibility(self):
        """测试向后可见性算子"""
        operator = VisibilityGraphOperator()
        
        # 创建测试数据
        prices = np.array([100, 101, 102, 103, 104, 105])
        
        result = operator._backward_visibility(prices, window=5)
        
        assert isinstance(result, np.ndarray)
        assert len(result) == len(prices)
    
    def test_horizontal_visibility(self):
        """测试水平可见性算子"""
        operator = VisibilityGraphOperator()
        
        # 创建测试数据
        prices = np.array([100, 101, 102, 103, 104, 105])
        
        result = operator._horizontal_visibility(prices, window=5)
        
        assert isinstance(result, np.ndarray)
        assert len(result) == len(prices)
    
    def test_visibility_matrix(self):
        """测试可见性矩阵算子"""
        operator = VisibilityGraphOperator()
        
        # 创建测试数据
        prices = np.array([100, 101, 102, 103, 104, 105])
        
        result = operator._visibility_matrix(prices, window=5)
        
        assert isinstance(result, np.ndarray)
        assert len(result) == len(prices)
    
    def test_aggregate_mean(self):
        """测试均值聚合算子"""
        operator = VisibilityGraphOperator()
        
        # 创建测试数据
        prices = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
        
        result = operator._aggregate_mean(prices, window=3)
        
        assert isinstance(result, np.ndarray)
        assert len(result) == len(prices)
    
    def test_aggregate_ratio(self):
        """测试比率聚合算子"""
        operator = VisibilityGraphOperator()
        
        # 创建测试数据
        prices = np.array([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
        
        result = operator._aggregate_ratio(prices, window=3)
        
        assert isinstance(result, np.ndarray)
        assert len(result) == len(prices)


class TestConvenienceFunctions:
    """测试便捷函数"""
    
    def test_get_visibility_operator_descriptions(self):
        """测试获取算子描述便捷函数"""
        descriptions = get_visibility_operator_descriptions()
        
        assert isinstance(descriptions, str)
        assert 'backward_visibility' in descriptions
    
    def test_get_visibility_example_factors(self):
        """测试获取示例因子便捷函数"""
        examples = get_visibility_example_factors()
        
        assert isinstance(examples, list)
        assert len(examples) > 0


class TestEdgeCases:
    """测试边界条件"""
    
    def test_empty_prices(self):
        """测试空价格序列"""
        operator = VisibilityGraphOperator()
        
        prices = np.array([])
        
        result = operator._backward_visibility(prices, window=5)
        
        assert isinstance(result, np.ndarray)
        assert len(result) == 0
    
    def test_single_price(self):
        """测试单个价格点"""
        operator = VisibilityGraphOperator()
        
        prices = np.array([100.0])
        
        result = operator._backward_visibility(prices, window=5)
        
        assert isinstance(result, np.ndarray)
        assert len(result) == 1
    
    def test_short_prices(self):
        """测试短价格序列"""
        operator = VisibilityGraphOperator()
        
        prices = np.array([100, 101])
        
        result = operator._backward_visibility(prices, window=5)
        
        assert isinstance(result, np.ndarray)
        assert len(result) == 2
    
    def test_constant_prices(self):
        """测试常数价格序列"""
        operator = VisibilityGraphOperator()
        
        prices = np.array([100.0] * 10)
        
        result = operator._backward_visibility(prices, window=5)
        
        assert isinstance(result, np.ndarray)
        assert len(result) == 10


class TestPromptGeneration:
    """测试 Prompt 生成"""
    
    def test_prompt_contains_operators(self):
        """测试 prompt 包含算子描述"""
        operator = VisibilityGraphOperator()
        
        descriptions = operator.get_operator_descriptions()
        
        # 检查所有算子都在描述中
        assert 'backward_visibility' in descriptions
        assert 'horizontal_visibility' in descriptions
        assert 'visibility_matrix' in descriptions
        assert 'visibility_aggregate_mean' in descriptions
        assert 'visibility_aggregate_ratio' in descriptions
    
    def test_prompt_contains_examples(self):
        """测试 prompt 包含示例因子"""
        operator = VisibilityGraphOperator()
        
        examples = operator.get_example_factors()
        
        # 检查示例因子代码
        for example in examples:
            assert 'def factor' in example
            assert 'import' in example


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
