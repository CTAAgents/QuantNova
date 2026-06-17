"""
技术指标同步脚本（v2.0）

使用 TqSdk ta 模块计算 70 个技术指标并保存到 DuckDB。

功能：
1. 从 DuckDB 读取 K 线数据
2. 使用 TqSdk ta 模块计算所有技术指标
3. 将指标保存到 DuckDB 的 indicators 表

使用方式：
    python tools/sync_indicators.py              # 同步所有品种的技术指标
    python tools/sync_indicators.py --symbols JD,RB  # 同步指定品种
    python tools/sync_indicators.py --check      # 检查指标状态
    python tools/sync_indicators.py --fast       # 仅计算核心指标（32个）
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


def compute_all_indicators(df: pd.DataFrame, fast: bool = False) -> Dict[str, pd.Series]:
    """
    从 K 线数据计算所有 TqSdk 技术指标
    
    Args:
        df: DataFrame with columns: open, high, low, close, volume
        fast: True=仅计算核心指标（32个），False=计算全部指标（70个）
        
    Returns:
        Dict of indicator name -> Series
    """
    indicators = {}
    
    # ===== A类：核心指标（必须） =====
    
    # 均线类
    for n in [5, 10, 20, 60, 100]:
        indicators[f'ma{n}'] = df['close'].rolling(n).mean()
    
    for n in [20, 60]:
        indicators[f'ema{n}'] = df['close'].ewm(span=n, adjust=False).mean()
    
    # ATR
    period = 14
    tr1 = df['high'] - df['low']
    tr2 = abs(df['high'] - df['close'].shift(1))
    tr3 = abs(df['low'] - df['close'].shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    indicators['atr'] = tr.rolling(period).mean()
    
    # ADX, +DI, -DI
    adx_period = 14
    plus_dm = df['high'] - df['high'].shift(1)
    minus_dm = df['low'].shift(1) - df['low']
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    atr_smooth = tr.ewm(alpha=1/adx_period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/adx_period, adjust=False).mean() / atr_smooth
    minus_di = 100 * minus_dm.ewm(alpha=1/adx_period, adjust=False).mean() / atr_smooth
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.ewm(alpha=1/6, adjust=False).mean()
    indicators['plus_di'] = plus_di
    indicators['minus_di'] = minus_di
    indicators['adx'] = adx
    indicators['adxr'] = (adx + adx.shift(6)) / 2
    
    # RSI (Wilder's smoothing)
    rsi_period = 14
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta.where(delta < 0, 0))
    avg_gain = gain.ewm(alpha=1/rsi_period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/rsi_period, adjust=False).mean()
    rs = avg_gain / avg_loss
    indicators['rsi'] = 100 - (100 / (1 + rs))
    
    # KDJ
    k_period = 9
    low_min = df['low'].rolling(k_period).min()
    high_max = df['high'].rolling(k_period).max()
    rsv = 100 * (df['close'] - low_min) / (high_max - low_min)
    indicators['kdj_k'] = rsv.ewm(com=2, adjust=False).mean()
    indicators['kdj_d'] = indicators['kdj_k'].ewm(com=2, adjust=False).mean()
    indicators['kdj_j'] = 3 * indicators['kdj_k'] - 2 * indicators['kdj_d']
    
    # Williams %R
    wr_period = 14
    high_max_wr = df['high'].rolling(wr_period).max()
    low_min_wr = df['low'].rolling(wr_period).min()
    indicators['wr'] = -100 * (high_max_wr - df['close']) / (high_max_wr - low_min_wr)
    
    # CCI
    cci_period = 14
    tp = (df['high'] + df['low'] + df['close']) / 3
    sma_tp = tp.rolling(cci_period).mean()
    mad = tp.rolling(cci_period).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True)
    indicators['cci'] = (tp - sma_tp) / (0.015 * mad)
    
    # MACD
    fast_ma = df['close'].ewm(span=12, adjust=False).mean()
    slow_ma = df['close'].ewm(span=26, adjust=False).mean()
    macd_line = fast_ma - slow_ma
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    indicators['macd'] = macd_line
    indicators['macd_signal'] = macd_signal
    indicators['macd_hist'] = macd_line - macd_signal
    
    # ROC
    roc_period = 10
    indicators['roc'] = (df['close'] - df['close'].shift(roc_period)) / df['close'].shift(roc_period) * 100
    
    # Bollinger Bands
    bb_period = 20
    bb_mid = df['close'].rolling(bb_period).mean()
    bb_std = df['close'].rolling(bb_period).std()
    indicators['bb_upper'] = bb_mid + 2 * bb_std
    indicators['bb_mid'] = bb_mid
    indicators['bb_lower'] = bb_mid - 2 * bb_std
    indicators['bb_width'] = (indicators['bb_upper'] - indicators['bb_lower']) / bb_mid
    
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
    
    # TSI
    tsi_long, tsi_short = 25, 13
    momentum = df['close'].diff()
    double_smooth = momentum.ewm(span=tsi_long, adjust=False).mean().ewm(span=tsi_short, adjust=False).mean()
    double_smooth_abs = momentum.abs().ewm(span=tsi_long, adjust=False).mean().ewm(span=tsi_short, adjust=False).mean()
    indicators['tsi'] = 100 * double_smooth / double_smooth_abs
    
    # ATR Ratio
    atr_short = tr.rolling(6).mean()
    atr_long = tr.rolling(24).mean()
    indicators['atr_ratio'] = atr_short / atr_long
    
    # Donchian Channel
    dc_period = 20
    indicators['dc_upper'] = df['high'].rolling(dc_period).max()
    indicators['dc_lower'] = df['low'].rolling(dc_period).min()
    indicators['dc_middle'] = (indicators['dc_upper'] + indicators['dc_lower']) / 2
    
    if fast:
        return indicators
    
    # ===== B类：扩展指标 =====
    
    # EMA2
    indicators['ema2'] = df['close'].ewm(span=2, adjust=False).mean()
    
    # BBI
    indicators['bbi'] = (df['close'].rolling(3).mean() + df['close'].rolling(6).mean() + 
                         df['close'].rolling(12).mean() + df['close'].rolling(24).mean()) / 4
    
    # DMA
    indicators['dma'] = df['close'].rolling(10).mean() - df['close'].rolling(50).mean()
    
    # EXPMA
    indicators['expma12'] = df['close'].ewm(span=12, adjust=False).mean()
    indicators['expma50'] = df['close'].ewm(span=50, adjust=False).mean()
    
    # TRMA
    indicators['trma'] = df['close'].rolling(20).apply(lambda x: np.mean(np.arange(1, len(x)+1) * x / np.sum(np.arange(1, len(x)+1))), raw=True)
    
    # SAR (简化版)
    sar_period = 4
    sar_af = 0.02
    sar_max = 0.2
    sar = pd.Series(index=df.index, dtype=float)
    sar.iloc[0] = df['low'].iloc[0]
    for i in range(1, len(df)):
        if df['close'].iloc[i] > sar.iloc[i-1]:
            sar.iloc[i] = min(df['low'].iloc[i], sar.iloc[i-1] + sar_af * (df['high'].iloc[i] - sar.iloc[i-1]))
        else:
            sar.iloc[i] = max(df['high'].iloc[i], sar.iloc[i-1] - sar_af * (sar.iloc[i-1] - df['low'].iloc[i]))
    indicators['sar'] = sar
    
    # ENV
    env_period = 14
    env_ma = df['close'].rolling(env_period).mean()
    indicators['env_upper'] = env_ma * 1.06
    indicators['env_lower'] = env_ma * 0.94
    
    # BIAS
    for n in [6, 12, 24]:
        ma_n = df['close'].rolling(n).mean()
        indicators[f'bias{n}'] = (df['close'] - ma_n) / ma_n * 100
    
    # PSY
    psy_period = 12
    up_days = (df['close'] > df['close'].shift(1)).rolling(psy_period).sum()
    indicators['psy'] = up_days / psy_period * 100
    
    # DPO
    dpo_period = 20
    indicators['dpo'] = df['close'] - df['close'].rolling(dpo_period).mean().shift(dpo_period // 2 + 1)
    
    # MTM
    mtm_period = 12
    indicators['mtm'] = df['close'] - df['close'].shift(mtm_period)
    indicators['mtm_ma'] = indicators['mtm'].rolling(6).mean()
    
    # ADTM
    adtm_period = 23
    dtm = df['high'] - df['high'].shift(1)
    dbm = df['low'].shift(1) - df['low']
    dtm = dtm.where(dtm > 0, 0)
    dbm = dbm.where(dbm > 0, 0)
    adtm_val = (dtm - dbm) / dtm.rolling(adtm_period).mean()
    indicators['adtm'] = adtm_val
    
    # DDI
    ddi_period = 13
    ddz = abs(df['high'] - df['high'].shift(1)) - abs(df['low'] - df['low'].shift(1))
    indicators['ddi'] = ddz.ewm(span=ddi_period, adjust=False).mean()
    
    # OBV
    obv = pd.Series(0.0, index=df.index)
    for i in range(1, len(df)):
        if df['close'].iloc[i] > df['close'].iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] + df['volume'].iloc[i]
        elif df['close'].iloc[i] < df['close'].iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] - df['volume'].iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i-1]
    indicators['obv'] = obv
    
    # AD (Accumulation/Distribution)
    clv = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low'])
    clv = clv.fillna(0)
    indicators['ad'] = (clv * df['volume']).cumsum()
    
    # MFI
    mfi_period = 14
    tp_mfi = (df['high'] + df['low'] + df['close']) / 3
    mf = tp_mfi * df['volume']
    pos_mf = mf.where(tp_mfi > tp_mfi.shift(1), 0)
    neg_mf = mf.where(tp_mfi < tp_mfi.shift(1), 0)
    mfi_ratio = pos_mf.rolling(mfi_period).sum() / neg_mf.rolling(mfi_period).sum()
    indicators['mfi'] = 100 - (100 / (1 + mfi_ratio))
    
    # VR
    vr_period = 26
    up_vol = df['volume'].where(df['close'] > df['close'].shift(1), 0)
    down_vol = df['volume'].where(df['close'] < df['close'].shift(1), 0)
    eq_vol = df['volume'].where(df['close'] == df['close'].shift(1), 0)
    indicators['vr'] = (up_vol.rolling(vr_period).sum() + eq_vol.rolling(vr_period).sum() / 2) / \
                       (down_vol.rolling(vr_period).sum() + eq_vol.rolling(vr_period).sum() / 2) * 100
    
    # ARBR
    arbr_period = 26
    ar_up = (df['high'] - df['open']).rolling(arbr_period).sum()
    ar_down = (df['open'] - df['low']).rolling(arbr_period).sum()
    indicators['ar'] = ar_up / ar_down * 100
    indicators['br'] = (df['high'] - df['close'].shift(1)).rolling(arbr_period).sum() / \
                       (df['close'].shift(1) - df['low']).rolling(arbr_period).sum() * 100
    
    # ASI
    asi_period = 6
    lc = df['close'].shift(1)
    r1 = abs(df['high'] - lc)
    r2 = abs(df['low'] - lc)
    r3 = abs(df['high'] - df['low'].shift(1))
    r4 = abs(lc - df['open'].shift(1))
    r = pd.concat([r1, r2, r3, r4], axis=1).max(axis=1)
    si = 50 * (df['close'] - lc + 0.5 * (df['close'] - df['open']) + 0.25 * (lc - df['open'].shift(1))) / r
    si = si.fillna(0)
    indicators['asi'] = si.rolling(asi_period).sum()
    
    # WVAD
    wvad_period = 24
    indicators['wvad'] = ((df['close'] - df['open']) / (df['high'] - df['low']) * df['volume']).rolling(wvad_period).sum()
    
    # PVT
    pvt = pd.Series(0.0, index=df.index)
    for i in range(1, len(df)):
        if df['close'].iloc[i-1] != 0:
            pvt.iloc[i] = pvt.iloc[i-1] + df['volume'].iloc[i] * (df['close'].iloc[i] - df['close'].iloc[i-1]) / df['close'].iloc[i-1]
        else:
            pvt.iloc[i] = pvt.iloc[i-1]
    indicators['pvt'] = pvt
    
    # CR
    cr_period = 26
    mid_cr = (df['high'].shift(1) + df['low'].shift(1) + df['close'].shift(1)) / 3
    cr_up = (df['high'] - mid_cr).clip(lower=0).rolling(cr_period).sum()
    cr_down = (mid_cr - df['low']).clip(lower=0).rolling(cr_period).sum()
    indicators['cr'] = cr_up / cr_down * 100
    
    # BOLL 宽度（已计算）
    
    # BBIBOLL
    bbiboll_period = 10
    indicators['bbiboll'] = indicators['bbi'].rolling(bbiboll_period).std() * 3
    
    # MASS
    mass_period = 9
    mass_ma1 = (df['high'] - df['low']).ewm(span=9, adjust=False).mean()
    mass_ma2 = mass_ma1.ewm(span=9, adjust=False).mean()
    indicators['mass'] = (mass_ma1 / mass_ma2).rolling(mass_period).sum()
    
    # VROC
    vroc_period = 12
    indicators['vroc'] = (df['volume'] - df['volume'].shift(vroc_period)) / df['volume'].shift(vroc_period) * 100
    
    # HCL
    hcl_period = 20
    indicators['hcl_upper'] = df['high'].rolling(hcl_period).mean()
    indicators['hcl_lower'] = df['low'].rolling(hcl_period).mean()
    indicators['hcl_mid'] = (indicators['hcl_upper'] + indicators['hcl_lower']) / 2
    
    # 均线斜率
    for n in [20, 60]:
        ma_n = indicators[f'ma{n}']
        indicators[f'ma{n}_slope'] = (ma_n - ma_n.shift(3)) / ma_n.shift(3) * 100
    
    # 均线间距
    indicators['spread_ma20_ma60'] = (indicators['ma20'] - indicators['ma60']) / indicators['ma60'] * 100
    
    # Hurst 指数
    hurst_period = 50
    def calc_hurst(series):
        if len(series) < hurst_period:
            return np.nan
        ts = series.values
        mean_ts = np.mean(ts)
        deviations = np.cumsum(ts - mean_ts)
        r = np.max(deviations) - np.min(deviations)
        s = np.std(ts)
        if s == 0 or r == 0:
            return np.nan
        return np.log(r/s) / np.log(len(ts))
    indicators['hurst'] = df['close'].rolling(hurst_period).apply(calc_hurst, raw=False)
    
    # ADX ROC
    indicators['adx_roc'] = (adx - adx.shift(5)) / 5
    
    # EMA 斜率强度
    indicators['ema_slope_strength'] = (indicators['ema20'] - indicators['ema20'].shift(1)) / indicators['atr']
    
    # 七维复合趋势强度
    indicators['trend_strength_composite'] = (
        indicators['tsi'].rank(pct=True) * 0.25 +
        indicators['er'].rank(pct=True) * 0.25 +
        indicators['ema_slope_strength'].rank(pct=True) * 0.15 +
        indicators['atr_ratio'].rank(pct=True) * 0.10 +
        indicators['r_squared'].rank(pct=True) * 0.10 +
        indicators['hurst'].rank(pct=True) * 0.08 +
        indicators['adx_roc'].rank(pct=True) * 0.07
    )
    
    return indicators


def sync_indicators_for_symbol(symbol: str, db_path: str = 'data/market.db', fast: bool = False) -> Dict[str, Any]:
    """
    为单个品种同步技术指标
    """
    conn = duckdb.connect(db_path)
    
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
    indicators = compute_all_indicators(df, fast=fast)
    
    # 创建 indicators 表（如果不存在）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS indicators (
            symbol VARCHAR,
            timestamp TIMESTAMP,
            indicator_name VARCHAR,
            value DOUBLE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 删除旧数据
    conn.execute(f"DELETE FROM indicators WHERE symbol = '{symbol}'")
    
    # 构建记录
    records = []
    for _, row in df.iterrows():
        ts = row['timestamp']
        for name, series in indicators.items():
            idx = df.index[df['timestamp'] == ts]
            if len(idx) > 0:
                val = series.loc[idx[0]]
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
        'indicators': len(indicators),
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
    parser = argparse.ArgumentParser(description='技术指标同步脚本 v2.0')
    parser.add_argument('--symbols', type=str, help='品种列表（逗号分隔）')
    parser.add_argument('--check', action='store_true', help='检查指标状态')
    parser.add_argument('--fast', action='store_true', help='仅计算核心指标（32个）')
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
    
    mode = "核心指标（32个）" if args.fast else "全部指标（70+个）"
    print(f"开始同步技术指标: {len(target_symbols)} 个品种, 模式={mode}")
    print(f"数据库: {db_path}")
    print("=" * 60)
    
    success = 0
    failed = 0
    skipped = 0
    
    for symbol in target_symbols:
        try:
            result = sync_indicators_for_symbol(symbol, db_path, fast=args.fast)
            if result['status'] == 'success':
                print(f"  {symbol}: {result['rows']} 条记录, {result['indicators']} 个指标, 最新: {result['latest_date']}")
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
