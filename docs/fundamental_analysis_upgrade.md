# 基本面分析模块升级方案

> 版本：v1.0 | 创建日期：2026-06-18
> 状态：待确认

## 一、项目概述

### 1.1 目标
为系统增加基本面分析能力，解决当前纯技术面分析的局限性，实现：
- 实时新闻和事件追踪
- 供需数据获取和分析
- 地缘政治风险评估
- 产业链数据整合

### 1.2 背景
当前系统是纯技术面分析系统，缺乏基本面数据获取和分析能力。这导致：
- 无法解释市场现象的根本原因（如能化板块偏弱）
- 无法捕捉重大事件对市场的影响（如美伊协议达成）
- 无法进行供需分析

### 1.3 范围
- 新闻抓取模块
- 供需数据接口
- 地缘政治事件追踪
- MarketContext扩展
- 推理层增强

## 二、任务清单

| 任务 | 描述 | 状态 | 交付物 |
|------|------|------|--------|
| 1. 设计基本面数据模型 | 定义基本面数据结构和存储方式 | 待开始 | models/fundamental.py |
| 2. 新闻抓取模块 | 实现财经新闻、政策公告抓取 | 待开始 | scripts/fundamental/news_crawler.py |
| 3. 供需数据接口 | 对接库存、产量、开工率数据 | 待开始 | scripts/fundamental/supply_demand.py |
| 4. 地缘政治事件追踪 | 实现地缘政治风险评估 | 待开始 | scripts/fundamental/geopolitical.py |
| 5. MarketContext扩展 | 在上下文中增加基本面维度 | 待开始 | scripts/trend_scanner/context.py |
| 6. 推理层增强 | 推理前自动搜索相关新闻 | 待开始 | scripts/trend_scanner/reasoning.py |
| 7. 测试用例 | 编写单元测试和集成测试 | 待开始 | tests/test_fundamental.py |

## 三、技术设计

### 3.1 基本面数据模型

```python
class FundamentalData:
    """基本面数据基类"""
    symbol: str
    timestamp: datetime
    source: str
    confidence: float

class NewsEvent(FundamentalData):
    """新闻事件"""
    title: str
    content: str
    category: str  # policy/geopolitical/industry/company
    impact: str    # positive/negative/neutral
    keywords: list[str]

class SupplyDemandData(FundamentalData):
    """供需数据"""
    inventory: float      # 库存
    production: float     # 产量
    consumption: float    # 消费量
    capacity_utilization: float  # 产能利用率
    import_volume: float  # 进口量
    export_volume: float  # 出口量

class GeopoliticalRisk(FundamentalData):
    """地缘政治风险"""
    region: str           # 地区
    risk_type: str        # war/sanctions/tariffs/dispute
    risk_level: str       # high/medium/low
    affected_commodities: list[str]  # 受影响的商品
    description: str
```

### 3.2 新闻抓取模块

**数据源优先级：**
1. 财新网（权威财经新闻）
2. 新浪财经（实时行情和新闻）
3. 央广网（政策解读）
4. 东方财富（行业新闻）
5. 雪球（市场情绪）

**抓取策略：**
- 关键词过滤：品种名称、行业术语、政策关键词
- 频率控制：每小时抓取一次
- 去重机制：基于标题相似度去重
- 优先级排序：根据新闻来源和内容重要性

### 3.3 供需数据接口

**数据源：**
1. Wind（专业金融数据）
2. 东方财富（免费数据）
3. 各行业协会官网
4. 海关总署（进出口数据）

**数据类型：**
- 库存数据：交易所库存、社会库存
- 产量数据：月度产量、开工率
- 消费数据：表观消费量
- 进出口数据：海关统计

### 3.4 地缘政治事件追踪

**风险类型：**
- 战争/冲突（如美伊关系）
- 制裁（如对俄制裁）
- 关税（如中美贸易战）
- 领土争端（如南海问题）

