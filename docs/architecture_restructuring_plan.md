# 系统架构重构计划

> 版本：v1.0 | 创建日期：2026-06-18
> 状态：进行中

## 一、当前架构问题分析

### 1.1 目录结构问题

**现状**：
```
scripts/
├── trend_scanner/     # 100+ 文件，职责过重
├── strategies/        # 仅包含 Carry 策略
└── fundamental/       # 基本面分析
```

**问题**：
- `trend_scanner` 目录承载了过多职责：策略、因子、推理、执行、进化、记忆等
- 策略层与因子进化层混在一起
- 缺乏清晰的模块边界

### 1.2 职责划分问题

**现状**：
- 趋势跟踪策略、因子进化、推理引擎都放在 `trend_scanner` 下
- Carry 策略作为独立模块放在 `strategies` 下
- 但趋势跟踪策略本身没有明确的目录归属

**问题**：
- 趋势跟踪策略应该有自己的独立目录
- 策略与基础设施应该分离

### 1.3 工作流问题

**现状**：
- 扫描流程：`scanner.py` → `reasoning.py` → `brief.py`
- 因子进化：`factor_generator.py` → `factor_evaluator.py` → `factor_evolution_engine.py`
- 执行流程：`execution.py` → `position_sizer.py` → `stop_loss.py`

**问题**：
- 工作流分散在多个模块中
- 缺乏统一的工作流编排

---

## 二、重构目标

### 2.1 核心目标

1. **职责分离**：每个目录只负责一个核心职责
2. **模块独立**：策略模块可以独立运行
3. **工作流清晰**：每个工作流有明确的入口和出口
4. **易于扩展**：新策略可以独立添加，不影响现有系统

### 2.2 设计原则

1. **策略独立**：每种策略有自己的目录和入口
2. **基础设施共享**：通用模块放在共享目录
3. **工作流编排**：通过配置和编排层协调各模块

---

## 三、新架构设计

### 3.1 目录结构

```
scripts/
├── core/                          # 核心基础设施
│   ├── __init__.py
│   ├── agent_base.py              # Agent 基类
│   ├── memory/                    # 记忆系统
│   │   ├── manager.py
│   │   ├── duckdb_store.py
│   │   ├── sqlite_store.py
│   │   └── retriever.py
│   ├── data/                      # 数据层
│   │   ├── unified_data_router.py
│   │   ├── data_sync.py
│   │   └── data_validator.py
│   └── utils/                     # 工具函数
│       ├── knowledge_anchors.py
│       └── knowledge_ingestion.py
│
├── indicators/                    # 指标计算层
│   ├── __init__.py
│   ├── indicator_engine.py        # 35+ 技术指标
│   ├── indicator_hub.py           # 统一指标加载
│   ├── multi_dimension_screener.py # 五维度评分
│   └── volatility_anchor.py       # 波动率锚点
│
├── reasoning/                     # 推理层
│   ├── __init__.py
│   ├── reasoning_engine.py        # LLM 推理引擎
│   ├── debate_engine.py           # 多角色辩论
│   ├── scenario_analyzer.py       # 场景分析
│   └── brief.py                   # 决策简报生成
│
├── evolution/                     # 因子进化层
│   ├── __init__.py
│   ├── factor_generator.py        # 因子生成
│   ├── factor_evaluator.py        # 因子评估
│   ├── factor_gate.py             # 门控决策
│   ├── factor_evolution_engine.py # 闭环进化
│   ├── factor_param_optimizer.py  # 参数优化
│   ├── seed_factor_pool.py        # 种子因子池
│   ├── multi_factor_model.py      # 多因子模型
│   ├── factor_experience_db.py    # 经验数据库
│   ├── walk_forward_validator.py  # Walk-Forward 验证
│   └── visibility_graph.py        # 可见图指标
│
├── strategies/                    # 策略层（独立策略）
│   ├── __init__.py
│   ├── trend_following/           # 趋势跟踪策略
│   │   ├── __init__.py
│   │   ├── scanner.py             # 主扫描器
│   │   ├── strategy.py            # 策略池
│   │   ├── risk_management.py     # 风险管理
│   │   ├── execution.py           # 执行引擎
│   │   ├── position_sizer.py      # 仓位管理
│   │   ├── stop_loss.py           # 止损管理
│   │   └── portfolio.py           # 组合管理
│   ├── carry/                     # Carry 策略
│   │   ├── __init__.py
│   │   └── carry_analyzer.py
│   └── arbitrage/                 # 套利策略
│       ├── __init__.py
│       └── arbitrage_analyzer.py
│
├── evolution_tools/               # 进化工具层
│   ├── __init__.py
│   ├── evolution_manager.py       # 进化管理器
│   ├── trajectory_analysis.py     # 轨迹分析
│   ├── trade_journal.py           # 交易日志
│   ├── strategy_health.py         # 策略健康度
│   ├── overfitting_detector.py    # 过拟合检测
│   └── circuit_breaker.py         # 熔断器
│
└── tools/                         # 工具层
    ├── __init__.py
    ├── monte_carlo.py             # 蒙特卡洛模拟
    ├── strategy_incubator.py      # 策略孵化
    └── scenario_analyzer.py       # 场景分析
```

