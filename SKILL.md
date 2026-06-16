---
name: trend-scanner-agent
description: >
  推理重于规则的期货趋势跟踪决策辅助系统 v4.0。
  脚本+Agent 混合架构，动态因子生成，多角色协作，RL 接口自设计。
  数据源：TqSdk（首选）+ 通达信 MCP（备选）+ 本地数据库缓存。
---

# Trend Scanner Agent

推理重于规则的期货趋势跟踪决策辅助系统 v4.0。

## 核心理念

**以人为本，推理为魂，规则为果。**

所有看似"规则"的内容（止损、仓位、入场条件）均由推理层根据当前市场状态动态生成，而非事先写死。系统不自动下单，只输出决策简报供人参考。

---

## 一、系统架构

### 1.1 整体架构（八层管线）

```
定时触发 (08:40 / 15:20 / 20:40)
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  ① 数据采集层（纯 Python）                               │
│  - TqSdk 拉取所有非僵尸品种 120 日 K 线                  │
│  - 写入本地 DuckDB（data/market.duckdb）                  │
│  - 降级链：TqSdk → 通达信 MCP → 本地数据库               │
│  输出 → data/market.duckdb                               │
└───────────────────────┬─────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────┐
│  ② Scanner 脚本（纯 Python，无 LLM）                     │
│  - 从本地 DuckDB 读取 K 线                               │
│  - 计算 7 维趋势强度指标                                  │
│  - 宏观状态检测 → 动态调整策略权重                        │
│  - 信号筛选（OR/AND 可配置）                              │
│  - 仓位建议 + 止损价位 → 附加到信号输出                   │
│  输出 → data/latest_scan.json                            │
└───────────────────────┬─────────────────────────────────┘
                        │ 有信号
                        ▼
┌─────────────────────────────────────────────────────────┐
│  ③ Reasoner Agent（LLM 推理）                            │
│  - 检索相似经验（多路召回）                               │
│  - LLM 推理生成决策简报                                   │
│    市场评估 → 操作方案 → 约束建议 → 置信度                │
│  输出 → data/latest_reasoning.json                       │
└───────────────────────┬─────────────────────────────────┘
                        │ 置信度 < 0.7
                        ▼
┌─────────────────────────────────────────────────────────┐
│  ④ Debater Agent（多角色协作，FinCon 思想）               │
│  - 分析师：技术面（趋势/动量/形态）                       │
│  - 风控官：风险收益比/止损/仓位                           │
│  - 基本面研究员：供需/政策/产业链                          │
│  - 协调者：汇总分歧，修正方案                             │
│  输出 → data/latest_debate.json                          │
└───────────────────────┬─────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────┐
│  ⑤ 仓位管理（PositionSizer）                             │
│  - 凯利公式：基于胜率/盈亏比计算最优仓位                  │
│  - 自适应仓位：趋势强度 × 波动率调整                      │
│  - 金字塔加仓：盈利后逐步加仓                             │
│  输出 → 附加到决策简报                                    │
└───────────────────────┬─────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────┐
│  ⑥ 动态止损（StopLossCalculator）                        │
│  - ATR 倍数止损：基于波动率                               │
│  - 移动止损：跟踪最高/最低价                              │
│  - 多条件综合止损：取最严格条件                           │
│  输出 → 附加到决策简报                                    │
└───────────────────────┬─────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────┐
│  ⑦ Monitor 脚本（纯 Python，每 30 分钟）                  │
│  - 监控持仓风险：趋势强度下降/ER 骤降/RSI 超买           │
│  - 分级预警：HIGH / MEDIUM / LOW                         │
│  输出 → data/latest_monitor.json                         │
└───────────────────────┬─────────────────────────────────┘
                        │ 交易结束后
                        ▼
┌─────────────────────────────────────────────────────────┐
│  ⑧ Evolver Agent（LLM 引导的 RL，GIFT 思想）             │
│  - 策略健康度评估（夏普/回撤/胜率趋势）                   │
│  - 过拟合检测（蒙特卡洛/参数敏感性）                      │
│  - 轨迹分析：从交易历史提取成功/失败模式                  │
│  - RL 接口设计：LLM 设计状态空间和奖励函数                │
│  输出 → 进化报告 + 策略退休建议                           │
└─────────────────────────────────────────────────────────┘
```

