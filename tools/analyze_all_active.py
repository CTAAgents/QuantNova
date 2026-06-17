#!/usr/bin/env python3
"""
全品种活跃筛选 + Agent 分析脚本

功能：
1. 获取全部期货主力合约品种（86个）
2. 批量获取行情数据，筛选持仓量≥10000手的活跃品种
3. 对活跃品种获取K线数据并计算技术指标
4. 使用 Reasoner Agent 进行推理分析
5. 使用 Debater Agent 进行辩论修正
6. 输出文本报告和 JSON 数据

使用方式：
    python tools/analyze_all_active.py                    # 全量分析
    python tools/analyze_all_active.py --min-oi 5000      # 自定义持仓量阈值
    python tools/analyze_all_active.py --skip-debate      # 跳过辩论
    python tools/analyze_all_active.py --output json      # 仅输出 JSON
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "scripts"))

from trend_scanner.indicators import IndicatorEngine
from trend_scanner.market_analysis import TrendPhaseDetector
from trend_scanner.tqsdk_bridge import TqSdkDataSource


class ActiveSymbolAnalyzer:
    """全品种活跃筛选 + Agent 分析器"""

    def __init__(self, min_oi: int = 10000, skip_debate: bool = False):
        """
        初始化分析器

        Args:
            min_oi: 最小持仓量阈值
            skip_debate: 是否跳过辩论
        """
        self.min_oi = min_oi
        self.skip_debate = skip_debate

        # 初始化数据源
        self.data_source = TqSdkDataSource()

        # 延迟初始化 Agent（避免导入错误）
        self._reasoner = None
        self._debater = None

    @property
    def reasoner(self):
        """延迟初始化 Reasoner Agent"""
        if self._reasoner is None:
            from tools.reasoner import ReasonerAgent

            self._reasoner = ReasonerAgent()
        return self._reasoner

    @property
    def debater(self):
        """延迟初始化 Debater Agent"""
        if self._debater is None:
            from tools.debater import DebaterAgent

            self._debater = DebaterAgent()
        return self._debater

    def step1_discover_symbols(self) -> list[dict[str, Any]]:
        """
        步骤1：发现所有主力合约品种

        Returns:
            品种列表
        """
        print("=" * 60)
        print("[步骤1] 获取所有主力合约品种...")
        print("=" * 60)

        symbols = self.data_source.get_all_symbols()

        if not symbols:
            print("[错误] 无法获取品种列表")
            return []

        print(f"发现 {len(symbols)} 个主力合约品种")

        # 按交易所分组统计
        exchange_count = {}
        for s in symbols:
            exchange = s.get("exchange", "UNKNOWN")
            exchange_count[exchange] = exchange_count.get(exchange, 0) + 1

        for exchange, count in sorted(exchange_count.items()):
            print(f"  - {exchange}: {count} 个品种")

        return symbols

    def step2_filter_active(self, symbols: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        步骤2：筛选活跃品种（持仓量≥阈值）

        Args:
            symbols: 品种列表

        Returns:
            活跃品种列表
        """
        print("\n" + "=" * 60)
        print(f"[步骤2] 筛选活跃品种（持仓量≥{self.min_oi}手）...")
        print("=" * 60)

        # 获取所有 TqSdk 品种代码
        tq_symbols = [s["tq_symbol"] for s in symbols]

        # 批量获取行情
        print(f"正在获取 {len(tq_symbols)} 个品种的行情数据...")
        quotes = self.data_source.get_quotes_batch(tq_symbols)

        if not quotes:
            print("[错误] 无法获取行情数据")
            return []

        print(f"成功获取 {len(quotes)} 个品种的行情数据")

        # 筛选活跃品种
        active_symbols = []

        for symbol_info in symbols:
            tq_symbol = symbol_info["tq_symbol"]
            quote = quotes.get(tq_symbol)

            if quote is None:
                continue

            oi = quote.get("open_interest", 0) or 0
            volume = quote.get("volume", 0) or 0

            if oi >= self.min_oi:
                active_symbol = {
                    **symbol_info,
                    "last_price": quote.get("last_price", 0),
                    "open_interest": oi,
                    "volume": volume,
                    "bid_price1": quote.get("bid_price1", 0),
                    "ask_price1": quote.get("ask_price1", 0),
                }
                active_symbols.append(active_symbol)

        # 按持仓量排序
        active_symbols.sort(key=lambda x: x.get("open_interest", 0), reverse=True)

        print(f"\n筛选结果：{len(active_symbols)} 个活跃品种（持仓量≥{self.min_oi}手）")
        print("\n活跃品种列表：")
        print("-" * 80)
        print(f"{'品种':<10} {'交易所':<8} {'最新价':<12} {'持仓量':<12} {'成交量':<12}")
        print("-" * 80)

        for s in active_symbols[:20]:  # 只显示前20个
            print(
                f"{s['symbol']:<10} {s['exchange']:<8} {s['last_price']:<12.2f} "
                f"{s['open_interest']:<12.0f} {s['volume']:<12.0f}"
            )

        if len(active_symbols) > 20:
            print(f"... 还有 {len(active_symbols) - 20} 个品种")

        return active_symbols

    def step3_analyze_symbols(self, active_symbols: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        步骤3：对活跃品种进行 Agent 分析

        Args:
            active_symbols: 活跃品种列表

        Returns:
            分析结果列表
        """
        print("\n" + "=" * 60)
        print(f"[步骤3] 对 {len(active_symbols)} 个活跃品种进行 Agent 分析...")
        print("=" * 60)

        results = []

        for i, symbol_info in enumerate(active_symbols, 1):
            symbol = symbol_info["symbol"]
            tq_symbol = symbol_info["tq_symbol"]

            print(f"\n[{i}/{len(active_symbols)}] 分析 {symbol}...")

            try:
                # 1. 获取K线数据
                df = self.data_source.get_kline(symbol, days=120)

                if df is None or len(df) < 60:
                    print(f"  [跳过] {symbol} 数据不足（{len(df) if df is not None else 0} 条）")
                    results.append(
                        {"symbol": symbol, "status": "SKIPPED", "reason": "数据不足", "symbol_info": symbol_info}
                    )
                    continue

                # 2. 计算技术指标
                engine = IndicatorEngine(df)
                engine.compute_all()

                # 计算复合趋势强度
                composite = engine.get_trend_strength_composite()
                engine.df["trend_strength_composite"] = composite

                # 获取最新数据
                latest = engine.df.iloc[-1]

                # 提取指标
                er = float(latest.get("er", 0))
                tsi = float(latest.get("tsi", 0))
                r_squared = float(latest.get("r_squared", 0))
                hurst = float(latest.get("hurst", 0.5))
                trend_strength = float(latest.get("trend_strength_composite", 0))
                rsi = float(latest.get("rsi", 50))
                adx = float(latest.get("adx", 0))

                # 判断方向
                if tsi > 0 and er > 0.5:
                    direction = "LONG"
                elif tsi < 0 and er > 0.5:
                    direction = "SHORT"
                else:
                    direction = "NEUTRAL"

                # 判断趋势阶段
                try:
                    trend_phase = TrendPhaseDetector.detect_phase(engine.df)
                    phase_str = trend_phase.phase if hasattr(trend_phase, "phase") else "UNKNOWN"
                except:
                    phase_str = "UNKNOWN"

                # 构建信号
                signal = {
                    "symbol": f"{symbol_info['exchange']}.{symbol.lower()}",
                    "direction": direction,
                    "trend_phase": phase_str,
                    "trend_strength_composite": trend_strength,
                    "tsi": tsi,
                    "er": er,
                    "r_squared": r_squared,
                    "hurst": hurst,
                    "rsi": rsi,
                    "adx": adx,
                    "key_signals": [],
                    "risk_factors": [],
                }

                # 3. Reasoner 分析
                print("  [Reasoner] 生成交易决策简报...")
                brief = self.reasoner.analyze(signal)

                # 4. Debater 辩论（可选）
                debate_result = None
                if not self.skip_debate:
                    print("  [Debater] 检查是否需要辩论...")
                    debate_result = self.debater.debate(brief, force=False)

                # 构建结果
                result = {
                    "symbol": symbol,
                    "exchange": symbol_info["exchange"],
                    "tq_symbol": tq_symbol,
                    "status": "SUCCESS",
                    "symbol_info": symbol_info,
                    "indicators": {
                        "er": er,
                        "tsi": tsi,
                        "r_squared": r_squared,
                        "hurst": hurst,
                        "trend_strength": trend_strength,
                        "rsi": rsi,
                        "adx": adx,
                        "direction": direction,
                        "trend_phase": phase_str,
                    },
                    "brief": brief,
                    "debate": debate_result,
                    "analysis_time": datetime.now().isoformat(),
                }

                results.append(result)

                # 输出摘要
                confidence = 0
                if brief.get("routes"):
                    for route in brief["routes"]:
                        if route.get("route_id") == brief.get("recommended_route"):
                            confidence = route.get("confidence", 0)
                            break

                print(f"  [结果] 方向={direction}, 置信度={confidence:.2f}, 趋势强度={trend_strength:.2f}, ER={er:.2f}")

            except Exception as e:
                print(f"  [错误] {symbol} 分析失败: {e}")
                import traceback

                traceback.print_exc()

                results.append({"symbol": symbol, "status": "ERROR", "error": str(e), "symbol_info": symbol_info})

        return results

    def generate_report(self, results: list[dict[str, Any]]) -> str:
        """
        生成文本报告

        Args:
            results: 分析结果列表

        Returns:
            报告文本
        """
        report_lines = []

        report_lines.append("=" * 80)
        report_lines.append("全品种活跃筛选 + Agent 分析报告")
        report_lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("=" * 80)

        # 统计
        total = len(results)
        success = len([r for r in results if r.get("status") == "SUCCESS"])
        skipped = len([r for r in results if r.get("status") == "SKIPPED"])
        errors = len([r for r in results if r.get("status") == "ERROR"])

        report_lines.append("\n统计:")
        report_lines.append(f"  - 总计: {total} 个品种")
        report_lines.append(f"  - 成功: {success} 个")
        report_lines.append(f"  - 跳过: {skipped} 个")
        report_lines.append(f"  - 错误: {errors} 个")

        # 按方向分组
        long_symbols = []
        short_symbols = []
        neutral_symbols = []

        for r in results:
            if r.get("status") != "SUCCESS":
                continue

            direction = r.get("indicators", {}).get("direction", "NEUTRAL")
            if direction == "LONG":
                long_symbols.append(r)
            elif direction == "SHORT":
                short_symbols.append(r)
            else:
                neutral_symbols.append(r)

        report_lines.append("\n方向分布:")
        report_lines.append(f"  - 多头: {len(long_symbols)} 个")
        report_lines.append(f"  - 空头: {len(short_symbols)} 个")
        report_lines.append(f"  - 中性: {len(neutral_symbols)} 个")

        # 详细结果
        report_lines.append("\n" + "=" * 80)
        report_lines.append("详细分析结果")
        report_lines.append("=" * 80)

        # 多头品种
        if long_symbols:
            report_lines.append("\n【多头品种】")
            report_lines.append("-" * 80)

            for r in sorted(long_symbols, key=lambda x: x.get("indicators", {}).get("trend_strength", 0), reverse=True):
                self._append_symbol_report(report_lines, r)

        # 空头品种
        if short_symbols:
            report_lines.append("\n【空头品种】")
            report_lines.append("-" * 80)

            for r in sorted(
                short_symbols, key=lambda x: x.get("indicators", {}).get("trend_strength", 0), reverse=True
            ):
                self._append_symbol_report(report_lines, r)

        # 中性品种
        if neutral_symbols:
            report_lines.append("\n【中性品种】")
            report_lines.append("-" * 80)

            for r in neutral_symbols[:10]:  # 只显示前10个
                self._append_symbol_report(report_lines, r)

            if len(neutral_symbols) > 10:
                report_lines.append(f"\n... 还有 {len(neutral_symbols) - 10} 个中性品种")

        # 错误和跳过的品种
        failed = [r for r in results if r.get("status") in ("SKIPPED", "ERROR")]
        if failed:
            report_lines.append("\n" + "=" * 80)
            report_lines.append("跳过/错误的品种")
            report_lines.append("=" * 80)

            for r in failed:
                report_lines.append(
                    f"\n{r['symbol']} ({r.get('exchange', 'N/A')}): {r.get('reason', r.get('error', '未知原因'))}"
                )

        return "\n".join(report_lines)

    def _append_symbol_report(self, report_lines: list[str], result: dict[str, Any]):
        """添加单个品种的报告"""
        symbol = result["symbol"]
        exchange = result.get("exchange", "N/A")
        indicators = result.get("indicators", {})
        brief = result.get("brief", {})
        debate = result.get("debate")

        report_lines.append(f"\n{symbol} ({exchange})")
        report_lines.append(f"  方向: {indicators.get('direction', 'N/A')}")
        report_lines.append(f"  趋势阶段: {indicators.get('trend_phase', 'N/A')}")
        report_lines.append(f"  趋势强度: {indicators.get('trend_strength', 0):.3f}")
        report_lines.append(f"  ER: {indicators.get('er', 0):.3f}")
        report_lines.append(f"  TSI: {indicators.get('tsi', 0):.2f}")
        report_lines.append(f"  R²: {indicators.get('r_squared', 0):.3f}")
        report_lines.append(f"  RSI: {indicators.get('rsi', 50):.1f}")
        report_lines.append(f"  ADX: {indicators.get('adx', 0):.1f}")

        # 简报摘要
        if brief:
            # 提取推荐方案
            recommended_route = brief.get("recommended_route", "")
            confidence = 0
            action = ""

            for route in brief.get("routes", []):
                if route.get("route_id") == recommended_route:
                    confidence = route.get("confidence", 0)
                    action = route.get("action", "")
                    break

            report_lines.append(f"  推荐方案: {recommended_route}")
            report_lines.append(f"  置信度: {confidence:.2f}")
            report_lines.append(f"  建议操作: {action}")

            # 风险提示
            warnings = brief.get("warnings", [])
            if warnings:
                report_lines.append(f"  风险提示: {'; '.join(warnings[:3])}")

        # 辩论结果
        if debate and debate.get("debate_triggered"):
            report_lines.append("  辩论修正: 是")
            revision_summary = debate.get("revision_summary", "")
            if revision_summary:
                report_lines.append(f"  修正说明: {revision_summary}")
        else:
            report_lines.append("  辩论修正: 否")

    def run(self) -> dict[str, Any]:
        """
        执行完整分析流程

        Returns:
            分析结果字典
        """
        start_time = datetime.now()

        print("\n" + "=" * 80)
        print("全品种活跃筛选 + Agent 分析")
        print(f"开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        # 步骤1：发现所有品种
        symbols = self.step1_discover_symbols()
        if not symbols:
            return {
                "status": "ERROR",
                "error": "无法获取品种列表",
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
            }

        # 步骤2：筛选活跃品种
        active_symbols = self.step2_filter_active(symbols)
        if not active_symbols:
            return {
                "status": "ERROR",
                "error": "没有活跃品种",
                "symbols_count": len(symbols),
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
            }

        # 步骤3：Agent 分析
        results = self.step3_analyze_symbols(active_symbols)

        # 生成报告
        report = self.generate_report(results)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print("\n" + "=" * 80)
        print("分析完成")
        print(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"耗时: {duration:.1f} 秒")
        print("=" * 80)

        return {
            "status": "SUCCESS",
            "symbols_count": len(symbols),
            "active_count": len(active_symbols),
            "results_count": len(results),
            "success_count": len([r for r in results if r.get("status") == "SUCCESS"]),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "results": results,
            "report": report,
        }


def main():
    parser = argparse.ArgumentParser(description="全品种活跃筛选 + Agent 分析")
    parser.add_argument("--min-oi", type=int, default=10000, help="最小持仓量阈值（默认10000手）")
    parser.add_argument("--skip-debate", action="store_true", help="跳过辩论")
    parser.add_argument("--output", choices=["json", "text", "both"], default="both", help="输出格式")
    parser.add_argument("--save", action="store_true", help="保存结果到文件")

    args = parser.parse_args()

    # 创建分析器
    analyzer = ActiveSymbolAnalyzer(min_oi=args.min_oi, skip_debate=args.skip_debate)

    # 执行分析
    result = analyzer.run()

    # 输出结果
    if result.get("status") == "SUCCESS":
        report = result.get("report", "")
        results_data = result.get("results", [])

        if args.output in ("text", "both"):
            print("\n" + report)

        if args.output in ("json", "both"):
            # JSON 输出（不包含 report 字段，避免重复）
            json_data = {k: v for k, v in result.items() if k != "report"}
            print("\n" + json.dumps(json_data, ensure_ascii=False, indent=2, default=str))

        # 保存到文件
        if args.save:
            # 保存 JSON
            json_path = project_root / "data" / "active_symbols_analysis.json"
            json_path.parent.mkdir(parents=True, exist_ok=True)

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)

            print(f"\nJSON 数据已保存到: {json_path}")

            # 保存报告
            report_path = project_root / "data" / "active_symbols_report.txt"
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report)

            print(f"文本报告已保存到: {report_path}")
    else:
        print(f"\n分析失败: {result.get('error', '未知错误')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