### 3.2 模块职责

| 模块 | 职责 | 核心文件 |
|------|------|----------|
| **core** | 核心基础设施 | agent_base, memory, data, utils |
| **indicators** | 指标计算 | indicator_engine, indicator_hub, multi_dimension_screener |
| **reasoning** | 推理层 | reasoning_engine, debate_engine, scenario_analyzer |
| **evolution** | 因子进化 | factor_generator, factor_evaluator, factor_evolution_engine |
| **strategies** | 策略层 | trend_following, carry, arbitrage |
| **evolution_tools** | 进化工具 | evolution_manager, trajectory_analysis, trade_journal |
| **tools** | 通用工具 | monte_carlo, strategy_incubator |

### 3.3 工作流设计

#### 3.3.1 趋势跟踪工作流

```
数据同步 → 指标计算 → 信号扫描 → 推理分析 → 决策简报
    ↓           ↓           ↓           ↓           ↓
data_sync   indicators   scanner    reasoning     brief
```

#### 3.3.2 因子进化工作流

```
种子因子 → 因子生成 → 因子评估 → 门控决策 → 经验记忆
    ↓           ↓           ↓           ↓           ↓
seed_pool   generator   evaluator    gate      experience_db
```

#### 3.3.3 Carry 策略工作流

```
期限结构 → 展期收益率 → 库存分析 → Carry 信号
    ↓           ↓           ↓           ↓
term_struct  roll_yield  inventory  carry_signal
```

---

## 四、迁移计划

### 4.1 Phase 1：创建新目录结构

1. 创建 `scripts/core/` 目录
2. 创建 `scripts/indicators/` 目录
3. 创建 `scripts/reasoning/` 目录
4. 创建 `scripts/evolution/` 目录
5. 创建 `scripts/strategies/trend_following/` 目录

### 4.2 Phase 2：迁移文件

1. 迁移核心模块到 `core/`
2. 迁移指标模块到 `indicators/`
3. 迁移推理模块到 `reasoning/`
4. 迁移因子进化模块到 `evolution/`
5. 迁移趋势跟踪模块到 `strategies/trend_following/`

### 4.3 Phase 3：更新导入

1. 更新所有模块的导入路径
2. 更新测试文件的导入路径
3. 更新工具脚本的导入路径

### 4.4 Phase 4：文档更新

1. 更新 README.md
2. 更新系统架构文档
3. 更新用户手册
4. 更新测试文档

---

## 五、预期收益

| 收益 | 说明 |
|------|------|
| **职责清晰** | 每个目录只负责一个核心职责 |
| **易于维护** | 模块边界清晰，修改影响可控 |
| **易于扩展** | 新策略可以独立添加 |
| **易于测试** | 模块独立，测试更简单 |

---

## 六、风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 导入路径变更 | 所有测试需要更新 | 批量更新导入路径 |
| 依赖关系变更 | 可能引入循环依赖 | 仔细设计模块边界 |
| 工作流变更 | 可能影响现有功能 | 充分测试验证 |

---

*本计划由 WorkBuddy 于 2026-06-18 创建*
