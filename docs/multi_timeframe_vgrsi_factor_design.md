# 多周期 VGRSI 一致性因子设计文档

> 版本：v1.0 | 创建日期：2026-06-17
> 状态：待实施

## 一、项目概述

### 1.1 目标

将 MultiTimeframeVGRSI 的共识信号封装为独立因子，可直接用于多因子模型。

### 1.2 背景

论文使用 M1、M5、M30 三个时间周期同时确认信号，只有三个周期同向才开仓。这种多时间框架确认机制比简单的"大周期过滤"更严格，可以有效过滤噪声信号。

### 1.3 范围

- 在 `visibility_graph.py` 中增加 `consensus_factor()` 函数
- 封装多时间框架共识信号为独立因子
- 纳入种子因子池
- 编写完整测试用例

---

## 二、技术设计

### 2.1 核心概念

**多时间框架一致性**：只有当所有时间框架都产生同向信号时，才输出最终信号。

**共识信号**：
- 1 = 所有时间框架都看多
- -1 = 所有时间框架都看空
- 0 = 无共识

### 2.2 接口定义

```python
class MultiTimeframeVGRSIFactor:
    """多周期 VGRSI 一致性因子"""
    
    def __init__(self, 
                 timeframe_configs: Dict[str, Dict[str, Any]] = None,
                 threshold_upper: float = 70.0,
                 threshold_lower: float = 30.0):
        """
        初始化多时间框架 VGRSI 因子
        
        Args:
            timeframe_configs: 各时间框架的配置
            threshold_upper: 买入信号阈值
            threshold_lower: 卖出信号阈值
        """
        pass
    
    def calculate(self, prices_dict: Dict[str, pd.Series]) -> pd.Series:
        """
        计算多时间框架共识因子
        
        Args:
            prices_dict: 各时间框架的价格数据 {timeframe: pd.Series}
            
        Returns:
            pd.Series: 共识因子值 (1=多, -1=空, 0=无共识)
        """
        pass
    
    def generate_signals(self, consensus_values: pd.Series) -> pd.Series:
        """
        根据共识因子值生成交易信号
        
        Args:
            consensus_values: 共识因子值
            
        Returns:
            pd.Series: 信号序列 (1=买入, -1=卖出, 0=无信号)
        """
        pass


def consensus_factor(prices_dict: Dict[str, pd.Series],
                     timeframe_configs: Dict[str, Dict[str, Any]] = None,
                     threshold_upper: float = 70.0,
                     threshold_lower: float = 30.0) -> pd.DataFrame:
    """
    便捷函数：计算多时间框架共识因子
    
    Args:
        prices_dict: 各时间框架的价格数据
        timeframe_configs: 各时间框架的配置
        threshold_upper: 买入信号阈值
        threshold_lower: 卖出信号阈值
        
    Returns:
        pd.DataFrame: 包含共识因子和信号的 DataFrame
    """
    pass
```

### 2.3 时间框架配置

```python
# 默认配置
timeframe_configs = {
    'M1': {'window_size': 50, 'aggregation_mode': 'A0'},
    'M5': {'window_size': 100, 'aggregation_mode': 'A0'},
    'M30': {'window_size': 150, 'aggregation_mode': 'A0'}
}
```

### 2.4 信号生成逻辑

```python
def generate_signals(self, consensus_values: pd.Series) -> pd.Series:
    signals = pd.Series(0, index=consensus_values.index)
    
    for i in range(1, len(consensus_values)):
        # 买入信号: 共识值从 0 或 -1 变为 1
        if consensus_values[i] == 1 and consensus_values[i-1] != 1:
            signals.iloc[i] = 1
        # 卖出信号: 共识值从 0 或 1 变为 -1
        elif consensus_values[i] == -1 and consensus_values[i-1] != -1:
            signals.iloc[i] = -1
    
    return signals
```

---

## 三、文件清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `scripts/trend_scanner/visibility_graph.py` | 修改 | 增加 MultiTimeframeVGRSIFactor 类 |
| `tests/test_multi_timeframe_vgrsi_factor.py` | 测试 | 多周期因子单元测试 |
| `tools/add_multi_timeframe_vgrsi_factor.py` | 工具 | 添加因子到种子因子池 |

---

## 四、与现有系统的集成

### 4.1 因子进化引擎

作为种子因子进入候选池，参与 Generate→Eval→Gate→Memory 闭环。

### 4.2 多因子模型

可与其他因子（如传统 RSI、MACD 等）组合，形成多因子模型。

### 4.3 Reasoner Agent

共识信号可作为 Reasoner 推理的输入之一。

---

## 五、风险提示

1. **信号稀疏**: 三周期同时确认的条件很严格，信号可能极其稀疏
2. **数据需求**: 需要多个时间框架的数据，数据获取成本较高
3. **参数敏感性**: 不同时间框架的窗口大小和阈值需要优化

---

*本文档是多周期 VGRSI 一致性因子的设计规范。*
