---
title: "Trend Scanner Agent Definition"
summary: "趋势跟踪 Agent 的能力和工具定义"
---

# Agent.md - 趋势跟踪 Agent

## 定位

推理重于规则的期货趋势跟踪决策辅助系统。

系统不进行自动下单，只提供态势研判、风险提示与操作建议。

## 架构

```
Orchestrator Agent（主协调）
  ├── Scanner 脚本（纯 Python）→ 条件触发 Reasoner
  ├── Reasoner Agent（LLM 推理）→ 生成决策简报
  ├── Debater Agent（self-debate）→ 修正方案
  ├── Monitor 脚本（纯 Python）→ 条件触发预警
  └── Evolver Agent（LLM 反思）→ 优化策略
```

## 能力

### 1. 趋势扫描（Scanner）
- 扫描期货全品种（17+ 品种）
- 计算 7 维趋势强度指标（ER/R²/Hurst/ADX ROC/TSI/EMA斜率/ATR比率）
- 筛选有信号的品种
- 输出结构化 JSON 信号

### 2. 智能推理（Reasoner）
- 接收 Scanner 信号
- 检索历史经验
- LLM 推理生成交易决策简报
- 输出市场评估 + 操作方案 + 动态约束

### 3. 辩论修正（Debater）
- 对 Reasoner 输出进行 self-debate
- 鹰派/鸽派对抗性推理
- 修正置信度和方案
- 输出分歧度和修正理由

### 4. 持仓监控（Monitor）
- 读取持仓数据
- 计算持仓品种风险指标
- 检测趋势反转信号
- 分级预警（LOW/MEDIUM/HIGH）

### 5. 经验进化（Evolver）
- 记录交易反馈
- 分析交易轨迹
- 归因故障原因
- 优化策略参数

## 工具

| 工具 | 用途 | 脚本 |
|------|------|------|
| Scanner | 全品种扫描 | tools/scan_opportunities.py |
| Heartbeat | 心跳监控 | tools/heartbeat.py |
| Monitor | 持仓分析 | tools/monitor_positions.py |
| Reasoner | LLM 推理 | tools/run_reasoner.py |
| Debater | 辩论修正 | tools/run_debater.py |
| Evolver | 经验进化 | tools/run_evolver.py |
| Orchestrator | 主协调 | tools/orchestrator.py |
| Positions | 持仓管理 | tools/positions_manager.py |
| TokenBudget | Token 预算 | tools/token_budget.py |
| HealthCheck | 健康检查 | tools/health_check.py |
| Logger | 统一日志 | tools/logger.py |

## 数据源

- **首选**：TqSdk（期货实时行情、主力合约）
- **备选**：通达信 MCP（A股/港股/美股/期货）
- **兜底**：本地 CSV

## 配置

所有参数存放在 `config/config.json`，用户可在对话中动态调整。

## 调度

| 类型 | 时间 | 说明 |
|------|------|------|
| Cron | 08:40 | 盘前准备 |
| Cron | 15:20 | 日盘收盘 |
| Cron | 20:40 | 夜盘开盘 |
| 心跳 | 每 5 分钟 | 交易时段监控 |

## Token 预算

- 每日预算：850,000 token
- 三级降级：80% 停止 Debater，90% 只保留 Scanner，100% 停止所有

## 与 v1 Skill 的关系

- **共享模块**：`scripts/trend_scanner/` 是核心计算包，v1 和 v2 共用
- **v1 保留**：原 Skill 继续可用，作为回退方案
- **v2 增量**：Agent 层是新增的调度层，不影响 v1 代码
