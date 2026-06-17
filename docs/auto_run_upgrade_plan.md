# 系统自动运行升级计划

> 版本：v2.0 | 创建日期：2026-06-18 | 更新：2026-06-18
> 状态：规划中

## 一、升级愿景

### 1.1 核心理念

**从"寄生运行"升级为"独立常驻"**，实现：

1. **独立运行**：系统作为独立服务运行，不依赖其他 Agent 平台
2. **常驻内存**：系统常驻内存，持续监控市场状态
3. **智能休眠**：非交易时间自动休眠，节省资源
4. **高效运行**：优化资源使用，提高系统效率

### 1.2 运行模式

| 模式 | 说明 | 优先级 |
|------|------|--------|
| **独立模式** | 系统作为独立服务运行 | 主要 |
| **寄生模式** | 依附于其他 Agent 平台运行 | 辅助 |

---

## 二、当前状态分析

### 2.1 现有架构问题

| 问题 | 说明 |
|------|------|
| **依赖 cron** | 需要外部调度器触发任务 |
| **非持续运行** | 每次任务启动/停止，开销大 |
| **资源浪费** | 非交易时间也在运行 |
| **缺乏自主性** | 无法自主判断何时执行 |

---

## 三、升级目标

### 3.1 核心目标

```
┌─────────────────────────────────────────────────────────────────┐
│                    升级目标                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │  独立运行    │ →  │  常驻内存    │ →  │  智能休眠    │         │
│  │  无依赖     │    │  持续监控    │    │  节省资源    │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│         │                   │                   │               │
│         ↓                   ↓                   ↓               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │  自主决策    │    │  实时响应    │    │  高效运行    │         │
│  │  智能调度    │    │  即时处理    │    │  低资源消耗  │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 具体指标

| 指标 | 当前值 | 目标值 |
|------|--------|--------|
| **内存占用** | 500MB+ | <200MB |
| **CPU 使用率** | 30%+ | <5%（休眠） |
| **启动时间** | 30s+ | <3s |
| **响应延迟** | 5min+ | <1s |

---

## 四、技术方案

### 4.1 独立运行架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    独立运行架构                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    主进程 (Main Process)                  │   │
│  │  • 事件循环                                              │   │
│  │  • 任务调度                                              │   │
│  │  • 资源管理                                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            ↓                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    工作进程 (Worker Processes)             │   │
│  │  • 数据同步 Worker                                        │   │
│  │  • 信号扫描 Worker                                        │   │
│  │  • 因子进化 Worker                                        │   │
│  │  • 策略生成 Worker                                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            ↓                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    共享内存 (Shared Memory)                │   │
│  │  • 市场状态缓存                                          │   │
│  │  • 任务队列                                              │   │
│  │  • 结果缓存                                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 内存管理方案

```python
class MemoryManager:
    """内存管理器"""

    def __init__(self, max_memory_mb: int = 200):
        self.max_memory_mb = max_memory_mb
        self.current_usage = 0
        self.cache = {}
        self.lru_cache = LRUCache(maxsize=1000)

    def check_memory(self) -> bool:
        """检查内存使用"""
        current = psutil.Process().memory_info().rss / 1024 / 1024
        return current < self.max_memory_mb

    def optimize_memory(self):
        """优化内存使用"""
        # 1. 清理过期缓存
        self._cleanup_expired_cache()

        # 2. 压缩大数据结构
        self._compress_large_structures()

        # 3. 释放未使用的资源
        self._release_unused_resources()

    def _cleanup_expired_cache(self):
        """清理过期缓存"""
        expired_keys = [k for k, v in self.cache.items()
                       if time.time() - v['timestamp'] > 3600]
        for key in expired_keys:
            del self.cache[key]
```

### 4.3 智能休眠机制

```python
class IntelligentSleeper:
    """智能休眠器"""

    def __init__(self):
        self.sleep_schedule = {
            'trading_hours': {'sleep': 0.1, 'wake': 0.5},  # 交易时间：高频监控
            'non_trading': {'sleep': 300, 'wake': 60},     # 非交易：低频监控
            'weekend': {'sleep': 3600, 'wake': 300},       # 周末：极低频
        }

    async def sleep(self):
        """智能休眠"""
        current_time = datetime.now()
        if self._is_trading_time(current_time):
            await asyncio.sleep(0.1)  # 交易时间：100ms
        elif self._is_weekend(current_time):
            await asyncio.sleep(3600)  # 周末：1小时
        else:
            await asyncio.sleep(300)  # 非交易：5分钟

    def _is_trading_time(self, dt: datetime) -> bool:
        """判断是否为交易时间"""
        # 期货交易时间：9:00-11:30, 13:30-15:00, 21:00-23:00
        hour = dt.hour
        return (9 <= hour < 11 or 13 <= hour < 15 or 21 <= hour < 23)
