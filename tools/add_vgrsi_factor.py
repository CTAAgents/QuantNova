"""
添加 VGRSI 因子到种子因子池

基于论文 "Visibility Graphs Can Make Money in Financial Markets" (arXiv: 2605.01300)
将 VGRSI 因子添加到系统的种子因子池中。

创建日期：2026-06-17
"""

import os
import sys


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.trend_scanner.seed_factor_pool import SeedFactorPool


def add_vgrsi_factor():
    """添加 VGRSI 因子到种子因子池"""

    # 初始化种子因子池
    pool = SeedFactorPool()

    # VGRSI A0 因子代码
    vgrsi_a0_code = '''
import numpy as np
import pandas as pd

def factor(df, window_size=100, threshold_upper=70, threshold_lower=30):
    """
    VGRSI A0 (Visibility Graph Relative Strength Index - Mean Aggregation)
    
    基于可见图的 RSI 变体，使用均值聚合模式捕捉趋势持续性。
    
    Args:
        df: DataFrame with 'close' column
        window_size: 可见性计算的回看窗口
        threshold_upper: 买入信号阈值
        threshold_lower: 卖出信号阈值
    
    Returns:
        pd.Series: VGRSI A0 值 (0-100)
    """
    from scripts.trend_scanner.visibility_graph import VGRSI
    
    calculator = VGRSI(
        window_size=window_size,
        aggregation_mode='A0',
        threshold_upper=threshold_upper,
        threshold_lower=threshold_lower
    )
    
    vgrsi_values = calculator.calculate(df['close'].values)
    return pd.Series(vgrsi_values, index=df.index)
'''

    # VGRSI A1 因子代码
    vgrsi_a1_code = '''
import numpy as np
import pandas as pd

def factor(df, window_size=100, threshold_upper=70, threshold_lower=30):
    """
    VGRSI A1 (Visibility Graph Relative Strength Index - Ratio Aggregation)
    
    基于可见图的 RSI 变体，使用比率聚合模式捕捉突破脉冲。
    
    Args:
        df: DataFrame with 'close' column
        window_size: 可见性计算的回看窗口
        threshold_upper: 买入信号阈值
        threshold_lower: 卖出信号阈值
    
    Returns:
        pd.Series: VGRSI A1 值 (0-100)
    """
    from scripts.trend_scanner.visibility_graph import VGRSI
    
    calculator = VGRSI(
        window_size=window_size,
        aggregation_mode='A1',
        threshold_upper=threshold_upper,
        threshold_lower=threshold_lower
    )
    
    vgrsi_values = calculator.calculate(df['close'].values)
    return pd.Series(vgrsi_values, index=df.index)
'''

    # 添加 VGRSI A0 因子
    pool.add_seed(
        name="VGRSI_A0",
        code=vgrsi_a0_code,
        logic="基于可见图的 RSI 变体，使用均值聚合模式。将价格时间序列转换为可见图网络，利用价格点之间的几何可见关系替代传统 RSI 的简单价格变化。A0 模式使用均值聚合，捕捉趋势持续性。",
        economic_rationale="可见图捕捉价格序列的拓扑结构特征，而非简单的趋势或动量。当价格点之间的可见性关系呈现特定模式时，表明市场处于趋势持续状态。",
        source="arXiv:2605.01300 - Visibility Graphs Can Make Money in Financial Markets",
        category="momentum",
    )

    # 添加 VGRSI A1 因子
    pool.add_seed(
        name="VGRSI_A1",
        code=vgrsi_a1_code,
        logic="基于可见图的 RSI 变体，使用比率聚合模式。将价格时间序列转换为可见图网络，利用价格点之间的几何可见关系替代传统 RSI 的简单价格变化。A1 模式使用比率聚合，捕捉突破脉冲。",
        economic_rationale="可见图捕捉价格序列的拓扑结构特征。当可见性关系中正向关系显著多于负向关系时，表明市场处于突破状态。",
        source="arXiv:2605.01300 - Visibility Graphs Can Make Money in Financial Markets",
        category="momentum",
    )

    # 打印摘要
    summary = pool.get_summary()
    print("种子因子池摘要:")
    print(f"  总因子数: {summary['total']}")
    print(f"  分类: {summary['categories']}")
    print(f"  状态: {summary['statuses']}")

    # 获取待验证的种子
    pending = pool.get_pending_seeds()
    print(f"\n待验证的种子因子 ({len(pending)}):")
    for seed in pending:
        print(f"  - {seed.name}: {seed.logic[:50]}...")


if __name__ == "__main__":
    add_vgrsi_factor()
