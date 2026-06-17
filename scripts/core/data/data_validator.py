"""
数据验证器

功能：
1. 检查数据时效性（最新数据日期是否为当天）
2. 检查数据完整性（K线连续性、成交量、价格逻辑等）
3. 生成验证报告
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb
import pandas as pd


class DataValidator:
    """数据验证器"""

    def __init__(self, db_path: str = "data/market.db"):
        """
        初始化验证器

        Args:
            db_path: DuckDB 数据库路径
        """
        self.db_path = db_path

    def check_timeliness(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """
        检查数据时效性

        Args:
            target_date: 目标日期（格式：YYYY-MM-DD），默认为今天

        Returns:
            验证结果字典
        """
        if target_date is None:
            target_date = datetime.now().strftime("%Y-%m-%d")

        result = {
            "is_timely": False,
            "target_date": target_date,
            "latest_dates": {},
            "missing_symbols": [],
            "message": "",
        }

        try:
            conn = duckdb.connect(self.db_path, read_only=True)

            # 查询每个品种的最新日期
            query = """
                SELECT symbol, MAX(DATE(timestamp)) as latest_date
                FROM klines
                WHERE timeframe = 'daily'
                GROUP BY symbol
            """
            df = conn.execute(query).fetchdf()
            conn.close()

            if df.empty:
                result["message"] = "数据库中没有K线数据"
                return result

            # 检查每个品种的最新日期
            target_dt = datetime.strptime(target_date, "%Y-%m-%d")
            today_str = target_date

            timely_count = 0
            total_count = len(df)

            for _, row in df.iterrows():
                symbol = row["symbol"]
                latest_date = row["latest_date"]
                if hasattr(latest_date, "strftime"):
                    latest_str = latest_date.strftime("%Y-%m-%d")
                else:
                    latest_str = str(latest_date)[:10]

                result["latest_dates"][symbol] = latest_str

                if latest_str == today_str:
                    timely_count += 1
                else:
                    result["missing_symbols"].append(symbol)

            # 判断是否整体时效性达标
            timely_ratio = timely_count / total_count if total_count > 0 else 0
            if timely_ratio >= 0.8:  # 80%品种数据最新
                result["is_timely"] = True
                result["message"] = f"数据时效性良好，{timely_count}/{total_count}品种数据已更新至{target_date}"
            else:
                result["message"] = f"数据时效性不足，仅{timely_count}/{total_count}品种数据更新至{target_date}"

        except Exception as e:
            result["message"] = f"检查时效性失败: {e}"

        return result

    def check_completeness(self, symbol: str, days: int = 5) -> Dict[str, Any]:
        """
        检查单个品种的数据完整性

        Args:
            symbol: 品种代码
            days: 检查最近N天

        Returns:
            验证结果字典
        """
        result = {
            "symbol": symbol,
            "is_complete": False,
            "total_bars": 0,
            "missing_dates": [],
            "zero_volume_count": 0,
            "price_errors": [],
            "volume_zero_ratio": 0.0,
            "issues": [],
        }

        try:
            conn = duckdb.connect(self.db_path, read_only=True)

            # 获取最近N天的数据
            query = f"""
                SELECT timestamp, open, high, low, close, volume, open_interest
                FROM klines
                WHERE symbol = '{symbol}' AND timeframe = 'daily'
                ORDER BY timestamp DESC
                LIMIT {days + 10}
            """
            df = conn.execute(query).fetchdf()
            conn.close()

            if df.empty:
                result["issues"].append(f"没有找到{symbol}的K线数据")
                return result

            result["total_bars"] = len(df)

            # 1. 检查成交量非零
            zero_volume = df[df["volume"] <= 0]
            result["zero_volume_count"] = len(zero_volume)
            result["volume_zero_ratio"] = len(zero_volume) / len(df) if len(df) > 0 else 0

            if len(zero_volume) > 0:
                result["issues"].append(f"发现{len(zero_volume)}根零成交量K线")

            # 2. 检查价格逻辑一致性
            price_errors = []
            for _, row in df.iterrows():
                if row["high"] < row["low"]:
                    price_errors.append(f"最高价低于最低价: {row['timestamp']}")
                if row["open"] > row["high"] or row["open"] < row["low"]:
                    price_errors.append(f"开盘价超出最高最低价范围: {row['timestamp']}")
                if row["close"] > row["high"] or row["close"] < row["low"]:
                    price_errors.append(f"收盘价超出最高最低价范围: {row['timestamp']}")

            result["price_errors"] = price_errors
            if price_errors:
                result["issues"].append(f"发现{len(price_errors)}个价格逻辑错误")

            # 3. 检查时间连续性（跳过周末）
            if len(df) >= 2:
                timestamps = sorted(df["timestamp"].tolist())
                missing_dates = []

                for i in range(len(timestamps) - 1):
                    curr = timestamps[i]
                    next_ts = timestamps[i + 1]

                    # 计算工作日差
                    curr_date = curr.date() if hasattr(curr, "date") else datetime.strptime(str(curr)[:10], "%Y-%m-%d").date()
                    next_date = next_ts.date() if hasattr(next_ts, "date") else datetime.strptime(str(next_ts)[:10], "%Y-%m-%d").date()

                    diff_days = (next_date - curr_date).days

                    # 如果间隔超过3天（考虑节假日），可能是缺失
                    if diff_days > 3:
                        # 记录缺失的日期范围
                        missing_dates.append(f"{curr_date} 至 {next_date} 间隔{diff_days}天")

                result["missing_dates"] = missing_dates
                if missing_dates:
                    result["issues"].append(f"发现{len(missing_dates)}处时间间隔异常")

            # 4. 综合判断
            if len(result["issues"]) == 0:
                result["is_complete"] = True

        except Exception as e:
            result["issues"].append(f"检查完整性失败: {e}")

        return result

    def validate_daily_data(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """
        验证当天数据的整体质量

        Args:
            target_date: 目标日期（默认今天）

        Returns:
            综合验证报告
        """
        if target_date is None:
            target_date = datetime.now().strftime("%Y-%m-%d")

        report = {
            "target_date": target_date,
            "overall_status": "UNKNOWN",
            "timeliness": {},
            "completeness_summary": {
                "total_symbols": 0,
                "complete_symbols": 0,
                "incomplete_symbols": 0,
                "critical_issues": [],
            },
            "recommendations": [],
        }

        # 1. 检查时效性
        timeliness = self.check_timeliness(target_date)
        report["timeliness"] = timeliness

        # 2. 抽样检查完整性（检查前10个活跃品种）
        try:
            conn = duckdb.connect(self.db_path, read_only=True)
            query = """
                SELECT DISTINCT symbol
                FROM klines
                WHERE timeframe = 'daily'
                ORDER BY symbol
                LIMIT 10
            """
            symbols = conn.execute(query).fetchdf()["symbol"].tolist()
            conn.close()

            complete_count = 0
            incomplete_symbols = []

            for symbol in symbols:
                completeness = self.check_completeness(symbol, days=5)
                report["completeness_summary"]["total_symbols"] += 1

                if completeness["is_complete"]:
                    complete_count += 1
                else:
                    incomplete_symbols.append({
                        "symbol": symbol,
                        "issues": completeness["issues"],
                    })

            report["completeness_summary"]["complete_symbols"] = complete_count
            report["completeness_summary"]["incomplete_symbols"] = len(incomplete_symbols)
            report["completeness_summary"]["critical_issues"] = incomplete_symbols

            # 3. 综合评估
            if timeliness["is_timely"] and len(incomplete_symbols) == 0:
                report["overall_status"] = "GOOD"
                report["recommendations"].append("数据质量和完整性良好")
            elif timeliness["is_timely"] and len(incomplete_symbols) <= 2:
                report["overall_status"] = "WARNING"
                report["recommendations"].append("数据时效性良好，但部分品种存在完整性问题")
            else:
                report["overall_status"] = "CRITICAL"
                report["recommendations"].append("数据时效性或完整性存在严重问题，建议立即同步")

            # 添加具体建议
            if not timeliness["is_timely"]:
                missing_count = len(timeliness.get("missing_symbols", []))
                report["recommendations"].append(f"有{missing_count}个品种数据未更新至{target_date}")

            if incomplete_symbols:
                report["recommendations"].append(f"有{len(incomplete_symbols)}个品种存在数据完整性问题")

        except Exception as e:
            report["overall_status"] = "ERROR"
            report["recommendations"].append(f"验证过程出错: {e}")

        return report

    def get_validation_summary(self, target_date: Optional[str] = None) -> str:
        """
        获取验证摘要文本（用于日志或通知）

        Args:
            target_date: 目标日期

        Returns:
            摘要文本
        """
        report = self.validate_daily_data(target_date)

        lines = [
            f"数据验证报告 - {report['target_date']}",
            f"整体状态: {report['overall_status']}",
            f"时效性: {'✓' if report['timeliness']['is_timely'] else '✗'} {report['timeliness']['message']}",
            f"完整性: {report['completeness_summary']['complete_symbols']}/{report['completeness_summary']['total_symbols']} 品种完整",
        ]

        if report["completeness_summary"]["critical_issues"]:
            lines.append("问题品种:")
            for item in report["completeness_summary"]["critical_issues"][:3]:  # 只显示前3个
                lines.append(f"  - {item['symbol']}: {', '.join(item['issues'][:2])}")

        if report["recommendations"]:
            lines.append("建议:")
            for rec in report["recommendations"][:3]:
                lines.append(f"  - {rec}")

        return "\n".join(lines)


def main():
    """命令行测试"""
    validator = DataValidator()
    print(validator.get_validation_summary())


if __name__ == "__main__":
    main()