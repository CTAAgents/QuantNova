# 双子系统架构实施计划

> 版本：v1.0 | 创建日期：2026-06-18
> 状态：Phase 1 进行中

---

## 一、项目概述

### 1.1 目标

将 QuantNova 从期货专用系统升级为同时支持期货和证券（股票/ETF/可转债/REITs）的双子系统架构。

### 1.2 架构决策（经 Grill-Me 压力测试确认）

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 子系统划分 | 期货子系统 + 证券子系统 | 数据结构和策略逻辑差异大 |
| MarketContext | 期货/证券各一套 | 字段差异大，不能强制统一 |
| 因子库 | 完全独立 | 因子逻辑不同 |
| 因子进化框架 | 共用 | 算法框架通用 |
| 推理引擎 | 共用 + 独立Prompt | 框架通用，Prompt适配市场 |
| 风险监控 | 各自独立 | 不跨子系统 |
| 默认数据源 | 通达信MCP | 统一数据源 |
| 证券内部策略 | 分别实现 | 策略逻辑差异大 |
| 可转债风控 | 单独实现，关联股票 | 需要监控正股价格 |
| ETF策略 | 不做套利，只做常规交易 | 简化复杂度 |

### 1.3 范围

**期货子系统**：
- 数据源：通达信MCP
- 策略：趋势跟踪、Carry、套利
- 风控：保证金/杠杆/T+0

**证券子系统**：
- 数据源：通达信MCP
- 品种：股票、ETF、可转债、REITs
- 策略：StockStrategy、ETFStrategy、ConvertibleBondStrategy、REITsStrategy
- 风控：T+1/涨跌停/流动性

---

## 二、任务清单

### Phase 1：市场抽象层（1周）

| 任务 | 描述 | 状态 | 交付物 |
|------|------|------|--------|
| 1.1 | 创建实施计划文档 | ✅ | 本文档 |
| 1.2 | 创建设计文档 | 🔄 | docs/market_abstraction_design.md |
| 1.3 | 编写市场抽象层测试 | ⏳ | tests/test_market_abstraction.py |
| 1.4 | 实现 MarketProvider 抽象基类 | ⏳ | scripts/core/market_provider.py |
| 1.5 | 实现 BaseRiskManager 抽象基类 | ⏳ | scripts/core/base_risk_manager.py |
| 1.6 | 更新配置文件 | ⏳ | config/config.json |

### Phase 2：期货子系统迁移（1周）

| 任务 | 描述 | 状态 | 交付物 |
|------|------|------|--------|
| 2.1 | 创建期货子系统设计文档 | ⏳ | docs/futures_subsystem_design.md |
| 2.2 | 编写期货子系统测试 | ⏳ | tests/test_futures_subsystem.py |
| 2.3 | 实现 FuturesProvider | ⏳ | scripts/futures/provider.py |
| 2.4 | 实现 FuturesMarketContext | ⏳ | scripts/futures/market_context.py |
| 2.5 | 实现 FuturesFactorLibrary | ⏳ | scripts/futures/factor_library.py |
| 2.6 | 实现 FuturesRiskManager | ⏳ | scripts/futures/risk_manager.py |
| 2.7 | 迁移期货策略 | ⏳ | scripts/futures/strategy/ |

### Phase 3：证券子系统开发（2周）

| 任务 | 描述 | 状态 | 交付物 |
|------|------|------|--------|
| 3.1 | 创建证券子系统设计文档 | ⏳ | docs/securities_subsystem_design.md |
| 3.2 | 编写证券子系统测试 | ⏳ | tests/test_securities_subsystem.py |
| 3.3 | 实现 SecuritiesProvider | ⏳ | scripts/securities/provider.py |
| 3.4 | 实现 SecuritiesMarketContext | ⏳ | scripts/securities/market_context.py |
| 3.5 | 实现 SecuritiesFactorLibrary | ⏳ | scripts/securities/factor_library.py |
| 3.6 | 实现 SecuritiesRiskManager | ⏳ | scripts/securities/risk_manager.py |
| 3.7 | 实现 StockStrategy | ⏳ | scripts/securities/strategy/stock.py |
| 3.8 | 实现 ETFStrategy | ⏳ | scripts/securities/strategy/etf.py |
| 3.9 | 实现 ConvertibleBondStrategy + RiskManager | ⏳ | scripts/securities/convertible_bond/ |
| 3.10 | 实现 REITsStrategy | ⏳ | scripts/securities/strategy/reits.py |

### Phase 4：推理系统适配（1周）

| 任务 | 描述 | 状态 | 交付物 |
|------|------|------|--------|
| 4.1 | 创建期货Prompt模板 | ⏳ | scripts/reasoning/futures_prompt.py |
| 4.2 | 创建证券Prompt模板 | ⏳ | scripts/reasoning/securities_prompt.py |
| 4.3 | 更新ReasoningEngine支持Prompt路由 | ⏳ | scripts/reasoning/reasoning_engine.py |

### Phase 5：测试与集成（1周）

| 任务 | 描述 | 状态 | 交付物 |
|------|------|------|--------|
| 5.1 | 期货子系统测试 | ⏳ | tests/test_futures/ |
| 5.2 | 证券子系统测试 | ⏳ | tests/test_securities/ |
| 5.3 | 集成测试 | ⏳ | tests/test_integration_dual.py |
| 5.4 | 更新文档 | ⏳ | README.md, docs/ |

---

## 三、技术设计

### 3.1 目录结构

```
scripts/
├── core/                    # 共享核心
│   ├── market_provider.py  # MarketProvider 抽象基类
│   ├── base_risk_manager.py # BaseRiskManager 抽象基类
│   └── ...
│
├── futures/                 # 期货子系统
│   ├── __init__.py
│   ├── provider.py
│   ├── market_context.py
│   ├── factor_library.py
│   ├── risk_manager.py
│   ├── strategy/
│   │   ├── trend.py
│   │   ├── carry.py
│   │   └── arbitrage.py
│   └── fundamental.py
│
└── securities/              # 证券子系统
    ├── __init__.py
    ├── provider.py
    ├── market_context.py
    ├── factor_library.py
    ├── risk_manager.py
    ├── convertible_bond/
    │   ├── strategy.py
    │   └── risk_manager.py
    ├── strategy/
    │   ├── stock.py
    │   ├── etf.py
    │   └── reits.py
    └── fundamental.py
```

### 3.2 核心接口

详见 `docs/market_abstraction_design.md`

---

## 四、测试用例

详见 `tests/test_market_abstraction.py`

---

## 五、时间表

| 阶段 | 时间 | 交付物 | 验证指标 |
|------|------|--------|----------|
| Phase 1 | 第1周 | 市场抽象层 | 测试通过 |
| Phase 2 | 第2周 | 期货子系统 | 测试通过 |
| Phase 3 | 第3-4周 | 证券子系统 | 测试通过 |
| Phase 4 | 第5周 | 推理系统适配 | 测试通过 |
| Phase 5 | 第6周 | 测试与集成 | 全部测试通过 |

---

## 六、进度跟踪

### 2026-06-18
- [x] 完成 Grill-Me 架构压力测试
- [x] 确认所有架构决策
- [x] 创建实施计划文档
- [ ] 创建设计文档
- [ ] 编写测试用例

---

*本文档由 WorkBuddy 于 2026-06-18 创建*