```

### 4.4 进程管理器

```python
class ProcessManager:
    """进程管理器"""

    def __init__(self):
        self.workers = {}
        self.max_workers = 4

    async def start_worker(self, worker_type: str):
        """启动工作进程"""
        if len(self.workers) >= self.max_workers:
            await self._wait_for_worker()

        worker = await self._create_worker(worker_type)
        self.workers[worker_type] = worker

    async def stop_worker(self, worker_type: str):
        """停止工作进程"""
        if worker_type in self.workers:
            await self.workers[worker_type].stop()
            del self.workers[worker_type]

    def get_memory_usage(self) -> dict:
        """获取内存使用情况"""
        return {
            'total': psutil.Process().memory_info().rss / 1024 / 1024,
            'workers': len(self.workers),
            'cache_size': len(self.cache),
        }
```

---

## 五、实施计划

### 5.1 Phase 1：基础框架（2-3周）

| 任务 | 说明 | 交付物 |
|------|------|--------|
| 1.1 设计独立运行架构 | 定义进程模型和通信机制 | 架构设计文档 |
| 1.2 实现主进程 | 事件循环和任务调度 | main.py |
| 1.3 实现内存管理器 | 内存监控和优化 | memory_manager.py |
| 1.4 实现智能休眠器 | 根据时间自动调整 | sleeper.py |

### 5.2 Phase 2：工作进程（3-4周）

| 任务 | 说明 | 交付物 |
|------|------|--------|
| 2.1 数据同步 Worker | 独立的数据同步进程 | workers/data_worker.py |
| 2.2 信号扫描 Worker | 独立的信号扫描进程 | workers/signal_worker.py |
| 2.3 因子进化 Worker | 独立的因子进化进程 | workers/evolution_worker.py |
| 2.4 策略生成 Worker | 独立的策略生成进程 | workers/strategy_worker.py |

### 5.3 Phase 3：资源优化（2-3周）

| 任务 | 说明 | 交付物 |
|------|------|--------|
| 3.1 实现共享内存 | 进程间数据共享 | shared_memory.py |
| 3.2 实现缓存优化 | LRU 缓存和压缩 | cache_optimizer.py |
| 3.3 实现资源监控 | CPU/内存/磁盘监控 | resource_monitor.py |
| 3.4 性能测试 | 资源使用测试 | tests/test_performance.py |

### 5.4 Phase 4：集成测试（2周）

| 任务 | 说明 | 交付物 |
|------|------|--------|
| 4.1 单元测试 | 各组件测试 | tests/test_*.py |
| 4.2 集成测试 | 端到端测试 | tests/test_integration.py |
| 4.3 压力测试 | 高并发测试 | tests/test_stress.py |
| 4.4 长期运行测试 | 7x24小时测试 | tests/test_long_running.py |

### 5.5 Phase 5：部署上线（1周）

| 任务 | 说明 | 交付物 |
|------|------|--------|
| 5.1 服务化部署 | 配置为系统服务 | deploy/service.py |
| 5.2 监控告警 | 添加监控和告警 | monitoring/alerts.py |
| 5.3 文档更新 | 更新所有文档 | docs/ |
| 5.4 用户指南 | 编写使用指南 | USER_GUIDE.md |

---

## 六、预期收益

| 收益 | 说明 |
|------|------|
| **独立运行** | 不依赖其他 Agent 平台 |
| **内存优化** | 内存占用降低 60%+ |
| **响应实时** | 重要信号立即处理 |
| **资源节约** | CPU 使用率降低 80%+ |
| **可靠性提升** | 异常自动恢复 |

---

## 七、风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| **系统复杂度** | 维护难度增加 | 模块化设计，充分测试 |
| **内存泄漏** | 长期运行内存增长 | 定期检查，自动重启 |
| **进程竞争** | 资源冲突 | 优先级队列，资源限制 |
| **状态丢失** | 异常导致状态丢失 | 持久化存储，定期备份 |

---

## 八、迁移策略

### 8.1 渐进式迁移

1. **Phase 1**：保留 cron，新增独立运行（双模式）
2. **Phase 2**：逐步将任务迁移到独立运行
3. **Phase 3**：验证稳定性后，移除 cron

### 8.2 回滚方案

1. 保留 cron 任务配置
2. 独立运行可随时禁用
3. 提供一键切换脚本

---

## 九、资源需求

| 资源 | 当前需求 | 升级后需求 |
|------|----------|------------|
| **CPU** | 2核+ | 1核+（休眠时更低） |
| **内存** | 4GB+ | 1GB+ |
| **存储** | 10GB+ | 5GB+ |
| **网络** | 稳定连接 | 稳定连接 |

---

*本计划由 WorkBuddy 于 2026-06-18 创建*