### 1.2 架构总览

```
Orchestrator Agent（主协调）
  │
  ├── 数据采集层
  │     ├── TqSdk 数据源（首选）
  │     ├── 通达信 MCP（备选）
  │     └── 本地 DuckDB（缓存 + 兜底）
  │
  ├── Scanner 脚本（纯 Python）
  │     ├── 传统技术指标计算
  │     ├── 宏观状态检测（MacroStateDetector）
  │     ├── 仓位建议（PositionSizer）
  │     ├── 止损价位（StopLossCalculator）
  │     └── 动态因子生成器（LLM 引导）
  │
  ├── Reasoner Agent（LLM 推理）
  │     ├── 市场状态分析
  │     └── 知识注入（研报、经验）
  │
  ├── Debater Agent（多角色协作）
  │     ├── 分析师角色
  │     ├── 风控官角色
  │     ├── 基本面研究员角色
  │     └── 概念性语言反馈
  │
  ├── Monitor 脚本（纯 Python）
  │     └── 持仓风险监控
  │
  ├── 记忆系统
  │     ├── MemoryBridge（集成桥接器）
  │     ├── SQLite（经验/规则/日志）
  │     └── DuckDB（K线/指标/因子库）
  │
  └── Evolver Agent（LLM 引导的 RL）
        ├── 策略健康度评估（StrategyHealthChecker）
        ├── 过拟合检测（OverfittingDetector）
        ├── 轨迹感知优化器
        └── 诊断引导修正
```

### 1.3 设计原则

| 原则 | 含义 | 体现 |
|------|------|------|
| 推理重于规则 | 所有"规则"由推理层动态生成 | 不存在独立的规则层 |
| 计算用脚本，推理用 Agent | 确定性计算不调 LLM | Scanner/Monitor 是纯 Python |
| 数据本地化 | TqSdk 数据写入本地 DuckDB | 避免重复 API 调用 |
| 因子即代码 | 因子是 LLM 生成的可执行代码 | FactorEngine 思想 |
| 概念性语言反馈 | Agent 间用自然语言互相教学 | FinCon 思想 |
| RL 接口自设计 | LLM 设计状态空间和奖励函数 | GIFT 思想 |
| 仓位风控前置 | 信号输出时附带仓位和止损 | 不依赖事后推理 |

### 1.4 运行方式与 LLM 策略

**系统是自包含的**，核心功能全部在 Python 脚本中实现，不依赖任何宿主平台。

#### LLM 降级链

```
用户自定义 LLM（LLM_API_KEY）
    │
    ├── 已设置 → 使用自定义 LLM
    │
    └── 未设置
          │
          ▼
宿主平台 LLM（WORKBUDDY_API_KEY 等）
    │
    ├── 可用 → 使用宿主平台 LLM
    │
    └── 不可用
          │
          ▼
规则模式（预置因子，无需 LLM）
```

---

## 二、数据采集层

### 2.1 工作机制

```
TqSdk API → DataSourceFactory.create() → TqSdkSource.get_kline()
    │
    ▼
DuckDBStore.insert_klines()
    - 增量写入 data/market.duckdb
    - 按 (symbol, timestamp) 去重
```

### 2.2 数据源适配器

**文件**：`scripts/trend_scanner/data_source.py`

| 数据源 | 类 | 优先级 | 特点 |
|--------|-----|--------|------|
| TqSdk | `TqSdkSource` | 首选 | 期货实时行情，主力合约自动识别 |
| 通达信 MCP | `TdxSource` | 备选 | 通过 MCP 工具调用 |
| 本地 DuckDB | `LocalDBSource` | 缓存 | 离线可用 |

