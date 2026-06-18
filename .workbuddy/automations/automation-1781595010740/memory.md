# K线数据同步执行记录

## 2026-06-17 07:50 (自动化触发)

### 执行命令
```
cd E:/Trend-scanner-Agent && "C:\Program Files\Python312\python.exe" tools/sync_data.py klines --days 120 --min-oi 10000
```

### 执行结果
- **首次执行** `--min-oi 10000`：返回"没有品种需要同步"
  - 原因：`symbols` 表 `open_interest` 字段全部为 NULL，OI 数据仅存在 DuckDB `quotes` 表
- **改用** `--min-oi 0 --force`：成功获取 86 个活跃品种
- **同步进度**：17/73 品种更新至 2026-06-16（最新交易日），后因 TqSdk 盘前连接卡死终止（运行 10m29s）

### 当前数据状态
| 指标 | 数值 |
|------|------|
| 总品种数 | 73 |
| 已更新至 6-16 | 17 个品种 |
| 仍在 6-15 | 56 个品种 |
| K线总行数 | 73,023 |
| 数据源 | TqSdk |

### 已更新品种（至 2026-06-16）
A, B, BZ, C, CF, CS, CY, OI, PF, PL, PR, PX, RM, SA, SH, SR, TA

### 未同步品种（TqSdk 超时/卡死）
CJ, EB, EG, FG, IC, IF, IH, IM, LF, MA, PPF, RB, T, TF, TL, TS, VF

### 已修复问题（2026-06-17 08:30）
1. **symbols 表 OI 回写**：
   - 修改 `sqlite_store.py`：`get_active_symbols` 方法使用 `COALESCE(open_interest, 0)` 处理 NULL
   - 修改 `data_sync.py`：`get_active_symbols` 方法增加 DuckDB quotes 表 OI 回退逻辑
   - 符号映射：SQLite symbol (RB) -> DuckDB symbol (SHFE.rb) 通过 exchange + variety 字段构建
   - 测试结果：`--min-oi 10000` 现在返回 70 个品种（之前返回 0 个）

2. **TqSdk 盘前稳定性**：保持 `--min-oi 0` 参数，避免盘前 OI 数据不完整导致筛选失败

3. **自动化参数调整**：已将 `--min-oi 10000` 改为 `--min-oi 0`，确保全品种同步
