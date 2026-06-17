# 波动幅度中位数作为止损锚点设计文档

> 版本：v1.0 | 创建日期：2026-06-17
> 状态：待实施

## 一、项目概述

### 1.1 目标

在 Reasoner 推理时，提供"近期 K 线波动幅度中位数"作为止损参考锚点，增强推理的数据支撑。

### 1.2 背景

论文中的风险管理参数化：止损/止盈基于最近 N 根 K 线高度的中位数乘以系数 Z，N 和 Z 也是优化参数。

与系统理念的差异：Trend-scanner 的核心原则是"推理重于规则"，止损位置由 Reasoner Agent 动态推导，不预设固定规则。但论文的**参数化风控思路**可以作为 Reasoner 的参考框架：
- Reasoner 在推导止损时，可以参考"近期 K 线波动幅度中位数"作为锚点
- 这比纯 LLM 推理更有数据支撑，同时保留了动态调整的灵活性

### 1.3 范围

- 实现 VolatilityAnchor 类
- 集成到 Reasoner 推理流程
- 编写完整测试用例

---

## 二、技术设计

### 2.1 核心概念

**波动幅度中位数**：最近 N 根 K 线高度（High - Low）的中位数。

**止损锚点**：波动幅度中位数乘以系数 Z，作为止损参考。

**公式**：
```
candle_heights = high - low (最近 N 根 K 线)
median_height = median(candle_heights)
stop_loss_anchor = median_height * Z
```

### 2.2 接口定义

```python
class VolatilityAnchor:
    """波动幅度止损锚点计算器"""
    
    def __init__(self, window: int = 20, multiplier: float = 2.0):
        """
        初始化波动幅度锚点计算器
        
        Args:
            window: 回看窗口大小（K 线数量）
            multiplier: 系数 Z
        """
        pass
    
    def calculate(self, df: pd.DataFrame) -> pd.Series:
        """
        计算波动幅度锚点
        
        Args:
            df: DataFrame with 'high' and 'low' columns
            
        Returns:
            pd.Series: 止损锚点值
        """
        pass
    
    def calculate_for_position(self, df: pd.DataFrame, 
                               entry_price: float, 
                               direction: str) -> float:
        """
        计算特定持仓的止损锚点
        
        Args:
            df: DataFrame with 'high' and 'low' columns
            entry_price: 入场价格
            direction: 方向 ('long' 或 'short')
            
        Returns:
            float: 止损价格
        """
        pass


def volatility_anchor(df: pd.DataFrame, 
                      window: int = 20, 
                      multiplier: float = 2.0) -> pd.DataFrame:
    """
    便捷函数：计算波动幅度锚点
    
    Args:
        df: DataFrame with 'high' and 'low' columns
        window: 回看窗口大小
        multiplier: 系数 Z
        
    Returns:
        pd.DataFrame: 包含锚点值的 DataFrame
    """
    pass
```

### 2.3 Reasoner 集成

在 Reasoner 推理时，将波动幅度锚点作为参考信息注入：

```python
def generate_trading_brief(self, market_context: str, 
                          positions: List[Dict]) -> str:
    """生成交易决策简报"""
    
    # 计算波动幅度锚点
    anchor = VolatilityAnchor(window=20, multiplier=2.0)
    
    # 为每个持仓计算止损锚点
    for pos in positions:
        df = self.get_price_data(pos['symbol'])
        stop_loss = anchor.calculate_for_position(
            df, pos['entry_price'], pos['direction']
        )
        pos['volatility_anchor'] = stop_loss
    
    # 构建 prompt，注入锚点信息
    prompt = f"""
    市场上下文：{market_context}
    
    持仓信息（含波动幅度止损锚点）：
    {positions}
    
    请根据以上信息生成交易决策简报，特别注意：
    1. 波动幅度止损锚点是基于近期市场波动计算的参考值
    2. 你可以根据当前市场状态调整止损位置
    3. 如果市场波动率变化较大，建议调整止损距离
    """
    
    return self.llm_client.generate(prompt)
```

### 2.4 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| window | 20 | 回看窗口大小（K 线数量） |
| multiplier | 2.0 | 系数 Z，控制止损距离 |

**参数调优建议**：
- 短线交易：window=10, multiplier=1.5
- 中线交易：window=20, multiplier=2.0
- 长线交易：window=50, multiplier=3.0

---

## 三、文件清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `scripts/trend_scanner/volatility_anchor.py` | 模块 | 波动幅度锚点计算器 |
| `tests/test_volatility_anchor.py` | 测试 | 波动幅度锚点单元测试 |
| `scripts/trend_scanner/reasoning.py` | 修改 | 集成到 Reasoner 推理流程 |

---

## 四、与现有系统的集成

### 4.1 Reasoner Agent

在 Reasoner 推理时，将波动幅度锚点作为参考信息注入 prompt。

### 4.2 止损计算器

可与现有的 StopLossCalculator 集成，提供更灵活的止损策略。

### 4.3 持仓健康度

可纳入 PositionHealthChecker 的评估指标。

---

## 五、风险提示

1. **参数敏感性**: window 和 multiplier 的选择对结果影响较大
2. **市场适应性**: 不同品种的波动率特性不同，可能需要品种特定的参数
3. **滞后性**: 基于历史数据计算，对突发波动反应滞后

---

*本文档是波动幅度中位数作为止损锚点的设计规范。*
