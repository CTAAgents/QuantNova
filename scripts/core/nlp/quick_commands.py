"""
快速命令执行器

提供简化的命令执行，避免网络超时问题：
- 快速状态检查
- 简化的持仓检查
- 本地数据查询
"""

import sys
from pathlib import Path
from typing import Any, Dict

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "scripts"))


def quick_status() -> str:
    """快速获取系统状态"""
    try:
        import psutil
        process = psutil.Process()
        memory = process.memory_info()

        status_lines = [
            "系统状态：",
            f"- 进程 ID: {process.pid}",
            f"- 内存使用: {memory.rss / 1024 / 1024:.1f} MB",
            f"- CPU 使用率: {psutil.cpu_percent(interval=0.1):.1f}%",
            f"- 运行时间: {process.create_time()}",
        ]
        return "\n".join(status_lines)
    except Exception as e:
        return f"获取状态失败: {e}"


def quick_health_check() -> str:
    """快速持仓健康度检查（不依赖网络）"""
    try:
        import json
        from datetime import datetime

        # 检查本地数据文件
        data_dir = project_root / "data"
        meta_db = data_dir / "meta.db"
        market_db = data_dir / "market.db"

        status_lines = ["持仓健康度检查："]

        # 检查数据库
        if meta_db.exists():
            status_lines.append(f"- 元数据库: 存在 ({meta_db.stat().st_size / 1024:.1f} KB)")
        else:
            status_lines.append("- 元数据库: 不存在")

        if market_db.exists():
            status_lines.append(f"- 市场数据库: 存在 ({market_db.stat().st_size / 1024 / 1024:.1f} MB)")
        else:
            status_lines.append("- 市场数据库: 不存在")

        # 检查最新扫描结果
        scan_file = data_dir / "latest_scan.json"
        if scan_file.exists():
            with open(scan_file, 'r', encoding='utf-8') as f:
                scan_data = json.load(f)
                scan_time = scan_data.get('timestamp', '未知')
                signals_count = len(scan_data.get('signals', []))
                status_lines.append(f"- 最新扫描: {scan_time}")
                status_lines.append(f"- 信号数量: {signals_count}")
        else:
            status_lines.append("- 最新扫描: 无")

        status_lines.append(f"\n检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return "\n".join(status_lines)

    except Exception as e:
        return f"健康度检查失败: {e}"


def quick_signals() -> str:
    """快速查看信号"""
    try:
        import json
        from datetime import datetime

        scan_file = project_root / "data" / "latest_scan.json"
        if not scan_file.exists():
            return "暂无扫描结果。请先执行扫描。"

        with open(scan_file, 'r', encoding='utf-8') as f:
            scan_data = json.load(f)

        signals = scan_data.get('signals', [])
        if not signals:
            return "当前没有明显信号。"

        lines = ["当前信号："]
        for signal in signals[:5]:  # 最多显示5个
            symbol = signal.get('symbol', '未知')
            direction = signal.get('direction', '未知')
            strength = signal.get('strength', '未知')
            lines.append(f"- {symbol}: {direction} ({strength})")

        if len(signals) > 5:
            lines.append(f"... 还有 {len(signals) - 5} 个信号")

        return "\n".join(lines)

    except Exception as e:
        return f"获取信号失败: {e}"


# 命令映射
QUICK_COMMANDS = {
    "status": quick_status,
    "health_check": quick_health_check,
    "signals": quick_signals,
}


def execute_quick_command(command_name: str) -> str:
    """执行快速命令"""
    if command_name in QUICK_COMMANDS:
        return QUICK_COMMANDS[command_name]()
    else:
        return f"未知的快速命令: {command_name}"
