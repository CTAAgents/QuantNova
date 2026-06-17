# 统一记忆管理系统设计文档

> 版本：v1.1 | 创建日期：2026-06-17 | 更新日期：2026-06-17
> 状态：已完成

## 一、问题概述

### 1.1 现状

当前系统存在多个记忆相关模块，功能重叠且缺乏统一管理：

| 模块 | 功能 | 问题 |
|------|------|------|
| `memory/manager.py` | 统一记忆管理器 | 核心模块，但部分功能未使用 |
| `experience.py` | 经验记忆池 | 与 memory/manager 功能重叠 |
| `memory_bridge.py` | Scanner/Reasoner/Evolver 集成 | 仅覆盖部分模块 |
| `factor_experience_db.py` | 因子经验数据库 | 独立于主记忆系统 |
| `memory_vectorizer.py` | 文本向量化 | 未与主记忆系统集成 |
| `vector_enhancement.py` | 向量增强 | 未与主记忆系统集成 |
| `selective_update.py` | 选择性更新 | 未与主记忆系统集成 |
| `regime_gate.py` | 机制门 | 未与主记忆系统集成 |

### 1.2 目标

1. 统一所有记忆相关模块的接口
2. 将各模块的零散记忆内容纳入统一管理
3. 提供清晰的记忆生命周期管理
4. 支持新模块（VGRSI、Walk-Forward、Volatility Anchor）的记忆需求

---

## 二、统一记忆架构

### 2.1 三层记忆模型

```
┌─────────────────────────────────────────────────────────────────────┐
│                     统一记忆管理器 (UnifiedMemoryManager)            │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ 短期记忆 (Short-term)                                          │  │
│  │ - 当前会话上下文                                                │  │
│  │ - 临时计算结果                                                  │  │
│  │ - 存储：内存 (Dict)                                             │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ 工作记忆 (Working)                                             │  │
│  │ - 今日信号、预警、决策简报                                       │  │
│  │ - 因子评估结果                                                  │  │
│  │ - Walk-Forward 验证结果                                         │  │
│  │ - 存储：SQLite                                                  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ 长期记忆 (Long-term)                                           │  │
│  │ - 交易经验、策略规则、模式库                                     │  │
│  │ - 因子演化轨迹、进化历史                                         │  │
│  │ - K线时序数据、技术指标历史                                      │  │
│  │ - 存储：SQLite + DuckDB + 向量索引                              │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 统一接口设计

```python
class UnifiedMemoryManager:
    """统一记忆管理器"""
    
    # ========== 经验管理 ==========
    def store_experience(self, experience: Dict) -> str
    def retrieve_experiences(self, context: Dict, top_k: int) -> List[Dict]
    def retrieve_experiences_multi_path(self, context: Dict, top_k: int) -> List[Dict]
    
    # ========== 因子管理 ==========
    def store_factor_result(self, factor_result: Dict) -> str
    def get_factor_history(self, factor_name: str) -> List[Dict]
    def store_factor_evaluation(self, evaluation: Dict) -> str
    
    # ========== Walk-Forward 管理 ==========
    def store_walk_forward_result(self, wf_result: Dict) -> str
    def get_walk_forward_history(self, factor_name: str) -> List[Dict]
    
    # ========== 可见图因子管理 ==========
    def store_visibility_graph_factor(self, factor_info: Dict) -> str
    def get_visibility_graph_factors(self) -> List[Dict]
    
    # ========== 波动率锚点管理 ==========
    def store_volatility_anchor(self, anchor_info: Dict) -> str
    def get_volatility_anchor(self, symbol: str) -> Dict
    
    # ========== 交易管理 ==========
    def store_trade(self, trade: Dict) -> str
    def get_trade_history(self, symbol: str, n: int) -> List[Dict]
    
    # ========== 规则管理 ==========
    def store_rule(self, rule: Dict) -> str
    def get_active_rules(self, rule_type: str) -> List[Dict]
    
    # ========== 进化管理 ==========
    def store_evolution_result(self, evolution: Dict) -> str
    def get_evolution_history(self) -> List[Dict]
