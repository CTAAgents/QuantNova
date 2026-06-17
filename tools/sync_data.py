#!/usr/bin/env python3
"""
数据同步脚本

功能：
1. 同步品种元数据
2. 同步行情数据
3. 同步K线数据
4. 查看统计信息

使用方式：
    python tools/sync_data.py sync                # 全量同步
    python tools/sync_data.py sync --days 30      # 同步30天K线
    python tools/sync_data.py sync --min-oi 5000  # 持仓量≥5000的品种
    python tools/sync_data.py stats               # 查看统计信息
    python tools/sync_data.py symbols             # 仅同步品种
    python tools/sync_data.py quotes              # 仅同步行情
    python tools/sync_data.py klines              # 仅同步K线
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path


# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "scripts"))

from trend_scanner.storage.data_sync import DataSyncManager


def main():
    parser = argparse.ArgumentParser(description="数据同步脚本")
    parser.add_argument("action", choices=["sync", "stats", "symbols", "quotes", "klines", "today"], help="操作类型")
    parser.add_argument("--days", type=int, default=120, help="K线天数（默认120天）")
    parser.add_argument("--min-oi", type=float, default=10000, help="最小持仓量阈值（默认10000手）")
    parser.add_argument("--force", action="store_true", help="强制全量同步")
    parser.add_argument("--db-dir", type=str, default="data", help="数据库目录")

    args = parser.parse_args()

    # 如果是定时同步任务，直接执行并退出
    if args.action == "today":
        run_scheduled_sync(attempt=1)
        return

    # 数据库路径
    sqlite_path = os.path.join(args.db_dir, "meta.db")
    duckdb_path = os.path.join(args.db_dir, "market.db")

    # 确保目录存在
    os.makedirs(args.db_dir, exist_ok=True)

    # 创建同步管理器
    manager = DataSyncManager(sqlite_path=sqlite_path, duckdb_path=duckdb_path)

    print("=" * 60)
    print("期货数据同步工具")
    print("=" * 60)
    print(f"SQLite: {sqlite_path}")
    print(f"DuckDB: {duckdb_path}")
    print(f"操作: {args.action}")
    print("=" * 60)

    if args.action == "sync":
        # 全量同步
        result = manager.full_sync(days=args.days, min_oi=args.min_oi)

        print("\n" + "=" * 60)
        print("同步完成")
        print("=" * 60)

        # 打印统计信息
        manager.print_statistics()

    elif args.action == "stats":
        # 打印统计信息
        manager.print_statistics()

    elif args.action == "symbols":
        # 同步品种
        print("\n开始同步品种元数据...")
        result = manager.sync_symbols()

        if result.get("success"):
            print(f"\n成功同步 {result.get('count', 0)} 个品种")
        else:
            print(f"\n同步失败: {result.get('error')}")

    elif args.action == "quotes":
        # 同步行情
        print(f"\n开始同步行情数据（持仓量≥{args.min_oi}）...")
        result = manager.sync_quotes(min_oi=args.min_oi)

        if result.get("success"):
            print(f"\n成功同步 {result.get('count', 0)} 个品种的行情")
            print(f"活跃品种: {result.get('active_count', 0)} 个")
        else:
            print(f"\n同步失败: {result.get('error')}")

    elif args.action == "klines":
        # 同步K线
        print(f"\n开始同步K线数据（{args.days}天，持仓量≥{args.min_oi}）...")

        # 获取品种列表
        if args.min_oi <= 0:
            # 同步全部品种
            all_symbols = manager.sqlite.get_all_symbols(active_only=True)
            symbol_codes = [s["symbol"] for s in all_symbols]
            print("模式: 全品种同步（忽略持仓量筛选）")
        else:
            # 只同步活跃品种
            active_symbols = manager.get_active_symbols(min_oi=args.min_oi)
            symbol_codes = [s["symbol"] for s in active_symbols]

        if not symbol_codes:
            print("没有品种需要同步")
            return

        print(f"需要同步 {len(symbol_codes)} 个品种")
        result = manager.sync_klines(symbols=symbol_codes, days=args.days, force=args.force)

        print("\n同步完成:")
        print(f"  成功: {result.get('synced', 0)}")
        print(f"  失败: {result.get('failed', 0)}")
        print(f"  跳过: {result.get('skipped', 0)}")


def load_sync_config() -> dict:
    """加载同步配置"""
    config_path = Path(__file__).parent.parent / "config" / "sync_config.json"
    if config_path.exists():
        import json
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def sync_today_with_validation(manager: DataSyncManager, config: dict = None) -> dict:
    """
    同步当天数据并验证

    Args:
        manager: 数据同步管理器
        config: 配置参数

    Returns:
        同步和验证结果
    """
    if config is None:
        config = load_sync_config()

    from trend_scanner.storage.data_validator import DataValidator

    result = {
        "success": False,
        "sync_result": None,
        "validation_result": None,
        "retries": 0,
        "message": "",
    }

    validator = DataValidator(manager.duckdb.db_path)
    today = datetime.now().strftime("%Y-%m-%d")

    # 1. 同步当天K线数据
    print(f"[同步] 开始同步当天数据 ({today})...")

    try:
        # 获取活跃品种
        active_symbols = manager.get_active_symbols(min_oi=config.get("sync_parameters", {}).get("min_oi", 10000))
        symbol_codes = [s["symbol"] for s in active_symbols]

        if not symbol_codes:
            result["message"] = "没有活跃品种需要同步"
            return result

        # 强制同步当天数据（使用较小的天数范围）
        days = config.get("sync_parameters", {}).get("default_days", 5)
        sync_result = manager.sync_klines(
            symbols=symbol_codes,
            days=days,
            force=config.get("sync_parameters", {}).get("force_sync_today", True),
        )
        result["sync_result"] = sync_result

        # 2. 验证数据质量
        print(f"[验证] 检查数据质量和完整性...")
        validation = validator.validate_daily_data(today)
        result["validation_result"] = validation

        # 3. 判断是否成功
        timeliness_ok = validation.get("timeliness", {}).get("is_timely", False)
        completeness_ok = validation.get("overall_status") in ["GOOD", "WARNING"]

        if timeliness_ok and completeness_ok:
            result["success"] = True
            result["message"] = f"数据同步和验证成功: {validation.get('overall_status')}"
        else:
            result["message"] = f"数据验证未通过: {validation.get('overall_status')}"

    except Exception as e:
        result["message"] = f"同步过程出错: {e}"

    return result


def run_scheduled_sync(attempt: int = 1):
    """
    执行定时同步任务（带重试逻辑）

    Args:
        attempt: 当前尝试次数（1或2）
    """
    config = load_sync_config()
    state_file = Path(__file__).parent.parent / config.get("state_file", "data/sync_state.json")

    print(f"[定时同步] 第{attempt}次尝试...")

    # 数据库路径
    sqlite_path = "data/meta.db"
    duckdb_path = "data/market.db"

    # 创建同步管理器
    manager = DataSyncManager(sqlite_path=sqlite_path, duckdb_path=duckdb_path)

    # 执行同步和验证
    result = sync_today_with_validation(manager, config)

    # 更新状态文件
    state = {
        "last_attempt": datetime.now().isoformat(),
        "attempt": attempt,
        "success": result["success"],
        "message": result["message"],
    }

    # 确保目录存在
    state_file.parent.mkdir(parents=True, exist_ok=True)

    import json
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    if result["success"]:
        print(f"[成功] 数据同步完成: {result['message']}")
        # 清除之前的失败状态
        if state_file.exists():
            state_file.unlink()
    else:
        print(f"[失败] 数据同步失败: {result['message']}")

        # 如果是第一次失败且配置了重试，等待第二次尝试
        max_retries = config.get("retry_policy", {}).get("max_retries", 2)
        if attempt < max_retries:
            print(f"[重试] 将在夜盘开盘时重试...")
            # 状态已保存，等待下一次触发
        else:
            # 两次都失败，需要通知用户
            print(f"[告警] 数据同步两次失败，需要通知用户")
            try:
                from alert_manager import AlertManager
                alert_mgr = AlertManager()
                alert_mgr.create_alert(
                    level="ERROR",
                    category="data_sync",
                    title="K线数据同步失败",
                    message=f"日盘收盘和夜盘开盘两次同步均失败: {result['message']}",
                    details={
                        "validation_report": result.get("validation_result"),
                        "sync_result": result.get("sync_result"),
                    },
                )
            except Exception as e:
                print(f"[告警] 创建告警失败: {e}")

    return result


if __name__ == "__main__":
    main()
