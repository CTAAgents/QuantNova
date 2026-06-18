# Changelog

> 版本号管理遵循 [VERSION_MANAGEMENT.md](VERSION_MANAGEMENT.md)
> 版本号唯一定义位置：`scripts/core/__version__.py`

---

## v2.0.0 (2026-06-18)

**双子系统版 — 期货+证券双市场支持**

### 里程碑

- 双子系统架构完成（期货子系统 + 证券子系统）
- 60+ 个模块注册到模块注册中心
- 659+ 单元测试全部通过
- 5个Phase实施完成（市场抽象层→期货迁移→证券开发→推理适配→测试集成）

### 新增

- **双子系统架构**
  - `scripts/futures/` - 期货子系统（Provider/MarketContext/FactorLibrary/RiskManager/Strategy）
  - `scripts/securities/` - 证券子系统（Provider/MarketContext/FactorLibrary/RiskManager/Strategy）
  - `scripts/core/market_provider.py` - MarketProvider 抽象基类
  - `scripts/core/base_risk_manager.py` - BaseRiskManager 抽象基类

- **证券子系统**
  - `StockStrategy` - 股票策略（价值/成长/动量）
  - `ETFStrategy` - ETF策略（趋势跟踪，不做套利）
  - `ConvertibleBondStrategy` - 可转债策略（双低策略）
  - `REITsStrategy` - REITs策略（分红收益率）
  - `ConvertibleBondRiskManager` - 可转债风控（关联正股）

- **推理系统适配**
  - `scripts/reasoning/futures_prompt.py` - 期货Prompt模板
  - `scripts/reasoning/securities_prompt.py` - 证券Prompt模板
  - `scripts/reasoning/prompt_router.py` - Prompt路由器

- **模块注册中心增强**
  - 新增60+个模块注册
  - 核心模块：TradingAssistant, ContextAssembler, MainProcess
  - 推理引擎：ReasoningEngine, DebateReasoningEngine, ScenarioAnalyzer, BriefGenerator
  - 进化模块：FactorExecutor, FactorGate, FactorValidator等
  - 工具模块：Backtest, MonteCarlo, ScenarioAnalyzerTool等

### 变更

- 系统名称统一为 QuantNova
- 版本号升级为 v2.0.0
- 数据源配置：期货=TqSdk（首选），证券=通达信MCP（首选）
- README.md 更新为双子系统架构描述
- 系统架构文档重写为双子系统架构

---

## v1.0.0 (2026-06-18)

**正式版 — 推理重于规则的期货趋势跟踪决策辅助系统**

### 里程碑

- 系统架构梳理完成，11层架构（Layer 0-10）
- 122个 Python 模块
- 544+ 单元测试
- 60个监控品种
- 5篇论文思想完整实现
- 本地部署方案完成，支持开机自启动
- AI编码行为准则标准化（CLAUDE.md）

### 新增

- **本地部署方案**
  - `start.bat` - 快速启动脚本
  - `service.bat` - 服务管理器
  - `monitor.bat` - 状态监控面板
  - `install_startup.bat` - 安装开机自启动
  - `DEPLOY.md` - 完整部署指南

- **文档体系**
  - `CLAUDE.md` - AI编码行为准则（项目标准）
  - `docs/CONTRIBUTING.md` - 开发规范
  - `docs/paper_implementation_guide.md` - 论文实现映射
  - `docs/architecture_diagram.svg` - 11层架构图

### 变更

- 系统名称统一为 QuantNova
- 版本号重置为 v1.0.0（遵循语义化版本号规范）

---

## v0.1.0 (2026-06-17)

**新架构版 — FinClaw整合 + 统一数据路由 + 知识锚点 + 分级输出 + 套利分析**

### 新增

- **统一数据路由层** (`unified_data_router.py`)
  - 9种数据类型智能路由（K线/行情/基差/季节性/仓单/龙虎榜/保证金/宏观/交割）
  - 自动Fallback机制（DuckDB → TqSdk → Pytdx → AkShare → CSV）
  - 配置驱动路由优先级（`config.json data_routing`段）
  - 数据时效性检查（fresh/stale/critical三级）
  - 远程数据自动回写本地DuckDB

- **知识锚点体系** (`knowledge_anchors.py`)
  - 13个默认锚点覆盖6个维度（momentum/trend/volatility/volume/basis/seasonality）
  - 为LLM因子生成提供种子+验证规则
  - SQLite持久化存储

- **分级输出机制** (`tiered_output.py`)
  - formal/standard/brief三级输出
  - JSON格式支持API/前端消费
  - 集成到Reasoner Agent

- **套利分析模块** (`arbitrage_analyzer.py`)
  - 12个预定义价差对（跨期+跨品种）
  - Z-Score信号 + 协整检验
  - 价差百分位分析

- **数据源扩展**
  - PytdxSource：通达信Python直连（pytdx库）
  - AkShareSource：基差/季节性/龙虎榜/保证金/宏观数据

- **分析维度补充**
  - 龙虎榜（多空持仓排名）
  - 保证金（交易所/经纪商比例）
  - 宏观经济（GDP/CPI/PMI + 品种关联）
  - 交割数据（交割月/仓单/距交割天数）

### 改进

- **孤立模块集成**：6个模块接入核心系统
  - knowledge_anchors → reasoning.py（知识锚点注入推理prompt）
  - tiered_output → reasoner.py（分级输出）
  - arbitrage_analyzer → scan_opportunities.py（--arbitrage参数）
  - belief_propagation → debater.py（信念传播）
  - conceptual_feedback → debater.py（概念性反馈）
  - rl_interface_designer → evolver.py（RL接口诊断）

- **版本管理**
  - 版本号重置为v0.1.0（开发阶段）
  - 消除所有文件中的版本号硬编码
  - 单一来源原则：`__version__.py`为唯一定义位置
  - 新增版本号管理规范文档

### 修复

- **AkShare API调用**
  - get_basis(): 使用`futures_spot_price()`获取基差数据
  - get_margin(): 使用`futures_fees_info()`获取保证金和手续费
  - get_macro(): 修复CPI/PMI数据解析，添加品种-宏观关联映射

### 测试

- 总计475个测试全部通过
- 新增111个测试（unified_data_router=76, phase3_4_5=35）

---

## 前序版本（v1.0 ~ v6.0）

> 版本号已合并精简，详见`scripts/trend_scanner/__version__.py`中的VERSION_HISTORY

| 版本 | 日期 | 关键变更 |
|------|------|---------|
| v6.0.0 | 2026-06-16 | Reasoner Agent深度分析 + 持仓健康度评估 |
| v5.0.0 | 2026-06-16 | 闭环迭代因子进化引擎 |
| v3.2.x | 2026-06-14 | 五路径框架 + 控制变量隔离 |
| v3.0.0 | 2026-06-14 | 推理优先架构重写 |
| v2.0.0 | 2026-06-01 | 自适应系统 |
| v1.0.0 | 2026-05-15 | 初始版本 |

---

*本文件记录 QuantNova 项目的变更历史。*
