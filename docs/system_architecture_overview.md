# QuantNova 系统架构总览

> 版本：v2.1.0 | 创建日期：2026-06-20 | 简化版
> 状态：双子系统架构（期货+证券），已简化

---

## 一、系统概述

QuantNova 是一个推理重于规则的量化交易决策辅助系统，支持期货和证券双市场。

**核心理念**：以人为本，推理为魂，规则为果。

**架构特点**：
- 双子系统分离：期货子系统 + 证券子系统
- 共享核心模块：推理引擎、因子评估、记忆系统
- 核心闭环：扫描→推理→辩论→风控

---

## 二、简化后架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                    QuantNova 简化架构 (v2.1.0)                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    共享核心模块                               │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │   │
│  │  │ 推理引擎     │  │ 因子评估     │  │ 记忆系统    │         │   │
│  │  │ reasoning/  │  │ evolution/  │  │ core/memory │         │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘         │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                    │                                │
│  ┌─────────────────────────────────┴─────────────────────────────┐ │
│  │                    市场抽象层                                   │ │
│  │  MarketProvider (抽象基类) │ BaseRiskManager (抽象基类)        │ │
│  └─────────────────────────────────┬─────────────────────────────┘ │
│                                    │                                │
│          ┌─────────────────────────┴─────────────────────────┐     │
│          │                                                     │     │
│  ┌───────┴───────────────────┐   ┌───────────────────────────┴──┐ │
│  │    期货子系统              │   │     证券子系统                 │ │
│  │  • FuturesProvider        │   │  • SecuritiesProvider         │ │
│  │  • TqSdk/通达信MCP        │   │  • 通达信MCP/NeoData          │ │
│  │  • 期货策略               │   │  • 证券策略                   │ │
│  └───────────────────────────┘   └──────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 三、模块清单（简化后）

### 核心模块（保留）

| 模块 | 文件数 | 说明 |
|------|--------|------|
| futures/ | 7 | 期货子系统（Provider+Strategy） |
| securities/ | 9 | 证券子系统（Provider+Strategy） |
| reasoning/ | 18 | 推理引擎+辩论引擎 |
| indicators/ | 6 | 指标计算 |
| fundamental/ | 3 | 基本面分析 |
| risk/ | 4 | 风控模块 |
| core/data/ | 10 | 数据层 |
| core/memory/ | 12 | 记忆系统 |
| core/config/ | 2 | 配置 |
| core/utils/ | 4 | 工具函数 |
| evolution/ | 4 | 因子评估（简化） |
| evolution_tools/ | 3 | 进化工具（简化） |

### 已删除模块

| 模块 | 原因 |
|------|------|
| rl/ | RL落地难，暂不使用 |
| core/nlp/ | 简化为意图识别（保留1个文件） |
| core/event_engine/ | 不必要 |
| core/meta/ | 暂不需要 |
| core/risk/ | 已有risk模块 |
| core/trading/ | 暂不需要 |
| core/workers/ | 不必要 |
| strategies/ | 已整合到子系统 |

---

## 四、数据源体系

| 市场 | 首选 | 第二 | 第三 |
|------|------|------|------|
| 期货K线 | TqSdk | 通达信MCP | - |
| 期货库存 | AKShare | - | - |
| 证券行情 | 通达信MCP | NeoData | WeStock |
| 宏观数据 | 通达信MCP | AKShare | - |
| 研报数据 | 通达信MCP | - | - |

---

## 五、核心工作流程

```
1. 数据获取
   ↓
2. 指标计算
   ↓
3. 信号生成（自优化参数）
   ↓
4. 辩论验证（鹰鸽对抗）
   ↓
5. 风控检查
   ↓
6. 输出建议
```

---

*本架构已简化，聚焦核心闭环。*

│  │  │ • 保证金/杠杆       │  │   │  │ • T+1交割           │    │ │
│  │  │ • T+0日内           │  │   │  │ • 涨跌停板          │    │ │
│  │  │ • 交割月管理        │  │   │  │ • 流动性风险        │    │ │
│  │  └─────────────────────┘  │   │  └─────────────────────┘    │ │
│  │                           │   │                              │ │
│  │  ┌─────────────────────┐  │   │  ┌─────────────────────┐    │ │
│  │  │ 期货策略            │  │   │  │ 证券策略            │    │ │
│  │  │ • 趋势跟踪          │  │   │  │ • StockStrategy     │    │ │
│  │  │ • Carry策略          │  │   │  │ • ETFStrategy       │    │ │
│  │  │ • 套利策略          │  │   │  │ • ConvertBondStrat  │    │ │
│  │  └─────────────────────┘  │   │  │ • REITsStrategy     │    │ │
│  │                           │   │  └─────────────────────┘    │ │
│  │  ┌─────────────────────┐  │   │  ┌─────────────────────┐    │ │
│  │  │ 期货Prompt          │  │   │  │ 证券Prompt          │    │ │
│  │  │ • T+0逻辑           │  │   │  │ • T+1逻辑           │    │ │
│  │  │ • 杠杆思维          │  │   │  │ • 估值思维          │    │ │
│  │  │ • 基差/库存分析     │  │   │  │ • 财务/股东分析     │    │ │
│  │  └─────────────────────┘  │   │  └─────────────────────┘    │ │
│  │                           │   │                              │ │
│  └───────────────────────────┘   └──────────────────────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 三、核心工作流

