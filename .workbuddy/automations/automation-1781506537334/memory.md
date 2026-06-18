# 扫描执行记录

## 2026-06-15 15:20 执行尝试
- 执行命令：`"C:\Program Files\Python312\python.exe" tools/scan_opportunities.py --output text --save`
- 状态：脚本运行超过7分钟仍无输出，疑似TqSdk连接或数据获取卡住，已终止
- 备注：脚本卡在TqSdk数据获取阶段，无标准输出

## 使用现有扫描结果
- 使用 `data/latest_scan.json` 作为输出（扫描时间：2026-06-15 14:52:04）
- 扫描品种数：17
- 信号数量：0
- 信号摘要：无信号

## 2026-06-16 15:18 执行成功
- 执行命令：`"C:\Program Files\Python312\python.exe" tools/scan_opportunities.py --output text --save`
- 状态：脚本正常完成，耗时约2分钟
- 扫描品种数：86
- 信号数量：5
- 信号摘要：BZ(SHORT), JD(LONG), EC(LONG), SC(SHORT), BR(SHORT)
- 结果已保存到 data/latest_scan.json
- 宏观状态：衰退期，策略权重：趋势跟踪60%，均值回归10%
- 数据源：TqSdk连接正常，部分品种本地数据不足回退到ADX绝对值模式

## 2026-06-18 00:02 执行成功
- 执行命令：`"C:\Program Files\Python312\python.exe" tools/scan_opportunities.py --output text --save`
- 状态：脚本正常完成，耗时约2分钟
- 扫描品种数：86
- 信号数量：2
- 信号摘要：BZ(SHORT), SC(SHORT)
- 结果已保存到 data/latest_scan.json
- 宏观状态：衰退期，策略权重：趋势跟踪60%，均值回归10%
- 数据源：TqSdk不可用（quote返回空数据），使用本地缓存，部分品种回退到ADX绝对值模式
- 数据时效性：数据最新（2026-06-17），与当前日期相差1天
- 注意事项：TqSdk调用超时（RB品种），数据库文件被占用（AD品种扫描失败）

## 2026-06-18 00:07 品种名称更新
- 用户纠正：BZ是纯苯，不是原油
- 更新内容：
  1. 创建品种名称映射文件：config/symbol_names.json（86个品种）
  2. 修改scan_opportunities.py，添加品种中文名称显示功能
  3. 更新latest_scan.json，在信号中添加symbol_name字段
- 品种分类：BZ（纯苯）属于能化板块，SC（原油）也属于能化板块
- 两个品种同时发出做空信号，反映能化板块整体偏弱

## 建议
- 考虑增加本地数据缓存以减少TqSdk依赖
- 监控ADX回退模式的准确性
- 检查数据库文件锁定问题（market.db被占用）