```

---

## 三、各模块记忆需求

### 3.1 因子进化引擎 (FactorEvolutionEngine)

**需要记忆的内容**：
- 因子生成历史（代码、来源、时间）
- 因子评估结果（IC、ICIR、t-stat）
- 门控决策（晋升/观察/淘汰）
- Walk-Forward 验证结果（通过率、OOS Sharpe）

**接口**：
```python
memory.store_factor_result({
    'factor_name': 'VGRSI_A0',
    'code': '...',
    'source': 'seed_pool',
    'evaluation': {'ic': 0.05, 'icir': 1.2},
    'walk_forward': {'pass_rate': 0.8, 'oos_sharpe': 0.6},
    'decision': 'promote'
})
```

### 3.2 可见图因子 (VisibilityGraph)

**需要记忆的内容**：
- 可见图算子使用历史
- 因子生成参数（窗口大小、聚合模式）
- 因子表现评估

**接口**：
```python
memory.store_visibility_graph_factor({
    'factor_name': 'VGRSI_A0',
    'operator': 'backward_visibility',
    'params': {'window': 100, 'aggregation': 'A0'},
    'performance': {'ic': 0.05, 'icir': 1.2}
})
```

### 3.3 Walk-Forward 验证器 (WalkForwardValidator)

**需要记忆的内容**：
- 验证配置（窗口大小、步长）
- 每个窗口的验证结果
- 最终通过率和参数

**接口**：
```python
memory.store_walk_forward_result({
    'factor_name': 'VGRSI_A0',
    'config': {'optimization_window': 30, 'test_window': 7},
    'total_windows': 10,
    'passed_windows': 8,
    'pass_rate': 0.8,
    'avg_oos_sharpe': 0.6,
    'window_results': [...]
})
```

### 3.4 波动率锚点 (VolatilityAnchor)

**需要记忆的内容**：
- 锚点计算参数（窗口、系数）
- 历史锚点值
- 止损效果评估

**接口**：
```python
memory.store_volatility_anchor({
    'symbol': 'RB',
    'params': {'window': 20, 'multiplier': 2.0},
    'anchor_value': 50.0,
    'stop_loss': 3150.0,
    'effectiveness': {'win_rate': 0.6, 'avg_loss': -2.0}
})
```

### 3.5 Reasoner 推理引擎

**需要记忆的内容**：
- 推理结果（方向、置信度、理由）
- 市场评估
- 决策简报

**接口**：
```python
memory.store_reasoning_result({
    'symbol': 'RB',
    'direction': 'LONG',
    'confidence': 0.8,
    'reasoning': '...',
    'market_assessment': {...}
})
```

---

## 四、实施计划

### 4.1 阶段一：统一接口

1. 扩展 `memory/manager.py`，添加新接口
2. 更新 `memory_bridge.py`，覆盖所有模块
3. 合并 `experience.py` 到 `memory/manager.py`

### 4.2 阶段二：集成新模块

1. 因子进化引擎集成记忆系统
2. 可见图因子集成记忆系统
3. Walk-Forward 验证器集成记忆系统
4. 波动率锚点集成记忆系统

### 4.3 阶段三：优化与测试

1. 编写测试用例
2. 优化查询性能
3. 更新文档

---

## 五、文件清单

| 文件 | 类型 | 说明 |
|------|------|------|
| `scripts/trend_scanner/memory/manager.py` | 修改 | 扩展统一记忆管理器 |
| `scripts/trend_scanner/memory_bridge.py` | 修改 | 更新集成桥接器 |
| `scripts/trend_scanner/factor_evolution_engine.py` | 修改 | 集成记忆系统 |
| `scripts/trend_scanner/visibility_graph.py` | 修改 | 集成记忆系统 |
| `scripts/trend_scanner/walk_forward_validator.py` | 修改 | 集成记忆系统 |
| `scripts/trend_scanner/volatility_anchor.py` | 修改 | 集成记忆系统 |
| `tests/test_unified_memory.py` | 测试 | 统一记忆系统测试 |

---

## 六、风险提示

1. **兼容性**: 修改核心模块可能影响现有功能
2. **性能**: 统一管理可能增加查询延迟
3. **复杂度**: 系统复杂度增加

---

*本文档是统一记忆管理系统的设计规范。*
