# 系统自动运行升级计划

> 版本：v1.0 | 创建日期：2026-06-18
> 状态：规划中

## 一、当前状态分析

### 1.1 现有自动化模式

**当前架构**：基于 cron 定时任务

| 任务 | 频率 | 说明 |
|------|------|------|
| 数据同步 | 每日 15:30/20:30 | 定时同步行情数据 |
| 趋势扫描 | 每日 8:40/15:30/20:30 | 定时扫描市场信号 |
| 因子进化 | 每周日 22:00 | 定时运行因子进化 |
| 策略生成 | 每月1日 22:00 | 定时生成新策略 |

### 1.2 现有模式的局限性

| 问题 | 说明 |
|------|------|
| **时间固定** | 无法根据市场状态动态调整执行时机 |
| **资源浪费** | 非交易时间也在运行，浪费计算资源 |
| **响应滞后** | 重要信号可能错过最佳响应时机 |
| **缺乏智能** | 无法判断何时需要执行、何时不需要 |

---

## 二、升级目标

### 2.1 核心目标

**从"定时执行"升级为"事件驱动"**，实现：

1. **智能触发**：根据市场状态自动判断是否需要执行
2. **持续运行**：系统作为服务持续运行，而非定时启动
3. **资源优化**：非交易时间自动休眠，节省资源
4. **实时响应**：重要信号立即处理，而非等待定时任务

### 2.2 升级后架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    全自动运行架构                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    事件驱动引擎                           │   │
│  │  • 市场状态监控                                          │   │
│  │  • 数据更新检测                                          │   │
│  │  • 信号触发检测                                          │   │
│  │  • 资源状态监控                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            ↓                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    智能调度器                             │   │
│  │  • 判断是否需要执行                                      │   │
│  │  • 选择最优执行时机                                      │   │
│  │  • 分配计算资源                                          │   │
│  │  • 管理任务优先级                                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            ↓                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    任务执行器                             │   │
│  │  • 数据同步                                              │   │
│  │  • 信号扫描                                              │   │
│  │  • 因子进化                                              │   │
│  │  • 策略生成                                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 三、技术方案

### 3.1 事件驱动引擎

**核心组件**：`EventDrivenEngine`

```python
class EventDrivenEngine:
    """事件驱动引擎"""

    def __init__(self):
        self.event_queue = asyncio.Queue()
        self.handlers = {}
        self.running = False

    async def start(self):
        """启动引擎"""
        self.running = True
        asyncio.create_task(self._monitor_market_state())
        asyncio.create_task(self._process_events())

    async def _monitor_market_state(self):
        """监控市场状态"""
        while self.running:
            # 检查是否在交易时间
            if self._is_trading_time():
                # 检查数据是否更新
                if self._data_needs_update():
                    await self.event_queue.put(DataUpdateEvent())
                # 检查是否有信号触发
                if self._signal_triggered():
                    await self.event_queue.put(SignalEvent())
            else:
                # 非交易时间，降低监控频率
                await asyncio.sleep(300)  # 5分钟

    async def _process_events(self):
        """处理事件"""
        while self.running:
            event = await self.event_queue.get()
            await self._handle_event(event)
```

### 3.2 智能调度器

**核心组件**：`IntelligentScheduler`

```python
class IntelligentScheduler:
    """智能调度器"""

    def __init__(self):
        self.task_queue = []
        self.resource_monitor = ResourceMonitor()

    async def should_execute(self, task_type: str) -> bool:
        """判断是否应该执行"""
        # 检查资源状态
        if not self.resource_monitor.has_enough_resources():
            return False

        # 检查任务优先级
        if not self._is_high_priority(task_type):
            return False

        # 检查执行间隔
        if not self._enough_time_since_last_run(task_type):
            return False

        return True

    async def schedule_task(self, task):
        """调度任务"""
        if await self.should_execute(task.type):
            self.task_queue.append(task)
            await self._execute_next()
```

### 3.3 事件类型定义

