# 可见图算子注入因子生成器设计文档

> 版本：v1.0 | 创建日期：2026-06-17
> 状态：待实施

## 一、项目概述

### 1.1 目标

在 `factor_generator.py` 的 LLM prompt 中增加"可见图类因子"作为可选范式，让 LLM 可以基于此范式自由组合生成新因子，扩展因子搜索空间。

### 1.2 背景

当前因子生成器的搜索空间主要在传统技术指标（均值、动量、波动率）的组合变异中。可见图（Visibility Graph）是一个**因子构造范式**，而非单一因子。论文只用了"向后可见性"这一种关系，但可见图理论还包含：
- 水平可见性（Horizontal Visibility Graph）
- 有限步长可见性
- 有向可见性

这些变体都可以作为因子生成器的**新算子/新范式**注入，扩展因子搜索空间。

### 1.3 范围

- 实现 VisibilityGraphOperator 类
- 修改 factor_generator.py 的 prompt 模板
- 添加可见图相关算子到因子知识库
- 编写完整测试用例

---

## 二、技术设计

### 2.1 核心概念

**算子（Operator）**：因子构造的基本单元，如"均值"、"动量"、"波动率"。

**范式（Paradigm）**：一组相关的算子，如"可见图类"包含：
- 向后可见性（Backward Visibility）
- 水平可见性（Horizontal Visibility）
- 可见性矩阵（Visibility Matrix）
- 可见性聚合（Visibility Aggregation）

### 2.2 接口定义

```python
class VisibilityGraphOperator:
    """可见图算子管理器"""
    
    def __init__(self):
        self.operators = {
            'backward_visibility': self._backward_visibility,
            'horizontal_visibility': self._horizontal_visibility,
            'visibility_matrix': self._visibility_matrix,
            'visibility_aggregate_mean': self._aggregate_mean,
            'visibility_aggregate_ratio': self._aggregate_ratio,
        }
    
    def get_operator_descriptions(self) -> str:
        """获取所有算子的描述，用于 LLM prompt"""
        pass
    
    def get_example_factors(self) -> List[str]:
        """获取示例因子代码，用于 LLM prompt"""
        pass
    
    def _backward_visibility(self, prices, **params) -> np.ndarray:
        """向后可见性关系"""
        pass
    
    def _horizontal_visibility(self, prices, **params) -> np.ndarray:
        """水平可见性关系"""
        pass
    
    def _visibility_matrix(self, prices, **params) -> np.ndarray:
        """可见性矩阵"""
        pass
    
    def _aggregate_mean(self, visibility, prices, **params) -> np.ndarray:
        """均值聚合"""
        pass
    
    def _aggregate_ratio(self, visibility, prices, **params) -> np.ndarray:
        """比率聚合"""
        pass


class FactorGeneratorWithVisibilityGraph(FactorGenerator):
    """扩展因子生成器，支持可见图算子"""
    
    def __init__(self, llm_client=None, validator=None, knowledge_manager=None):
        super().__init__(llm_client, validator, knowledge_manager)
        self.visibility_operator = VisibilityGraphOperator()
    
    def _build_generation_prompt(self, market_context: str, 
                                 research_report: str = None) -> str:
        """构建包含可见图算子的 prompt"""
        base_prompt = super()._build_generation_prompt(market_context, research_report)
        
        # 添加可见图算子描述
        visibility_desc = self.visibility_operator.get_operator_descriptions()
        visibility_examples = self.visibility_operator.get_example_factors()
        
        enhanced_prompt = f"""
{base_prompt}

## 可见图类因子范式（新增）

### 可用算子
{visibility_desc}

### 示例因子
{visibility_examples}

### 使用建议
- 可见图捕捉价格序列的拓扑结构特征，与传统趋势/动量指标互补
- 建议将可见图算子与传统算子组合，如：可见性 + 均值、可见性 + 波动率
- A0 聚合模式适合捕捉趋势持续性，A1 聚合模式适合捕捉突破脉冲
"""
        return enhanced_prompt
```

