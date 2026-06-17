"""
技术指标同步脚本

在下载 K 线数据时，同时使用 TqSdk ta 模块计算技术指标并保存到 DuckDB。

功能：
1. 从 DuckDB 读取 K 线数据
2. 使用 TqSdk ta 模块计算技术指标
3. 将指标保存到 DuckDB 的 indicators 表

使用方式：
    python tools/sync_indicators.py              # 同步所有品种的技术指标
    python tools/sync_indicators.py --symbols JD,RB  # 同步指定品种
    python tools/sync_indicators.py --check      # 检查指标状态
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import duckdb
import pandas as pd
import numpy as np

# 添加模块路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))


# 从 TqSdk K 线数据计算技术指标
def compute_indicators_from_klines(df: pd.DataFrame) -> Dict[str, pd.Series]:
    """
    从 K 线数据计算技术指标（使用 pandas 实现，不依赖 TqSdk）
    
    Args:
        df: DataFrame with columns: open, high, low, close, volume
        
    Returns:
        Dict of indicator name -> Series
    """
    indicators = {}
    
    # ===== 趋势指标 =====
    # EMA
    for period in [20, 60]:
        indicators[f'ema{period}'] = df['close'].ewm(span=period, adjust=False).mean()
    
    # SMA
    for period in [5, 10, 20, 60, 100]:
        indicators[f'sma{period}'] = df['close'].rolling(period).mean()
    
    # ATR
    period = 14
    tr1 = df['high'] - df['low']
    tr2 = abs(df['high'] - df['close'].shift(1))
    tr3 = abs(df['low'] - df['close'].shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    indicators['atr'] = tr.rolling(period).mean()
    
    # ADX, +DI, -DI (Wilder's method)
    adx_period = 14
    adx_m = 6
    plus_dm = df['high'] - df['high'].shift(1)
    minus_dm = df['low'].shift(1) - df['low']
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    
    atr_smooth = tr.ewm(alpha=1/adx_period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/adx_period, adjust=False).mean() / atr_smooth
    minus_di = 100 * minus_dm.ewm(alpha=1/adx_period, adjust=False).mean() / atr_smooth
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.ewm(alpha=1/adx_m, adjust=False).mean()
    
    indicators['plus_di'] = plus_di
    indicators['minus_di'] = minus_di
    indicators['adx'] = adx
    
    # ADXR
    indicators['adxr'] = (adx + adx.shift(adx_m)) / 2
    
    # 效率比 (ER)
    er_period = 20
    direction = abs(df['close'] - df['close'].shift(er_period))
    volatility = df['close'].diff().abs().rolling(er_period).sum()
    indicators['er'] = direction / volatility
    
    # R-squared
    r2_period = 20
    def calc_r2(series):
        if len(series) < r2_period:
            return np.nan
        x = np.arange(len(series))
        y = series.values
        if np.any(np.isnan(y)):
            return np.nan
        corr = np.corrcoef(x, y)[0, 1]
        return corr ** 2 if not np.isnan(corr) else np.nan
    indicators['r_squared'] = df['close'].rolling(r2_period).apply(calc_r2, raw=False)
    
    # TSI (True Strength Index)
    tsi_long, tsi_short = 25, 13
    momentum = df['close'].diff()
    double_smooth = momentum.ewm(span=tsi_long, adjust=False).mean().ewm(span=tsi_short, adjust=False).mean()
    double_smooth_abs = momentum.abs().ewm(span=tsi_long, adjust=False).mean().ewm(span=tsi_short, adjust=False).mean()
    indicators['tsi'] = 100 * double_smooth / double_smooth_abs
    
    # ===== 震荡指标 =====
    # RSI (Wilder's smoothing)
    rsi_period = 14
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta.where(delta < 0, 0))
    avg_gain = gain.ewm(alpha=1/rsi_period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/rsi_period, adjust=False).mean()
    rs = avg_gain / avg_loss
    indicators['rsi'] = 100 - (100 / (1 + rs))
    
    # STOCH (KDJ)
    k_period, d_period = 9, 6
    low_min = df['low'].rolling(k_period).min()
    high_max = df['high'].rolling(k_period).max()
    stoch_k = 100 * (df['close'] - low_min) / (high_max - low_min)
    indicators['stoch_k'] = stoch_k
    indicators['stoch_d'] = stoch_k.rolling(d_period).mean()
    
    # Williams %R
    wr_period = 14
    high_max_wr = df['high'].rolling(wr_period).max()
    low_min_wr = df['low'].rolling(wr_period).min()
    indicators['williams_r'] = -100 * (high_max_wr - df['close']) / (high_max_wr - low_min_wr)
    
    # CCI
    cci_period = 14
    tp = (df['high'] + df['low'] + df['close']) / 3
    sma_tp = tp.rolling(cci_period).mean()
    mad = tp.rolling(cci_period).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True)
    indicators['cci'] = (tp - sma_tp) / (0.015 * mad)
    
    # ===== 动量指标 =====
    # MACD
    fast, slow, signal = 12, 26, 9
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    macd_signal = macd_line.ewm(span=signal, adjust=False).mean()
    indicators['macd'] = macd_line
    indicators['macd_signal'] = macd_signal
    indicators['macd_hist'] = macd_line - macd_signal
    
    # ROC
    roc_period = 10
    indicators['roc'] = (df['close'] - df['close'].shift(roc_period)) / df['close'].shift(roc_period) * 100
    
    # ===== 波动率指标 =====
    # Bollinger Bands
    bb_period, bb_std = 20, 2
    bb_mid = df['close'].rolling(bb_period).mean()
    bb_std_val = df['close'].rolling(bb_period).std()
    indicators['bb_upper'] = bb_mid + bb_std * bb_std_val
    indicators['bb_mid'] = bb_mid
    indicators['bb_lower'] = bb_mid - bb_std * bb_std_val
    indicators['bb_width'] = (indicators['bb_upper'] - indicators['bb_lower']) / bb_mid
    
    # ATR Ratio
    atr_short = tr.rolling(6).mean()
    atr_long = tr.rolling(24).mean()
    indicators['atr_ratio'] = atr_short / atr_long
    
    # ===== 通道指标 =====
    # Donchian Channel
    dc_period = 20
    indicators['dc_upper'] = df['high'].rolling(dc_period).max()
    indicators['dc_lower'] = df['low'].rolling(dc_period).min()
    indicators['dc_middle'] = (indicators['dc_upper'] + indicators['dc_lower']) / 2
    
    return indicators


def sync_indicators_for_symbol(symbol: str, db_path: str = 'data/market.db') -> Dict[str, Any]:
    """
    为单个品种同步技术指标
    
    Args:
        symbol: 品种代码
        db_path: DuckDB 数据库路径
        
    Returns:
        同步结果
    """
    conn = duckdb.connect(db_path)
    
    # 读取 K 线数据
    query = f"""
        SELECT timestamp, open, high, low, close, volume
        FROM klines
        WHERE symbol = '{symbol}'
        ORDER BY timestamp ASC
    """
    df = conn.execute(query).fetchdf()
    
    if len(df) < 30:
        conn.close()
        return {'symbol': symbol, 'status': 'skip', 'reason': f'数据不足 ({len(df)} rows)'}
    
    # 计算技术指标
    indicators = compute_indicators_from_klines(df)
    
    # 构建指标 DataFrame
    indicator_df = pd.DataFrame({
        'symbol': symbol,
        'timestamp': df['timestamp'],
    })
    
    # 添加所有指标列
    for name, series in indicators.items():
        indicator_df[name] = series.values
    
    # 删除旧的指标数据
    conn.execute(f"DELETE FROM indicators WHERE symbol = '{symbol}'")
    
    # 插入新数据
    # 先检查 indicators 表是否存在，不存在则创建
    conn.execute("""
        CREATE TABLE IF NOT EXISTS indicators (
            symbol VARCHAR,
            timestamp TIMESTAMP,
            indicator_name VARCHAR,
            value DOUBLE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 转换为长格式存储
    records = []
    for _, row in indicator_df.iterrows():
        ts = row['timestamp']
        for name in indicators.keys():
            val = row[name]
            if pd.notna(val):
                records.append({
                    'symbol': symbol,
                    'timestamp': ts,
                    'indicator_name': name,
                    'value': float(val),
                    'created_at': datetime.now()
                })
    
    if records:
        records_df = pd.DataFrame(records)
        conn.execute("""
            INSERT INTO indicators (symbol, timestamp, indicator_name, value, created_at)
            SELECT symbol, timestamp, indicator_name, value, created_at FROM records_df
        """)
    
    conn.close()
    
    return {
        'symbol': symbol,
        'status': 'success',
        'rows': len(records),
        'indicators': list(indicators.keys()),
        'latest_date': str(df['timestamp'].iloc[-1])
    }


def check_indicators_status(db_path: str = 'data/market.db') -> pd.DataFrame:
    """检查指标同步状态"""
    conn = duckdb.connect(db_path, read_only=True)
    
    try:
        query = """
            SELECT 
                symbol,
                COUNT(DISTINCT indicator_name) as indicator_count,
                MIN(timestamp) as earliest,
                MAX(timestamp) as latest,
                COUNT(*) as total_records
            FROM indicators
            GROUP BY symbol
            ORDER BY symbol
        """
        df = conn.execute(query).fetchdf()
    except Exception:
        df = pd.DataFrame()
    
    conn.close()
    return df


def main():
    parser = argparse.ArgumentParser(description='技术指标同步脚本')
    parser.add_argument('--symbols', type=str, help='品种列表（逗号分隔）')
    parser.add_argument('--check', action='store_true', help='检查指标状态')
    parser.add_argument('--db-dir', type=str, default='data', help='数据库目录')
    
    args = parser.parse_args()
    
    db_path = os.path.join(args.db_dir, 'market.db')
    
    if args.check:
        print("指标同步状态:")
        df = check_indicators_status(db_path)
        if len(df) > 0:
            print(df.to_string())
        else:
            print("  无指标数据")
        return
    
    # 获取所有品种
    conn = duckdb.connect(db_path, read_only=True)
    symbols_query = "SELECT DISTINCT symbol FROM klines ORDER BY symbol"
    all_symbols = conn.execute(symbols_query).fetchdf()['symbol'].tolist()
    conn.close()
    
    # 筛选品种
    if args.symbols:
        target_symbols = [s.strip().upper() for s in args.symbols.split(',')]
    else:
        target_symbols = all_symbols
    
    print(f"开始同步技术指标: {len(target_symbols)} 个品种")
    print(f"数据库: {db_path}")
    print("=" * 60)
    
    success = 0
    failed = 0
    skipped = 0
    
    for symbol in target_symbols:
        try:
            result = sync_indicators_for_symbol(symbol, db_path)
            if result['status'] == 'success':
                print(f"  {symbol}: {result['rows']} 条记录, {len(result['indicators'])} 个指标, 最新: {result['latest_date']}")
                success += 1
            elif result['status'] == 'skip':
                print(f"  {symbol}: 跳过 - {result['reason']}")
                skipped += 1
            else:
                print(f"  {symbol}: 失败 - {result.get('error', 'unknown')}")
                failed += 1
        except Exception as e:
            print(f"  {symbol}: 错误 - {e}")
            failed += 1
    
    print("=" * 60)
    print(f"完成: {success} 成功, {skipped} 跳过, {failed} 失败")


if __name__ == '__main__':
    main()