```python
class Event:
    """事件基类"""
    pass

class DataUpdateEvent(Event):
    """数据更新事件"""
    pass

class SignalEvent(Event):
    """信号触发事件"""
    pass

class FactorEvolutionEvent(Event):
    """因子进化事件"""
    pass

class StrategyGenerationEvent(Event):
    """策略生成事件"""
    pass

class SystemHealthEvent(Event):
    """系统健康事件"""
    pass
```

### 3.4 触发条件定义

| 事件 | 触发条件 | 说明 |
|------|----------|------|
| **数据更新** | 新K线数据到达 | 收盘后自动触发 |
| **信号扫描** | 数据更新后 | 数据就绪后自动触发 |
| **因子进化** | 每周一次 + 信号异常 | 定期 + 异常触发 |
| **策略生成** | 每月一次 + 因子有效 | 定期 + 条件触发 |
| **系统健康** | 资源不足或异常 | 监控触发 |

---

## 四、实施计划

### 4.1 Phase 1：基础框架（1-2周）

| 任务 | 说明 | 交付物 |
|------|------|--------|
| 1.1 设计事件驱动架构 | 定义事件类型和处理流程 | 架构设计文档 |
| 1.2 实现 EventDrivenEngine | 核心事件驱动引擎 | event_engine.py |
| 1.3 实现 IntelligentScheduler | 智能调度器 | scheduler.py |
| 1.4 实现 ResourceMonitor | 资源监控器 | resource_monitor.py |

### 4.2 Phase 2：事件处理器（2-3周）

| 任务 | 说明 | 交付物 |
|------|------|--------|
| 2.1 DataUpdateHandler | 数据更新处理器 | handlers/data_handler.py |
| 2.2 SignalHandler | 信号扫描处理器 | handlers/signal_handler.py |
| 2.3 FactorEvolutionHandler | 因子进化处理器 | handlers/evolution_handler.py |
| 2.4 StrategyHandler | 策略生成处理器 | handlers/strategy_handler.py |

### 4.3 Phase 3：集成测试（1-2周）

| 任务 | 说明 | 交付物 |
|------|------|--------|
| 3.1 单元测试 | 各组件测试 | tests/test_event_engine.py |
| 3.2 集成测试 | 端到端测试 | tests/test_auto_run.py |
| 3.3 性能测试 | 资源使用测试 | tests/test_performance.py |

### 4.4 Phase 4：部署上线（1周）

| 任务 | 说明 | 交付物 |
|------|------|--------|
| 4.1 服务化部署 | 配置为系统服务 | deploy/service.py |
| 4.2 监控告警 | 添加监控和告警 | monitoring/alerts.py |
| 4.3 文档更新 | 更新所有文档 | docs/ |

---

## 五、预期收益

| 收益 | 说明 |
|------|------|
| **响应实时** | 重要信号立即处理，不再等待定时任务 |
| **资源优化** | 非交易时间自动休眠，节省 60%+ 计算资源 |
| **智能调度** | 根据市场状态动态调整执行时机 |
| **可靠性提升** | 异常自动恢复，减少人工干预 |
| **扩展性强** | 新增事件类型只需添加处理器 |

---

## 六、风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| **系统复杂度增加** | 维护难度增加 | 模块化设计，充分测试 |
| **资源竞争** | 多任务并发冲突 | 优先级队列，资源限制 |
| **状态管理** | 持久化状态复杂 | 使用数据库存储状态 |
| **异常处理** | 异常可能导致任务堆积 | 超时机制，队列限制 |

---

## 七、迁移策略

### 7.1 渐进式迁移

1. **Phase 1**：保留 cron 任务，新增事件驱动引擎（双模式运行）
2. **Phase 2**：逐步将任务迁移到事件驱动
3. **Phase 3**：验证稳定性后，移除 cron 任务

### 7.2 回滚方案

1. 保留 cron 任务配置
2. 事件驱动引擎可随时禁用
3. 提供一键切换脚本

---

## 八、资源需求

| 资源 | 需求 | 说明 |
|------|------|------|
| **CPU** | 2核+ | 持续运行需要更多 CPU |
| **内存** | 4GB+ | 事件队列和状态缓存 |
| **存储** | 10GB+ | 事件日志和状态数据 |
| **网络** | 稳定连接 | 实时数据获取 |

---

*本计划由 WorkBuddy 于 2026-06-18 创建*