### 2.3 本地数据库

**文件**：`scripts/trend_scanner/memory/duckdb_store.py`

```
data/market.duckdb
  ├── klines 表（K线时序数据）
  ├── indicators 表（技术指标历史）
  └── factor_library 表（因子库）
```

---

## 三、Scanner 模块

### 3.1 工作机制

```
本地 DuckDB (klines)
    │
    ▼
IndicatorEngine.compute_all()  ← 计算 7 维趋势强度指标
    │
    ▼
MacroStateDetector.detect()  ← 宏观状态检测（新增）
    │
    ▼
信号筛选（filter_mode: or/and）
    │
    ▼
PositionSizer.calculate()  ← 仓位建议（新增）
    │
    ▼
StopLossCalculator.atr_stop()  ← 止损价位（新增）
    │
    ▼
MemoryBridge.store_scan_result()  ← 存储到记忆系统
    │
    ▼
data/latest_scan.json
```

### 3.2 技术指标（7 维）

| 指标 | 权重 | 含义 |
|------|------|------|
| TSI | 25% | 趋势强度指数 |
| ER | 25% | 效率比 |
| EMA 斜率 | 15% | 均线斜率强度 |
| ATR 比率 | 10% | 波动率比率 |
| R² | 10% | 拟合度 |
| Hurst | 8% | 赫斯特指数 |
| ADX ROC | 7% | ADX 变化率 |

### 3.3 信号输出格式（含仓位和止损）

```json
{
  "symbol": "DCE.jm2609",
  "direction": "LONG",
  "signal_strength": "STRONG",
  "trend_strength_composite": 0.72,
  "position_suggestion": {
    "method": "adaptive",
    "position_size": 0.25,
    "position_pct": "25.0%",
    "risk_metrics": {
      "max_loss_pct": "5.0%",
      "kelly_optimal": "30.0%"
    }
  },
  "stop_loss": {
    "stop_price": 1425.0,
    "atr_multiplier": 2.5,
    "risk_points": 75.0
  },
  "macro_state": {
    "cycle": {"state": "recovery", "name": "复苏"},
    "strategy_weights": {
      "trend_following": 0.4,
      "mean_reversion": 0.3
    }
  }
}
```

---

## 四、Reasoner Agent

### 4.1 工作机制

```
Scanner 信号 → 检索相似经验 → LLM 推理 → 决策简报
                                              │
                                    置信度 < 0.7 → Debater
```

### 4.2 决策简报输出格式

```json
{
  "symbol": "DCE.jm2609",
  "direction": "LONG",
  "confidence": 0.75,
  "market_assessment": {
    "trend_phase": "DEVELOPING",
    "trend_strength": "中强"
  },
  "routes": [
    {
      "name": "方案A：顺势做多",
      "entry": "当前价附近入场",
      "stop_loss": "前低下方 2ATR"
    }
  ],
  "constraints": [
    {"type": "position_size", "value": "标准仓位的 60%"}
  ]
}
```

---

## 五、Debater Agent

### 5.1 工作机制（多角色协作）

```
Reasoner 决策简报
    │
    ├── Step 1: 分析师独立分析（技术面）
    ├── Step 2: 风控官独立分析（风险）
    ├── Step 3: 基本面研究员独立分析（可选）
    ├── Step 4: 概念性语言反馈（角色间互相教学）
    └── Step 5: 协调者综合决策
    │
    ▼
data/latest_debate.json
```

### 5.2 角色定义

| 角色 | 文件 | 职责 |
|------|------|------|
| 分析师 | `agents/analyst_role.md` | 技术面分析 |
| 风控官 | `agents/risk_officer_role.md` | 风险评估 |
| 基本面研究员 | 内置于 `debater.md` | 供需分析 |
| 协调者 | 内置于 `debater.md` | 综合决策 |

