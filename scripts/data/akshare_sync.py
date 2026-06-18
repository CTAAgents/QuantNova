#!/usr/bin/env python3
"""
AKShare 期货数据同步脚本

使用 AKShare 获取期货最新数据，并更新到本地数据库
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import duckdb
import pandas as pd

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "scripts"))


def get_akshare_futures_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    使用 AKShare 获取期货数据
    
    Args:
        symbol: 品种代码（如 'RB0'）
        start_date: 开始日期（如 '20260601'）
        end_date: 结束日期（如 '20260618'）
    
    Returns:
        DataFrame
    """
    import akshare as ak
    
    try:
        df = ak.futures_main_sina(symbol=symbol, start_date=start_date, end_date=end_date)
        return df
    except Exception as e:
        print(f"获取 {symbol} 数据失败: {e}")
        return pd.DataFrame()


def convert_to_klines_format(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """
    将 AKShare 数据转换为 klines 表格式
    
    Args:
        df: AKShare 返回的 DataFrame
        symbol: 品种代码
    
    Returns:
        DataFrame
    """
    if df.empty:
        return pd.DataFrame()
    
    # 创建映射列名
    column_mapping = {
        '日期': 'timestamp',
        '开盘价': 'open',
        '最高价': 'high',
        '最低价': 'low',
        '收盘价': 'close',
        '成交量': 'volume',
        '持仓量': 'open_interest'
    }
    
    # 重命名列
    df_converted = df.rename(columns=column_mapping)
    
    # 选择需要的列
    required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'open_interest']
    df_converted = df_converted[required_columns].copy()
    
    # 添加其他列
    df_converted['symbol'] = symbol
    df_converted['timeframe'] = 'daily'
    df_converted['source'] = 'akshare'
    df_converted['created_at'] = datetime.now()
    
    # 转换 timestamp 列为 datetime
    df_converted['timestamp'] = pd.to_datetime(df_converted['timestamp'])
    
    # 确保数值列是正确的类型
    numeric_columns = ['open', 'high', 'low', 'close', 'volume', 'open_interest']
    for col in numeric_columns:
        df_converted[col] = pd.to_numeric(df_converted[col], errors='coerce')
    
    return df_converted


def sync_futures_data_to_db(db_path: str, symbols: list[str] = None, days: int = 5):
    """
    同步期货数据到数据库
    
    Args:
        db_path: 数据库路径
        symbols: 品种列表，None 则同步所有品种
        days: 同步天数
    """
    import akshare as ak
    
    print("=" * 60)
    print("AKShare 期货数据同步")
    print("=" * 60)
    
    # 获取品种列表
    if symbols is None:
        print("\n[步骤1] 获取期货品种列表...")
        try:
            df_symbols = ak.futures_display_main_sina()
            symbols = df_symbols['symbol'].tolist()
            print(f"  找到 {len(symbols)} 个品种")
        except Exception as e:
            print(f"  获取品种列表失败: {e}")
            return
    
    # 连接数据库
    print(f"\n[步骤2] 连接数据库: {db_path}")
    conn = duckdb.connect(db_path)
    
    # 计算日期范围
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
    print(f"  日期范围: {start_date} - {end_date}")
    
    # 同步数据
    print(f"\n[步骤3] 同步 {len(symbols)} 个品种的数据...")
    synced_count = 0
    failed_count = 0
    
    for i, symbol in enumerate(symbols, 1):
        try:
            print(f"  [{i}/{len(symbols)}] 同步 {symbol}...")
            
            # 获取数据
            df = get_akshare_futures_data(symbol, start_date, end_date)
            
            if df.empty:
                print(f"    [跳过] 无数据")
                failed_count += 1
                continue
            
            # 转换格式
            df_converted = convert_to_klines_format(df, symbol)
            
            if df_converted.empty:
                print(f"    [跳过] 转换失败")
                failed_count += 1
                continue
            
            # 插入数据库
            conn.execute("""
                INSERT INTO klines (symbol, timestamp, timeframe, open, high, low, close, volume, open_interest, source, created_at)
                SELECT symbol, timestamp, timeframe, open, high, low, close, volume, open_interest, source, created_at
                FROM df_converted
            """)
            
            synced_count += 1
            print(f"    [成功] 同步 {len(df_converted)} 条记录")
            
        except Exception as e:
            print(f"    [错误] {e}")
            failed_count += 1
    
    # 关闭连接
    conn.close()
    
    # 打印统计
    print("\n" + "=" * 60)
    print("同步完成")
    print("=" * 60)
    print(f"  成功同步: {synced_count} 个品种")
    print(f"  同步失败: {failed_count} 个品种")
    print(f"  日期范围: {start_date} - {end_date}")
    
    return {
        "synced": synced_count,
        "failed": failed_count,
        "start_date": start_date,
        "end_date": end_date
    }


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AKShare 期货数据同步")
    parser.add_argument("--symbols", type=str, help="品种列表（逗号分隔，如 RB0,HC0,JM0）")
    parser.add_argument("--days", type=int, default=5, help="同步天数（默认5天）")
    parser.add_argument("--db-path", type=str, default="data/market.db", help="数据库路径")
    
    args = parser.parse_args()
    
    # 解析品种列表
    symbols = None
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",")]
    
    # 执行同步
    result = sync_futures_data_to_db(
        db_path=args.db_path,
        symbols=symbols,
        days=args.days
    )
    
    print(f"\n同步结果: {result}")


if __name__ == "__main__":
    main()
