"""
持仓数据管理工具

管理 positions.json 的读写、验证、更新。
支持用户手动提交持仓和未来接入真实账户。

使用方式：
    python tools/positions_manager.py list                    # 查看持仓
    python tools/positions_manager.py add --symbol DCE.jm2609 --direction LONG --price 1350
    python tools/positions_manager.py remove --symbol DCE.jm2609
    python tools/positions_manager.py update --symbol DCE.jm2609 --price 1385
"""

import json
import os
import sys
import argparse
from datetime import datetime
from typing import Optional, List, Dict, Any

# 配置文件路径
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config')
POSITIONS_FILE = os.path.join(CONFIG_DIR, 'positions.json')


def load_positions() -> Dict[str, Any]:
    """加载持仓数据"""
    if not os.path.exists(POSITIONS_FILE):
        return {"updated_at": None, "positions": []}
    
    with open(POSITIONS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_positions(data: Dict[str, Any]):
    """保存持仓数据"""
    data["updated_at"] = datetime.now().isoformat()
    os.makedirs(os.path.dirname(POSITIONS_FILE), exist_ok=True)
    with open(POSITIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def list_positions():
    """列出所有持仓"""
    data = load_positions()
    positions = data.get("positions", [])
    
    if not positions:
        print("当前无持仓")
        return
    
    print(f"持仓更新时间: {data.get('updated_at', '未知')}")
    print(f"持仓数量: {len(positions)}")
    print("-" * 80)
    print(f"{'品种':<20} {'方向':<8} {'入场价':<10} {'当前价':<10} {'盈亏%':<10} {'持仓天数':<8}")
    print("-" * 80)
    
    for pos in positions:
        symbol = pos.get("symbol", "")
        direction = pos.get("direction", "")
        entry_price = pos.get("entry_price", 0)
        current_price = pos.get("current_price", 0)
        pnl_pct = pos.get("pnl_pct", 0)
        holding_days = pos.get("holding_days", 0)
        
        pnl_str = f"{pnl_pct:+.2f}%" if pnl_pct else "N/A"
        print(f"{symbol:<20} {direction:<8} {entry_price:<10.1f} {current_price:<10.1f} {pnl_str:<10} {holding_days:<8}")


def add_position(symbol: str, direction: str, price: float, notes: str = ""):
    """添加持仓"""
    data = load_positions()
    positions = data.get("positions", [])
    
    # 检查是否已存在
    for pos in positions:
        if pos.get("symbol") == symbol:
            print(f"错误: {symbol} 已存在持仓记录，请先移除或更新")
            return
    
    new_position = {
        "symbol": symbol,
        "direction": direction.upper(),
        "entry_price": price,
        "current_price": price,
        "holding_days": 0,
        "pnl_pct": 0.0,
        "notes": notes,
        "added_at": datetime.now().isoformat()
    }
    
    positions.append(new_position)
    data["positions"] = positions
    save_positions(data)
    print(f"已添加持仓: {symbol} {direction.upper()} @ {price}")


def remove_position(symbol: str):
    """移除持仓"""
    data = load_positions()
    positions = data.get("positions", [])
    
    found = False
    new_positions = []
    for pos in positions:
        if pos.get("symbol") == symbol:
            found = True
            print(f"已移除持仓: {symbol}")
        else:
            new_positions.append(pos)
    
    if not found:
        print(f"错误: 未找到 {symbol} 的持仓记录")
        return
    
    data["positions"] = new_positions
    save_positions(data)


def update_position(symbol: str, price: Optional[float] = None, notes: Optional[str] = None):
    """更新持仓价格或备注"""
    data = load_positions()
    positions = data.get("positions", [])
    
    found = False
    for pos in positions:
        if pos.get("symbol") == symbol:
            found = True
            if price is not None:
                pos["current_price"] = price
                # 计算盈亏
                entry = pos.get("entry_price", 0)
                if entry > 0:
                    if pos.get("direction") == "LONG":
                        pos["pnl_pct"] = (price - entry) / entry * 100
                    else:
                        pos["pnl_pct"] = (entry - price) / entry * 100
            if notes is not None:
                pos["notes"] = notes
            print(f"已更新持仓: {symbol}")
            break
    
    if not found:
        print(f"错误: 未找到 {symbol} 的持仓记录")
        return
    
    data["positions"] = positions
    save_positions(data)


def main():
    parser = argparse.ArgumentParser(description="持仓数据管理工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # list 命令
    subparsers.add_parser("list", help="查看持仓")
    
    # add 命令
    add_parser = subparsers.add_parser("add", help="添加持仓")
    add_parser.add_argument("--symbol", required=True, help="品种代码（如 DCE.jm2609）")
    add_parser.add_argument("--direction", required=True, choices=["LONG", "SHORT", "long", "short"], help="方向")
    add_parser.add_argument("--price", required=True, type=float, help="入场价格")
    add_parser.add_argument("--notes", default="", help="备注")
    
    # remove 命令
    remove_parser = subparsers.add_parser("remove", help="移除持仓")
    remove_parser.add_argument("--symbol", required=True, help="品种代码")
    
    # update 命令
    update_parser = subparsers.add_parser("update", help="更新持仓")
    update_parser.add_argument("--symbol", required=True, help="品种代码")
    update_parser.add_argument("--price", type=float, help="当前价格")
    update_parser.add_argument("--notes", help="备注")
    
    args = parser.parse_args()
    
    if args.command == "list":
        list_positions()
    elif args.command == "add":
        add_position(args.symbol, args.direction, args.price, args.notes)
    elif args.command == "remove":
        remove_position(args.symbol)
    elif args.command == "update":
        update_position(args.symbol, args.price, args.notes)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
