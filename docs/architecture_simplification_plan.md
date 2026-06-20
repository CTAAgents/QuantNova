# QuantNova 架构简化方案

> 版本：v1.0 | 创建日期：2026-06-20
> 目标：简化架构，聚焦核心闭环

---

## 一、当前状态

| 指标 | 数值 |
|------|------|
| 总文件数 | 168个 |
| 总代码行数 | 58,734行 |
| 核心模块 | 87个文件 / 30,969行 |
| 可简化模块 | 81个文件 / 27,765行 |
| 简化比例 | 48.2% |

---

## 二、简化方案

### 保留模块（核心闭环）

| 模块 | 文件数 | 行数 | 说明 |
|------|--------|------|------|
| futures/ | 9 | 1,236 | 期货子系统 |
| securities/ | 12 | 1,450 | 证券子系统 |
| reasoning/ | 19 | 9,006 | 推理引擎（核心） |
| indicators/ | 7 | 2,660 | 指标引擎 |
| fundamental/ | 4 | 1,334 | 基本面分析 |
| risk/ | 5 | 1,331 | 风控模块 |
| core/data/ | 11 | 6,023 | 数据层 |
| core/memory/ | 13 | 5,248 | 记忆系统 |
| core/config/ | 3 | 808 | 配置 |
| core/utils/ | 4 | 1,873 | 工具函数 |
| **小计** | **87** | **30,969** | |

### 删除/简化模块

| 模块 | 文件数 | 行数 | 原因 |
|------|--------|------|------|
| rl/ | 9 | 3,678 | RL落地难，暂不使用 |
| core/nlp/ | 9 | 1,056 | 简化为意图识别 |
| evolution/ | 24 | 10,959 | 简化为因子筛选 |
| evolution_tools/ | 11 | 5,438 | 合并到evolution |
| core/event_engine/ | 4 | 513 | 事件引擎不必要 |
| core/meta/ | 3 | 1,018 | 元学习暂不需要 |
| core/risk/ | 5 | 1,585 | 已有risk模块 |
| core/trading/ | 4 | 1,398 | 交易执行暂不需要 |
| core/workers/ | 5 | 351 | Worker模式不必要 |
| strategies/ | 7 | 1,769 | 已整合到futures/securities |
| **小计** | **81** | **27,765** | |

---

## 三、简化后的架构

```
QuantNova 简化架构
├── 核心闭环（必须）
│   ├── 数据获取（futures/provider, securities/provider）
│   ├── 指标计算（indicators/）
│   ├── 基本面（fundamental/）
│   ├── 推理引擎（reasoning/reasoner）
│   ├── 辩论引擎（reasoning/debate_engine）
│   ├── 风控模块（risk/）
│   └── 记忆系统（core/memory/）
│
├── 子系统（必须）
│   ├── 期货子系统（futures/）
│   └── 证券子系统（securities/）
│
└── 基础设施（必须）
    ├── 数据层（core/data/）
    ├── 配置（core/config/）
    └── 工具（core/utils/）
```

---

## 四、执行计划

### Phase 1: 删除RL模块（可节省3,678行）

```bash
# 删除 rl/ 目录
rm -rf scripts/rl/
rm -rf tools/rl/
```

### Phase 2: 简化NLP模块（可节省约800行）

保留：
- `intent_parser.py` — 意图识别

删除：
- 其他NLP文件

### Phase 3: 简化进化模块（可节省约15,000行）

保留：
- `factor_evaluator.py` — 因子评估
- `evolution_manager.py` — 进化管理（简化版）

删除：
- 其他evolution和evolution_tools文件

### Phase 4: 删除不必要的core模块（可节省约5,000行）

删除：
- `core/event_engine/`
- `core/meta/`
- `core/risk/`（已有risk/）
- `core/trading/`
- `core/workers/`

### Phase 5: 整合strategies模块（可节省约1,700行）

将 `strategies/` 中的逻辑整合到 `futures/strategy/` 和 `securities/strategy/`

---

## 五、预期效果

| 指标 | 当前 | 简化后 | 节省 |
|------|------|--------|------|
| 文件数 | 168 | ~87 | 81 (48%) |
| 代码行数 | 58,734 | ~31,000 | 27,734 (47%) |
| 模块耦合 | 高 | 低 | - |
| 维护成本 | 高 | 低 | - |

---

## 六、风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 删除RL后无法恢复 | 中 | Git保留历史 |
| 简化过度影响功能 | 低 | 保留核心闭环 |
| 依赖关系断裂 | 低 | 逐步删除，测试验证 |

---

*本方案基于模块分析结果制定，执行前请确认。*
