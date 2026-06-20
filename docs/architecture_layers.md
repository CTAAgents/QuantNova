# QuantNova 层级架构

> 版本：v2.1.0 | 更新日期：2026-06-20 | 简化版

---

## 一、架构演进

### 原始架构（v1.0 - 11层 + 3跨层模块）

```
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 10 - 主协调层 (Orchestrator)                                   │
│   TradingAssistant + MainProcess + EventEngine + Workers + NLP      │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 9 - 分析工具层 (Analytics)                                     │
│   PositionSizer + StopLoss + RiskManager + Backtester + Health     │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 8 - 高级分析层 (Advanced Analysis)                             │
│   KnowledgeAnchors + VisibilityGraph + RegimeSegmenter + DataValid │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 7 - 因子进化层 (Factor Evolution)                              │
│   FactorGenerator → FactorEvaluator → FactorGate → Evolver         │
│   + FactorValidator + FactorLifecycle + FactorGovernance            │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 6 - 进化层 (Evolution)                                         │
│   EvolutionManager + TrajectoryAnalyzer + CircuitBreaker + Meta    │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 5 - 策略层 (Strategy)                                          │
│   TrendScanner + Carry + Arbitrage + RiskManager + Execution       │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 4 - 推理层 (Reasoning)                                         │
│   ReasoningEngine(LLM推理) + DebateEngine(鹰鸽辩论) + Scenario     │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 3 - 记忆层 (Memory)                                            │
│   UnifiedMemoryManager + MemoryBridge + ExperienceMemory + Vector  │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 2 - 存储层 (Storage)                                           │
│   DuckDBStore + SQLiteStore + DataSync + TqSdkBridge + DataRouter  │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 1 - 感知层 (Perception)                                        │
│   IndicatorEngine(自研35+指标+TqSdk内置70+指标+7维趋势强度)          │
│   + ContextAssembler + MultiDimensionScreener + MacroState           │
│   + 基本面分析(国际/国内新闻源)                                     │
├─────────────────────────────────────────────────────────────────────┤
│ Layer 0 - 数据模型层 (Foundation)                                    │
│   models.py + TrendScannerConfig + ControlVariable                  │
└─────────────────────────────────────────────────────────────────────┘

跨层模块:
  RL模块 (8个) → Layer 5(信号) + Layer 7(Walk-Forward) + Layer 8(接口) + Layer 10
  NLP模块 (7个) → Layer 1(命令解析) + Layer 10(LLM对话)
  Tools工具集 (10+个) → CLI入口脚本
```

### 简化后架构（v2.1.0 - 10层，无跨层模块）