---

## 六、仓位管理模块

### 6.1 工作机制

**文件**：`scripts/trend_scanner/position_sizer.py`

```
Scanner 信号（趋势强度 + 波动率）
    │
    ▼
PositionSizer.calculate()
    │
    ├── 凯利公式：f* = p - (1-p)/b
    │     - p = 胜率（默认 0.55）
    │     - b = 盈亏比（默认 1.5）
    │     - 实际使用半凯利（0.5x）降低风险
    │
    ├── 自适应仓位：
    │     - 基础仓位 = 凯利公式结果
    │     - 趋势加成 = trend_strength / 0.5（最高 1.5x）
    │     - 波动率调整 = base_vol / current_vol
    │
    └── 金字塔加仓：
          - 盈利 > 1.5 ATR 才加仓
          - 首次 50%，第二次 30%，第三次 20%
    │
    ▼
signal['position_suggestion']
```

### 6.2 核心方法

| 方法 | 参数 | 说明 |
|------|------|------|
| `kelly(win_rate, win_loss_ratio)` | 胜率/盈亏比 | 凯利公式计算最优仓位 |
| `risk_parity(volatilities)` | 波动率列表 | 风险平价权重分配 |
| `adaptive(trend_strength, volatility)` | 趋势强度/波动率 | 自适应仓位（默认） |
| `pyramid(current_position, ...)` | 当前持仓信息 | 金字塔加仓判断 |

---

## 七、动态止损模块

### 7.1 工作机制

**文件**：`scripts/trend_scanner/stop_loss.py`

```
入场价 + ATR + 方向
    │
    ▼
StopLossCalculator.multi_condition_stop()
    │
    ├── ATR 止损：entry ± ATR × 2.5
    ├── 移动止损：best_price ± ATR × 3.0（盈利时激活）
    ├── 波动率调整止损：高波动放宽，低波动收紧
    └── 时间止损：持仓超 10 天自动止损
    │
    ▼
取最严格的条件 → signal['stop_loss']
```

### 7.2 核心方法

| 方法 | 说明 |
|------|------|
| `atr_stop(entry_price, atr, direction)` | ATR 倍数止损（默认 2.5x） |
| `trailing_stop(best_price, atr, direction)` | 移动止损（跟踪最高/最低价） |
| `volatility_adjusted_stop(...)` | 波动率调整止损 |
| `time_stop(entry_time, max_holding_days)` | 时间止损（默认 10 天） |
| `multi_condition_stop(...)` | 多条件综合止损（取最严格） |

### 7.3 止损触发逻辑

```python
# 多条件综合止损
result = calculator.multi_condition_stop(
    entry_price=1500,
    current_price=1480,
    atr=30,
    direction="LONG",
    best_price=1530,
    entry_time=datetime(2026, 6, 10),
    current_vol=0.18
)
# result['triggered'] = True/False
# result['final_stop_price'] = 1425.0（最严格的止损价）
# result['risk_pct'] = 5.0（风险百分比）
```

---

## 八、策略健康度评估模块

### 8.1 工作机制

**文件**：`scripts/trend_scanner/strategy_health.py`

```
交易历史（最近 50 笔）
    │
    ▼
StrategyHealthChecker.check()
    │
    ├── 夏普比率（权重最高）
    ├── 最大回撤
    ├── 胜率趋势（最近 20 笔 vs 之前）
    ├── 连续亏损次数
    └── 盈亏比（总盈利/总亏损）
    │
    ▼
health_score = 100 - 各维度扣分
    │
    ├── 80-100：健康 → 继续运行
    ├── 60-80：亚健康 → 降低仓位至 60%
    ├── 40-60：不健康 → 暂停开新仓
    └── 0-40：严重失效 → 清仓复盘
```

### 8.2 评分规则

