---
name: trend-scanner-agent
description: >
  推理重于规则的期货趋势跟踪决策辅助系统。
  Davey框架补充（蒙特卡洛+策略孵化+熔断+组合管理） + 
  FinClaw整合 + 统一数据路由 + 知识锚点 + 分级输出 + 套利分析 + 
  Reasoner Agent 深度分析 + 持仓健康度评估 + 闭环迭代因子进化引擎，
  每日自动扫描 86 个主力合约，筛选非僵尸品种（持仓量≥10000），
  数据源：TqSdk（首选）+ Pytdx（备选）+ AkShare（基差/季节性/龙虎榜）+ 本地数据库缓存。
---

# Trend Scanner Agent

> 完整文档请查看 [README.md](README.md)

## 快速开始

```bash
# 数据同步
python tools/sync_data.py sync --days 120

# 运行扫描
python tools/scan_opportunities.py --output text --save

# Reasoner深度分析（推荐）
python tools/scan_opportunities.py --reasoner --output text --save

# 持仓健康度评估
python tools/scan_opportunities.py --position-health

# 因子评估
python tools/scan_opportunities.py --evaluate-factors

# 因子进化
python tools/scan_opportunities.py --evolve --evolve-rounds 5
```

## 核心能力

| 能力 | 命令 | 来源 |
|------|------|------|
| 全品种扫描 | `--output text --save` | 核心 |
| **五维度筛选评分** | `--use-multi-dimension` | 核心 |
| **Reasoner深度分析** | `--reasoner --output text --save` | 核心 |
| **持仓健康度评估** | `--position-health` | 核心 |
| **蒙特卡洛模拟** | 内置（自动触发） | Davey Step 5 |
| **策略孵化** | 内置（自动触发） | Davey Step 6 |
| **停止交易阈值** | 内置（自动触发） | Davey Step 7 |
| **多策略组合** | 内置（自动触发） | Davey Step 7 |
| 因子评估 | `--evaluate-factors` | 因子进化 |
| 因子进化 | `--evolve` | 因子进化 |
| 参数优化 | `--optimize-params` | 因子进化 |
| 策略健康检查 | `--health-check` | 分析工具 |
| 过拟合检测 | `--overfitting-check` | 分析工具 |

## Davey 框架模块（新增）

基于 Kevin J. Davey《构建盈利的算法交易系统》补充的4个风控模块：

| 模块 | 文件 | 功能 |
|------|------|------|
| 蒙特卡洛模拟 | `monte_carlo.py` | 交易重排→破产概率/置信区间/最差情景 |
| 策略孵化 | `strategy_incubator.py` | 实盘数据验证3-6个月，对比回测预期 |
| 停止交易阈值 | `circuit_breaker.py` | 策略级熔断（最大亏损/回撤/连续亏损） |
| 多策略组合 | `strategy_portfolio.py` | 策略权重优化/相关性控制/分散化 |

## 触发词

趋势扫描、期货扫描、因子评估、因子进化、参数优化、持仓健康度、Reasoner分析、蒙特卡洛、策略孵化、熔断、组合管理

---

**完整文档：[README.md](README.md)**