**评估指标：**
- 风险等级：高/中/低
- 影响范围：全球/区域/国家
- 持续时间：短期/中期/长期
- 影响商品：能源/金属/农产品

### 3.5 MarketContext扩展

```python
class MarketContext:
    # 现有字段...
    
    # 新增基本面维度
    fundamental: FundamentalContext

class FundamentalContext:
    """基本面上下文"""
    news_events: list[NewsEvent]           # 近期新闻事件
    supply_demand: SupplyDemandData        # 供需数据
    geopolitical_risks: list[GeopoliticalRisk]  # 地缘政治风险
    policy_impact: PolicyImpact            # 政策影响
    industry_chain: IndustryChainData      # 产业链数据
```

### 3.6 推理层增强

**推理前信息收集流程：**

```python
def reason(self, context, ...):
    # 1. 获取市场上下文（现有）
    # 2. 搜索相关新闻（新增）
    news_events = self._search_news(context.symbol)
    # 3. 检查地缘政治风险（新增）
    geopolitical_risks = self._check_geopolitical_risks(context.symbol)
    # 4. 获取供需数据（新增）
    supply_demand = self._get_supply_demand(context.symbol)
    # 5. 组装基本面上下文（新增）
    fundamental_context = self._assemble_fundamental_context(
        news_events, geopolitical_risks, supply_demand
    )
    # 6. 合并到MarketContext（新增）
    context.fundamental = fundamental_context
    # 7. 构建推理提示词（增强）
    # 8. 调用LLM推理（现有）
    # 9. 生成交易决策简报（现有）
```

## 四、测试用例

| 测试场景 | 输入 | 预期输出 | 状态 |
|----------|------|----------|------|
| 新闻抓取测试 | 品种代码 | 新闻列表 | 待编写 |
| 供需数据测试 | 品种代码 | 供需数据 | 待编写 |
| 地缘政治风险测试 | 地区代码 | 风险评估 | 待编写 |
| 上下文组装测试 | K线数据+基本面数据 | 完整MarketContext | 待编写 |
| 推理增强测试 | 完整MarketContext | 交易决策简报 | 待编写 |

## 五、时间表

| 阶段 | 时间 | 交付物 | 验证指标 |
|------|------|--------|----------|
| Phase 1: 数据模型设计 | 1天 | models/fundamental.py | 数据模型定义完成 |
| Phase 2: 新闻抓取模块 | 2天 | news_crawler.py | 能抓取5个数据源的新闻 |
| Phase 3: 供需数据接口 | 2天 | supply_demand.py | 能获取主要品种的供需数据 |
| Phase 4: 地缘政治追踪 | 1天 | geopolitical.py | 能评估地缘政治风险 |
| Phase 5: MarketContext扩展 | 1天 | context.py | 上下文包含基本面维度 |
| Phase 6: 推理层增强 | 1天 | reasoning.py | 推理前自动搜索新闻 |
| Phase 7: 测试和验证 | 1天 | test_fundamental.py | 所有测试用例通过 |

## 六、进度跟踪

### 2026-06-18
- [x] 创建升级方案文档
- [ ] 用户确认方案
- [ ] 开始实施

## 七、风险评估

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 数据源不可用 | 高 | 中 | 多数据源备份 |
| 新闻抓取被封 | 中 | 高 | 代理池+频率控制 |
| 数据质量差 | 高 | 中 | 数据清洗+验证 |
| 性能问题 | 中 | 低 | 异步处理+缓存 |

## 八、预期收益

1. **提升分析准确性**：能够解释市场现象的根本原因
2. **捕捉重大事件**：及时响应地缘政治、政策变化
3. **增强风险预警**：提前识别潜在风险
4. **提高决策质量**：基于更全面的信息做出决策

## 九、下一步行动

1. 用户确认升级方案
2. 开始Phase 1：数据模型设计
3. 逐步实施各模块
4. 测试验证
5. 部署上线