| 维度 | 阈值 | 扣分 |
|------|------|------|
| 夏普比率 | < 0.5 | 最多 -30 |
| 最大回撤 | > 15% | 最多 -30 |
| 胜率下降 | > 10% | 最多 -20 |
| 连续亏损 | ≥ 5 次 | 最多 -20 |
| 盈亏比 | < 1.0 | 最多 -15 |

### 8.3 策略退休判断

```python
result = checker.should_retire(trades)
# 条件（满足 2 个以上触发退休）：
# - 夏普比率 < 0.5
# - 最大回撤 > 25%
# - 健康评分 < 40
```

---

## 九、宏观状态集成模块

### 9.1 工作机制

**文件**：`scripts/trend_scanner/macro_state.py`

```
宏观指标（GDP/通胀/利率/PMI/VIX）
    │
    ▼
MacroStateDetector.detect()
    │
    ├── 经济周期：复苏/过热/滞胀/衰退
    ├── 流动性：宽松/中性/紧缩
    └── 风险偏好：risk-on/risk-off
    │
    ▼
策略权重调整
    │
    ├── 复苏期：趋势 40% / 均值回归 30% / 事件驱动 20%
    ├── 过热期：趋势 30% / 均值回归 40% / 事件驱动 20%
    ├── 滞胀期：趋势 50% / 防守 20% / 事件驱动 10%
    └── 衰退期：趋势 60% / 防守 20% / 事件驱动 10%
```

### 9.2 策略权重配置

| 经济周期 | 趋势跟踪 | 均值回归 | 事件驱动 | 防守 |
|----------|----------|----------|----------|------|
| 复苏 | 40% | 30% | 20% | 10% |
| 过热 | 30% | 40% | 20% | 10% |
| 滞胀 | 50% | 20% | 10% | 20% |
| 衰退 | 60% | 10% | 10% | 20% |

### 9.3 集成方式

宏观状态在 Scanner 阶段检测，结果附加到扫描输出：

```python
# Scanner 输出
scan_result['macro_state'] = {
    'cycle': {'state': 'recovery', 'name': '复苏'},
    'liquidity': {'state': 'loose', 'name': '宽松'},
    'risk_appetite': {'state': 'risk_on', 'name': '风险偏好'},
    'strategy_weights': {'trend_following': 0.4, ...}
}
```

---

## 十、过拟合检测模块

### 10.1 工作机制

**文件**：`scripts/trend_scanner/overfitting_detector.py`

```
交易收益序列
    │
    ▼
OverfittingDetector.comprehensive_check()
    │
    ├── 蒙特卡洛模拟（1000 次）
    │     - 打乱收益序列
    │     - 计算原始夏普的 p 值
    │     - p < 0.05 → 过拟合
    │
    ├── 夏普合理性检验
    │     - 夏普 > 3.0 且无法解释 → 99% 过拟合
    │
    └── 样本内外对比
          - 训练集 vs 测试集夏普衰减 > 50% → 过拟合
    │
    ▼
综合判断（2/3 检测到 → 高度过拟合）
```

### 10.2 检测方法

| 方法 | 原理 | 过拟合判定 |
|------|------|------------|
| 蒙特卡洛模拟 | 打乱收益序列，检查原始夏普是否异常 | p < 0.05 |
| 夏普合理性 | 经验法则：夏普 > 3 且无法解释 | 夏普 > 3.0 |
| 样本内外对比 | 训练集 vs 测试集表现差异 | 衰减 > 50% |
| 参数敏感性 | 参数微调后收益变化大 | 敏感性 > 0.5 |

### 10.3 集成方式

过拟合检测在 Evolver 阶段执行：

```python
# Evolver 输出
detector = OverfittingDetector()
result = detector.comprehensive_check(returns)
# result['verdict'] = '未检测到明显过拟合信号'
# result['risk_level'] = 'LOW'
# result['recommendation'] = '继续观察'
```

