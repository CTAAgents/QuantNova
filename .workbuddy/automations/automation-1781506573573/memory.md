# 心跳监控自动化执行记录

## 2026-06-16 08:58
- **修复**: DataSyncManager.get_kline() 添加 `allow_tqsdk_fallback` 参数，心跳模式禁用 TqSdk 兜底避免超时阻塞
- **修复**: DataSource 基类及 LocalDBSource/TqSdkSource/CsvSource 支持 **kwargs 透传
- **修复**: heartbeat.py 两处 get_kline 调用传入 `allow_tqsdk_fallback=False`
- **结果**: 持仓 2 个，扫描品种 17 个，预警 0 个，新信号 0 个
- **状态**: DuckDB 有 77 根K线数据（数据量不足滚动窗口 120 根，回退到 ADX 绝对值模式）
- **输出**: 无事件，静默

## 2026-06-17 08:51
- **修复**: heartbeat.py load_positions() 函数兼容列表格式的 positions.json 文件
- **结果**: 持仓 3 个，扫描品种 17 个，预警 2 个，新信号 0 个
- **预警**:
  - [HIGH] JM: ER=0.242 极低，趋势效率丧失
  - [HIGH] HC: ER=0.126 极低，趋势效率丧失
- **状态**: 检测到持仓预警事件，输出给用户

## 2026-06-17 09:08
- **功能增强**: 默认扫描全部86个主力合约品种（不再只扫描配置文件中的17个）
- **实现**: 新增 get_all_main_contracts() 从 data_source.py 提取品种列表，K线不足自动跳过
- **参数**: 新增 --config-only 可回退到仅扫描配置文件品种
- **结果**: 持仓 3 个，扫描品种 86 个，预警 2 个，新信号 0 个
- **预警**:
  - [HIGH] JM: ER=0.242 极低，趋势效率丧失
  - [HIGH] HC: ER=0.126 极低，趋势效率丧失
- **耗时**: ~1分30秒（含行情获取 + K线计算）
- **输出**: 有持仓预警事件