```
┌─────────────────────────────────────────────────────────────────────┐
│                    QuantNova 简化架构 (v2.1.0)                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Layer 10: 配置层 (Configuration)                                   │
│  ├── trend_scanner_config.py                                        │
│  └── control_variable.py                                            │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 9: 记忆层 (Memory)                                           │
│  ├── manager.py - 记忆管理器                                        │
│  ├── experience.py - 经验记忆                                       │
│  ├── duckdb_store.py - DuckDB存储                                  │
│  └── evolution.py - 进化记忆                                        │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 8: 数据层 (Data)                                             │
│  ├── data_sync.py - 数据同步                                        │
│  ├── data_store.py - 数据存储                                       │
│  ├── data_validator.py - 数据校验                                   │
│  ├── futures_data_router.py - 期货数据路由                          │
│  └── securities_data_router.py - 证券数据路由                       │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 7: 因子评估层 (Factor Evaluation)                            │
│  ├── factor_evaluator.py - 因子评估                                 │
│  ├── factor_validator.py - 因子验证                                 │
│  ├── factor_gate.py - 因子门控                                      │
│  └── evolver.py - 进化管理                                          │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 6: 证券子系统 (Securities)                                   │
│  ├── provider.py - 证券数据提供者                                   │
│  ├── market_context.py - 市场上下文                                 │
│  ├── factor_library.py - 因子库                                     │
│  └── risk_manager.py - 风控管理                                     │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 5: 期货子系统 (Futures)                                      │
│  ├── provider.py - 期货数据提供者                                   │
│  ├── market_context.py - 市场上下文                                 │
│  ├── factor_library.py - 因子库                                     │
│  └── risk_manager.py - 风控管理                                     │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 4: 风控层 (Risk Control)                                     │
│  ├── crowding_detector.py - 拥挤度检测                              │
│  ├── deployment_risk.py - 部署风险                                  │
│  ├── return_attributor.py - 收益归因                                │
│  └── audit_trail.py - 审计轨迹                                      │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 3: 推理层 (Reasoning)                                        │
│  ├── reasoner.py - LLM推理引擎                                      │
│  ├── debater.py - 辩论引擎                                          │
│  ├── brief.py - 简报生成                                            │
│  ├── scenario_analyzer.py - 场景分析                                │
│  └── prompt_router.py - Prompt路由                                  │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 2: 基本面分析层 (Fundamental)                                │
│  ├── news_crawler.py - 新闻抓取                                     │
│  ├── supply_demand.py - 供需数据                                    │
│  └── geopolitical.py - 地缘政治                                    │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 1: 指标计算层 (Indicators)                                   │
│  ├── indicator_engine.py - 指标引擎                                 │
│  ├── indicator_hub.py - 指标中心                                    │
│  ├── multi_dimension_screener.py - 多维筛选                         │
│  ├── scoring_analytics.py - 评分分析                                │
│  └── macro_state.py - 宏观状态                                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 二、架构对比

| 维度 | 原始架构 | 简化后 |
|------|----------|--------|
| 层数 | 11层 + 3跨层模块 | 10层（无跨层） |
| 文件数 | 168个 | 104个 |
| 代码行数 | 58,734行 | 41,973行 |
| 复杂度 | 高 | 低 |
| 维护成本 | 高 | 低 |

---

## 三、删除/简化的层

| 原始层 | 状态 | 说明 |
|--------|------|------|
| Layer 10 主协调层 | ❌ 删除 | TradingAssistant/MainProcess/EventEngine/Workers已删除 |
| Layer 9 分析工具层 | ⚠️ 简化 | 仅保留风控核心功能 |
| Layer 8 高级分析层 | ❌ 删除 | KnowledgeAnchors/VisibilityGraph/RegimeSegmenter已删除 |
| Layer 6 进化层 | ⚠️ 简化 | 仅保留EvolutionManager核心 |
| Layer 0 数据模型层 | ⚠️ 合并 | 合并到配置层 |

---

## 四、保留的核心层

| 层级 | 名称 | 核心模块 | 功能 |
|------|------|----------|------|
| Layer 1 | 指标计算层 | indicator_engine.py | 技术指标计算 |
| Layer 2 | 基本面分析层 | news_crawler.py | 基本面数据获取 |
| Layer 3 | 推理层 | reasoner.py + debater.py | LLM推理 + 辩论验证 |
| Layer 4 | 风控层 | crowding_detector.py | 风险控制 |
| Layer 5 | 期货子系统 | provider.py | 期货数据+策略 |
| Layer 6 | 证券子系统 | provider.py | 证券数据+策略 |
| Layer 7 | 因子评估层 | factor_evaluator.py | 因子评估+进化 |
| Layer 8 | 数据层 | data_sync.py | 数据同步+存储 |
| Layer 9 | 记忆层 | experience.py | 经验记忆 |
| Layer 10 | 配置层 | trend_scanner_config.py | 系统配置 |

---

## 五、数据流

```
数据源（TqSdk/通达信MCP/AKShare）
    ↓
Layer 8: 数据层（同步+存储）
    ↓
Layer 1: 指标计算层（技术指标）
    ↓
Layer 2: 基本面分析层（基本面数据）
    ↓
Layer 5/6: 市场子系统（数据提供+市场上下文）
    ↓
Layer 9: 记忆层（经验检索）
    ↓
Layer 3: 推理层（LLM推理+辩论验证）
    ↓
Layer 4: 风控层（风险检查）
    ↓
Layer 7: 因子评估层（因子优化）
    ↓
输出：交易决策简报
```

---

*本文档反映简化后的实际架构状态。*