---

## 十一、Monitor 模块

### 11.1 工作机制

```
config/positions.json → 获取最新指标 → 风险检测 → 分级预警
```

### 11.2 预警分级

| 级别 | 触发条件 | 动作 |
|------|----------|------|
| HIGH | 趋势反转 / ER 骤降 / 趋势强度不足 | 立即通知 |
| MEDIUM | 盈利回撤 / RSI 超买超卖 | 关注观察 |
| LOW | 波动率扩大 / ADX 趋势减弱 | 记录备查 |

---

## 十二、Evolver Agent

### 12.1 工作机制

```
交易结果
    │
    ▼
StrategyHealthChecker.check()  ← 策略健康度评估（新增）
    │
    ▼
OverfittingDetector.comprehensive_check()  ← 过拟合检测（新增）
    │
    ▼
TrajectoryAnalyzer.analyze()  ← 轨迹分析
    │
    ▼
FailureLearner.learn()  ← 失败学习
    │
    ▼
RLInterfaceDesigner.design()  ← RL 接口设计
    │
    ▼
MemoryBridge.store_evolution_result()  ← 存储进化结果
```

### 12.2 进化触发条件

| 条件 | 阈值 | 说明 |
|------|------|------|
| 连续亏损 | ≥ 3 次 | 策略可能失效 |
| 累计亏损 | ≥ 10% | 风险失控 |
| 定期进化 | 每 20 笔交易 | 主动优化 |
| 新模式 | 检测到新模式 | 环境变化 |

### 12.3 Evolver 输出示例

```
开始进化流程...
触发原因: 连续亏损 3 次
分析样本: 25 笔交易

策略健康度: 65.0/100 (亚健康)
  - 夏普比率偏低 (0.45): -15
  - 胜率下降 (-12%): -10
  建议: 策略亚健康，建议降低仓位至 60%，密切观察

过拟合检测: 未检测到明显过拟合信号 (风险: LOW)

⚠️ 策略退休警告:
  - 夏普比率过低 (0.45)
```

---

## 十三、记忆系统

### 13.1 三层记忆架构

```
① 短期记忆（Session）→ 内存
② 工作记忆（Working）→ SQLite
③ 长期记忆（Persistent）→ SQLite + DuckDB
```

### 13.2 双存储引擎

| 引擎 | 文件 | 用途 |
|------|------|------|
| SQLite | `data/memory.db` | 经验/规则/交易日志 |
| DuckDB | `data/market.duckdb` | K线/指标/因子库 |

### 13.3 MemoryBridge（集成桥接器）

**文件**：`scripts/trend_scanner/memory_bridge.py`

| 调用方 | 方法 | 功能 |
|--------|------|------|
| Scanner | `store_scan_result()` | 存储扫描结果 |
| Reasoner | `retrieve_similar_experiences()` | 检索相似经验 |
| Reasoner | `store_reasoning_result()` | 存储推理结果 |
| Evolver | `get_trade_history()` | 获取交易历史 |
| Evolver | `store_evolution_result()` | 存储进化结果 |

---

## 十四、动态因子生成（FactorEngine）

### 14.1 工作机制

```
市场上下文 / 研报内容 → FactorGenerator.generate() → FactorValidator.validate()
    │                                                        │
    │                                               验证通过？
    │                                                  │
    ├── 是 → 存入知识库                                │
    └── 否 → LLM 修正 → 重新验证
```

### 14.2 LLM 客户端

**文件**：`scripts/trend_scanner/llm_factor_client.py`

| 提供者 | 用途 |
|--------|------|
| Auto | 自动检测（默认） |
| OpenAI 兼容 | 支持任意 OpenAI 兼容 API |
| Anthropic | Claude 系列 |
| 本地 | Ollama 等本地模型 |

---

## 十五、数据流与调度

### 15.1 完整数据流