### 2.3 算子描述（用于 LLM prompt）

```
### 可见图类算子

1. **backward_visibility(prices, window=100)**
   - 功能：计算价格点之间的向后可见性关系
   - 返回：可见性矩阵（哪些点从哪些点可见）
   - 适用：捕捉价格序列的局部结构特征

2. **horizontal_visibility(prices, window=100)**
   - 功能：计算水平可见性关系（更严格的可见性条件）
   - 返回：水平可见性矩阵
   - 适用：捕捉价格序列的转折点

3. **visibility_matrix(prices, window=100)**
   - 功能：计算完整的可见性矩阵
   - 返回：邻接矩阵表示的可见图
   - 适用：网络分析、度分布计算

4. **visibility_aggregate_mean(visibility, prices)**
   - 功能：基于可见性关系的均值聚合
   - 返回：聚合后的因子值
   - 适用：趋势持续性指标

5. **visibility_aggregate_ratio(visibility, prices)**
   - 功能：基于可见性关系的比率聚合
   - 返回：聚合后的因子值
   - 适用：突破脉冲指标
```

### 2.4 示例因子（用于 LLM prompt）

```python
# 示例 1：可见性动量因子
def factor(df, window=50):
    """可见性动量：基于可见性关系的动量指标"""
    from scripts.trend_scanner.visibility_graph import VisibilityGraph
    
    prices = df['close'].values
    n = len(prices)
    result = np.full(n, np.nan)
    
    for i in range(window, n):
        window_prices = prices[i-window:i+1]
        visibility = VisibilityGraph.compute_visibility_matrix(window_prices, window)
        
        # 计算可见性动量
        positive_count = 0
        negative_count = 0
        for j, visible_points in visibility.items():
            for k in visible_points:
                if window_prices[k] > window_prices[j]:
                    positive_count += 1
                elif window_prices[k] < window_prices[j]:
                    negative_count += 1
        
        if positive_count + negative_count > 0:
            result[i] = positive_count / (positive_count + negative_count) * 100
    
    return pd.Series(result, index=df.index)

# 示例 2：可见性波动率因子
def factor(df, window=50):
    """可见性波动率：基于可见性关系的波动率指标"""
    from scripts.trend_scanner.visibility_graph import VisibilityGraph
    
    prices = df['close'].values
    n = len(prices)
    result = np.full(n, np.nan)
    
    for i in range(window, n):
        window_prices = prices[i-window:i+1]
        visibility = VisibilityGraph.compute_visibility_matrix(window_prices, window)
        
        # 计算可见性波动率
        visible_returns = []
        for j, visible_points in visibility.items():
            for k in visible_points:
                ret = (window_prices[k] - window_prices[j]) / window_prices[j]
                visible_returns.append(abs(ret))
        
        if visible_returns:
            result[i] = np.std(visible_returns)
    
    return pd.Series(result, index=df.index)
```

---

## 三、文件清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `scripts/trend_scanner/visibility_graph_operator.py` | 模块 | 可见图算子管理器 |
| `scripts/trend_scanner/factor_generator.py` | 修改 | 增加可见图 prompt 模板 |
| `tests/test_visibility_graph_operator.py` | 测试 | 可见图算子单元测试 |
| `tools/add_visibility_operators.py` | 工具 | 添加算子到因子知识库 |

---

## 四、与现有系统的集成

### 4.1 因子生成器

扩展 FactorGenerator 的 prompt 模板，增加可见图算子描述和示例。

### 4.2 因子知识库

将可见图算子添加到因子知识库，供 LLM 参考。

### 4.3 因子进化引擎

LLM 生成的可见图类因子可直接进入进化引擎的候选池。

---

## 五、风险提示

1. **计算复杂度**: 可见图计算的时间复杂度为 O(n²)，对大数据集可能较慢
2. **因子有效性**: 可见图因子在国内期货市场的有效性需要验证
3. **LLM 理解**: LLM 对可见图概念的理解可能有限，需要提供足够的示例

---

*本文档是可见图算子注入因子生成器的设计规范。*