### 3.1 期货市场分析工作流

```
用户请求（期货品种）
    ↓
PromptRouter.get_prompt("futures") → 获取期货Prompt
    ↓
FuturesProvider.get_kline() → 获取K线数据
    ↓
FuturesFactorLibrary.calculate_*() → 计算因子
    ↓
FuturesMarketContext → 组装市场上下文
    ↓
ReasoningEngine.reason() → LLM推理（期货Prompt）
    ↓
FuturesRiskManager.calculate_*() → 风险管理
    ↓
输出决策简报
```

### 3.2 证券市场分析工作流

```
用户请求（证券品种）
    ↓
PromptRouter.get_prompt("securities") → 获取证券Prompt
    ↓
SecuritiesProvider.get_kline() → 获取K线数据
    ↓
SecuritiesFactorLibrary.calculate_*() → 计算因子
    ↓
SecuritiesMarketContext → 组装市场上下文
    ↓
ReasoningEngine.reason() → LLM推理（证券Prompt）
    ↓
SecuritiesRiskManager.calculate_*() → 风险管理
    ↓
输出决策简报
```

---

## 四、数据流

### 4.1 数据获取

```
通达信MCP → FuturesProvider / SecuritiesProvider
    ↓
K线数据 + 基本面数据
    ↓
MarketContext（期货/证券各自的数据模型）
```

### 4.2 因子计算

```
MarketContext → FactorLibrary（完全独立）
    ↓
期货因子：基差、库存、持仓量、期限结构
证券因子：估值、质量、情绪、动量
    ↓
因子得分
```

### 4.3 风险管理

```
MarketContext + FactorScores → RiskManager（各自独立）
    ↓
期货风控：保证金/杠杆/T+0
证券风控：T+1/涨跌停/流动性
    ↓
风险指标 + 止损止盈
```

---

## 五、模块清单

### 5.1 共享核心模块

| 模块 | 路径 | 功能 |
|------|------|------|
| MarketProvider | `scripts/core/market_provider.py` | 市场数据提供者抽象基类 |
| BaseRiskManager | `scripts/core/base_risk_manager.py` | 风险管理器抽象基类 |
| ModuleRegistry | `scripts/core/module_registry.py` | 模块注册中心 |
| ReasoningEngine | `scripts/reasoning/reasoning_engine.py` | 推理引擎 |
| PromptRouter | `scripts/reasoning/prompt_router.py` | Prompt路由器 |

### 5.2 期货子系统

| 模块 | 路径 | 功能 |
|------|------|------|
| FuturesProvider | `scripts/futures/provider.py` | 期货数据提供者 |
| FuturesMarketContext | `scripts/futures/market_context.py` | 期货市场上下文 |
| FuturesFactorLibrary | `scripts/futures/factor_library.py` | 期货因子库 |
| FuturesRiskManager | `scripts/futures/risk_manager.py` | 期货风控 |
| TrendStrategy | `scripts/futures/strategy/trend.py` | 趋势策略 |
| CarryStrategy | `scripts/futures/strategy/carry.py` | Carry策略 |
| ArbitrageStrategy | `scripts/futures/strategy/arbitrage.py` | 套利策略 |
| FuturesPrompt | `scripts/reasoning/futures_prompt.py` | 期货Prompt |

### 5.3 证券子系统

| 模块 | 路径 | 功能 |
|------|------|------|
| SecuritiesProvider | `scripts/securities/provider.py` | 证券数据提供者 |
| SecuritiesMarketContext | `scripts/securities/market_context.py` | 证券市场上下文 |
| SecuritiesFactorLibrary | `scripts/securities/factor_library.py` | 证券因子库 |
| SecuritiesRiskManager | `scripts/securities/risk_manager.py` | 证券风控 |
| StockStrategy | `scripts/securities/strategy/stock.py` | 股票策略 |
| ETFStrategy | `scripts/securities/strategy/etf.py` | ETF策略 |
| REITsStrategy | `scripts/securities/strategy/reits.py` | REITs策略 |
| ConvertibleBondStrategy | `scripts/securities/convertible_bond/strategy.py` | 可转债策略 |
| ConvertibleBondRiskManager | `scripts/securities/convertible_bond/risk_manager.py` | 可转债风控 |
| SecuritiesPrompt | `scripts/reasoning/securities_prompt.py` | 证券Prompt |

---

## 六、技术栈

| 组件 | 技术 |
|------|------|
| 数据源 | 通达信MCP（默认） |
| 推理引擎 | LLM + Prompt模板 |
| 因子计算 | Python + NumPy + Pandas |
| 风险管理 | Python + 自研算法 |
| 测试框架 | pytest |

---

## 七、配置管理

```json
{
  "market_type": "futures",
  "active_subsystem": "futures",
  "data_source": "tdx_mcp",
  "subsystems": {
    "futures": {
      "margin_rate": 0.1,
      "leverage": 10
    },
    "securities": {
      "t_plus_1": true,
      "limit_up_pct": 0.1
    }
  }
}
```

---

*本文档由 WorkBuddy 于 2026-06-18 创建*