```
TqSdk → DuckDB → Scanner（指标+宏观+仓位+止损）
    → Reasoner（LLM推理） → Debater（多角色辩论）
    → PositionSizer（仓位优化） → StopLossCalculator（止损计算）
    → Monitor（风险监控） → Evolver（健康度+过拟合+进化）
```

### 15.2 调度

| 时间 | 任务 |
|------|------|
| 08:40 | 数据同步 + 全品种扫描 |
| 15:20 | 数据同步 + 全品种扫描 + 输出总结 |
| 20:40 | 数据同步 + 全品种扫描 |
| 每 30 分钟 | 持仓监控 |
| 每 5 分钟 | 心跳检测 |

---

## 附录

### A. 目录结构

```
Trend-scanner-Agent/
├── SKILL.md
├── config/
│   ├── config.json
│   └── positions.json
├── scripts/trend_scanner/
│   ├── data_source.py          # 数据源适配器
│   ├── memory_bridge.py        # 记忆系统集成桥接器
│   ├── factor_generator.py     # 动态因子生成
│   ├── llm_factor_client.py    # LLM 客户端
│   ├── factor_validator.py     # 因子验证器
│   ├── trajectory_analyzer.py  # 轨迹感知优化器
│   ├── report_parser.py        # 研报知识注入
│   ├── conceptual_feedback.py  # 概念性语言反馈
│   ├── belief_propagation.py   # 信念传播
│   ├── rl_interface_designer.py # RL 接口设计
│   ├── position_sizer.py       # 仓位管理
│   ├── stop_loss.py            # 动态止损
│   ├── strategy_health.py      # 策略健康度评估
│   ├── macro_state.py          # 宏观状态集成
│   ├── overfitting_detector.py # 过拟合检测
│   └── memory/
│       ├── manager.py          # 统一记忆管理器
│       ├── sqlite_store.py     # SQLite 存储
│       ├── duckdb_store.py     # DuckDB 存储
│       ├── llm_factory.py      # LLM 提供者工厂
│       ├── retriever.py        # 多路召回检索器
│       └── evolution.py        # 自优化闭环
├── tools/
│   ├── scan_opportunities.py   # Scanner
│   ├── monitor_positions.py    # Monitor
│   ├── heartbeat.py            # 心跳监控
│   ├── orchestrator.py         # Orchestrator
│   ├── run_reasoner.py         # Reasoner
│   ├── run_debater.py          # Debater
│   ├── run_evolver.py          # Evolver
│   └── data_formats.py         # 数据格式定义
├── agents/
│   ├── orchestrator.md
│   ├── reasoner.md
│   ├── debater.md
│   ├── analyst_role.md
│   ├── risk_officer_role.md
│   └── evolver.md
├── tests/
├── data/
│   ├── market.duckdb
│   ├── memory.db
│   └── factor_knowledge.json
└── docs/
```

### B. 快速开始

```bash
git clone https://github.com/CTAAgents/Trend-scanner-Agent.git
cd Trend-scanner-Agent
pip install -r requirements.txt

export TQ_USER=your_username
export TQ_PASSWORD=your_password
export LLM_API_KEY=your_api_key  # 可选

python tools/scan_opportunities.py --output text --save
python tools/orchestrator.py full
```

### C. 测试覆盖

| 测试文件 | 数量 | 状态 |
|---------|------|------|
| test_factor_generator.py | 22 | ✅ |
| test_trajectory_analyzer.py | 11 | ✅ |
| test_report_parser.py | 16 | ✅ |
| test_multi_debater.py | 22 | ✅ |
| test_rl_interface.py | 15 | ✅ |
| test_e2e_pipeline.py | 14 | ✅ |
| test_full_pipeline.py | 22 | ✅ |
| test_performance.py | 20 | ✅ |
| test_memory_system.py | 12 | ✅ |
| **总计** | **162** | **全部通过** |

### D. 许可证

MIT License
