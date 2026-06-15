---
name: reasoner
description: "期货趋势跟踪推理 Agent —— 接收市场信号，生成交易决策简报"
version: "1.0.0"
author: "Trend-scanner-Agent"
created: "2026-06-15"
tags: ["trading", "futures", "reasoning", "agent"]
---

# Reasoner Agent（推理器）

## 概述

Reasoner Agent 是 Trend-scanner-Agent 系统的核心推理组件。它接收 Scanner 脚本或 Monitor 脚本的信号，通过 LLM 推理生成交易决策简报。

## 核心理念

**推理是一切的上游，规则只是推理的临时产物。**

所有约束（止损、仓位、入场条件）均由推理层根据当前市场状态和历史经验实时推导，而非事先写死。

## 职责

1. **接收信号**：从 Scanner 脚本或 Monitor 脚本接收市场信号
2. **经验检索**：从经验记忆池中检索相似历史经验
3. **LLM 推理**：调用 LLM 进行深度推理
4. **生成简报**：输出结构化的交易决策简报

## 输入格式

```json
{
  "symbol": "DCE.jm2609",
  "direction": "LONG",
  "trend_phase": "DEVELOPING",
  "trend_strength_composite": 0.72,
  "tsi": 25.3,
  "er": 0.65,
  "r_squared": 0.68,
  "key_signals": ["ER>0.6", "TSI>20", "均线多头排列"],
  "risk_factors": ["RSI接近超买", "波动率扩张"],
  "scan_id": "scan_20260615_103000"
}
```

## 输出格式

```json
{
  "symbol": "DCE.jm2609",
  "timestamp": "2026-06-15T10:30:05",
  "trend_phase": {
    "phase": "DEVELOPING",
    "label": "趋势发展",
    "confidence": 0.75
  },
  "assessment": {
    "summary": "焦煤处于趋势发展阶段，均线多头排列，动量充足",
    "signal_hint": "趋势确认，可考虑顺势入场"
  },
  "routes": [
    {
      "route_id": "A",
      "name": "顺势做多",
      "action": "在回调至支撑位时入场做多",
      "confidence": 0.72,
      "reasoning": "趋势发展阶段，动量充足，均线支撑",
      "constraints": [
        {"type": "stop_loss", "value": 1320, "reason": "ATR 止损"},
        {"type": "position_size", "value": 0.3, "reason": "中等仓位"}
      ],
      "risks": ["RSI 接近超买", "波动率扩张"]
    },
    {
      "route_id": "B",
      "name": "观望等待",
      "action": "等待更明确的信号或回调机会",
      "confidence": 0.28,
      "reasoning": "RSI 超买风险，等待回调",
      "constraints": [],
      "risks": ["可能错过趋势行情"]
    }
  ],
  "recommended_route": "A",
  "uncertainty": {
    "level": "MEDIUM",
    "factors": ["RSI 超买", "波动率扩张"]
  },
  "warnings": [],
  "reasoning_model": "WorkBuddy Agent (default)",
  "experience_count": 3,
  "generation_time_ms": 1200
}
```

## 工作流程

```
接收信号
  │
  ▼
解析信号摘要
  │
  ▼
读取完整 MarketContext（从 latest_scan.json）
  │
  ▼
检索相似经验（从经验记忆池）
  │
  ▼
构建推理提示词
  │
  ▼
调用 LLM 推理
  │
  ▼
解析 LLM 输出
  │
  ▼
生成交易决策简报
  │
  ▼
输出简报（JSON 格式）
```

## 触发条件

- **Scanner 信号**：中信号（置信度 0.7-0.85）或强信号（置信度 > 0.85）
- **Monitor 预警**：HIGH 级别预警
- **用户指令**：用户显式要求分析某个品种

## 配置参数

```json
{
  "reasoner": {
    "llm_type": "workbuddy_agent",
    "debate_trigger_confidence": 0.7,
    "max_tokens_per_day": 500000,
    "experience_top_k": 5,
    "experience_similarity_threshold": 0.6
  }
}
```

## 使用方式

### 作为 WorkBuddy Agent

```python
# 通过 WorkBuddy Agent 系统调用
from tools.reasoner import ReasonerAgent

agent = ReasonerAgent()
result = agent.analyze(signal_data)
print(result)
```

### 作为独立脚本

```bash
# 分析单个品种
python tools/reasoner.py --symbol DCE.jm2609 --direction LONG

# 分析信号文件
python tools/reasoner.py --signal data/latest_scan.json
```

## 依赖模块

- `scripts/trend_scanner/reasoning.py` - 推理引擎
- `scripts/trend_scanner/brief.py` - 简报生成器
- `scripts/trend_scanner/experience.py` - 经验记忆池
- `scripts/trend_scanner/context.py` - 上下文组装
- `scripts/trend_scanner/models.py` - 数据模型

## 错误处理

- **LLM 调用失败**：使用规则退化，生成基本建议
- **经验检索失败**：使用空经验列表，降低置信度
- **数据不足**：返回 DATA_INSUFFICIENT 状态

## Token 预算

- 每次推理消耗约 2000-5000 token
- 每日预算 500K token（约 100-250 次推理）
- 达到预算 80% 时停止 Debater Agent

## 监控指标

- 推理成功率
- 平均推理时间
- Token 消耗量
- 置信度分布
- 推荐路线准确率
