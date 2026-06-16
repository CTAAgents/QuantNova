"""
DuckDB 存储模块

存储分析型数据：
- K线数据
- 技术指标历史
- 行情快照
"""

import os
import duckdb
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path


class DuckDBStore:
    """DuckDB 存储管理器"""
    
    def __init__(self, db_path: str = "data/market.db"):
        """
        初始化 DuckDB 存储
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self._ensure_dir()
        self._init_db()
    
    def _ensure_dir(self):
        """确保数据库目录存在"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    
    def _get_conn(self) -> duckdb.DuckDBPyConnection:
        """获取数据库连接"""
        return duckdb.connect(self.db_path)
    
    def _init_db(self):
        """初始化数据库表结构"""
        conn = self._get_conn()
        try:
            # 1. K线数据表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS klines (
                    symbol VARCHAR NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    timeframe VARCHAR NOT NULL DEFAULT 'daily',
                    
                    -- OHLCV
                    open DOUBLE,
                    high DOUBLE,
                    low DOUBLE,
                    close DOUBLE,
                    volume DOUBLE,
                    open_interest DOUBLE,
                    
                    -- 元数据
                    source VARCHAR DEFAULT 'tqsdk',
                    created_at TIMESTAMP DEFAULT current_timestamp,
                    
                    -- 主键
                    PRIMARY KEY (symbol, timestamp, timeframe)
                )
            """)
            
            # 2. 技术指标历史表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS indicators (
                    symbol VARCHAR NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    indicator_name VARCHAR NOT NULL,
                    value DOUBLE,
                    
                    -- 元数据
                    parameters VARCHAR,
                    created_at TIMESTAMP DEFAULT current_timestamp,
                    
                    -- 主键
                    PRIMARY KEY (symbol, timestamp, indicator_name)
                )
            """)
            
            # 3. 行情快照表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS quotes (
                    symbol VARCHAR NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    
                    -- 行情数据
                    last_price DOUBLE,
                    open_interest DOUBLE,
                    volume DOUBLE,
                    bid_price1 DOUBLE,
                    ask_price1 DOUBLE,
                    highest DOUBLE,
                    lowest DOUBLE,
                    pre_close DOUBLE,
                    
                    -- 元数据
                    source VARCHAR DEFAULT 'tqsdk',
                    created_at TIMESTAMP DEFAULT current_timestamp,
                    
                    -- 主键
                    PRIMARY KEY (symbol, timestamp)
                )
            """)
            
            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_klines_symbol ON klines(symbol)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_klines_time ON klines(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_indicators_symbol ON indicators(symbol)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_indicators_name ON indicators(indicator_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_quotes_symbol ON quotes(symbol)")
            
        finally:
            conn.close()
    
    # ============================================================
    # K线数据操作
    # ============================================================
    
    def save_klines(self, symbol: str, df: pd.DataFrame, timeframe: str = 'daily',
                   source: str = 'tqsdk'):
        """
        保存K线数据
        
        Args:
            symbol: 品种代码
            df: DataFrame，包含 date/open/high/low/close/volume/open_interest
            timeframe: 时间周期
            source: 数据来源
        """
        if df is None or df.empty:
            return
        
        # 准备数据
        df = df.copy()
        
        # 确保列名正确
        column_mapping = {
            'date': 'timestamp',
            'datetime': 'timestamp',
        }
        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
        
        # 添加必要列
        df['symbol'] = symbol
        df['timeframe'] = timeframe
        df['source'] = source
        df['created_at'] = datetime.now()
        
        # 确保 timestamp 列存在
        if 'timestamp' not in df.columns:
            raise ValueError("DataFrame must have 'date' or 'timestamp' column")
        
        # 转换 timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # 选择需要的列
        columns = ['symbol', 'timestamp', 'timeframe', 'open', 'high', 'low', 'close', 
                   'volume', 'open_interest', 'source', 'created_at']
        df = df[[c for c in columns if c in df.columns]]
        
        # 填充缺失列
        for col in columns:
            if col not in df.columns:
                df[col] = None
        
        conn = self._get_conn()
        try:
            # 删除已有数据（避免重复）
            min_date = df['timestamp'].min()
            max_date = df['timestamp'].max()
            
            conn.execute("""
                DELETE FROM klines 
                WHERE symbol = ? AND timeframe = ? 
                AND timestamp >= ? AND timestamp <= ?
            """, [symbol, timeframe, min_date, max_date])
            
            # 插入新数据
            conn.execute("""
                INSERT INTO klines (symbol, timestamp, timeframe, open, high, low, close, 
                                   volume, open_interest, source, created_at)
                SELECT symbol, timestamp, timeframe, open, high, low, close, 
                       volume, open_interest, source, created_at
                FROM df
            """)
            
        finally:
            conn.close()
    
    def get_klines(self, symbol: str, days: int = 120, timeframe: str = 'daily',
                  end_date: datetime = None) -> Optional[pd.DataFrame]:
        """
        获取K线数据
        
        Args:
            symbol: 品种代码
            days: 获取天数（记录条数）
            timeframe: 时间周期
            end_date: 结束日期
        
        Returns:
            DataFrame
        """
        conn = self._get_conn()
        try:
            # 获取最近N条记录（不依赖日期范围）
            df = conn.execute("""
                SELECT timestamp as date, open, high, low, close, volume, open_interest
                FROM klines
                WHERE symbol = ? AND timeframe = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, [symbol, timeframe, days]).fetchdf()
            
            if df.empty:
                return None
            
            # 转换日期格式并按时间正序排列
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            
            return df
            
        finally:
            conn.close()
    
    def get_latest_kline(self, symbol: str, timeframe: str = 'daily') -> Optional[Dict[str, Any]]:
        """
        获取最新K线数据
        
        Args:
            symbol: 品种代码
            timeframe: 时间周期
        
        Returns:
            K线数据字典
        """
        conn = self._get_conn()
        try:
            result = conn.execute("""
                SELECT * FROM klines
                WHERE symbol = ? AND timeframe = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, [symbol, timeframe]).fetchone()
            
            if result:
                columns = ['symbol', 'timestamp', 'timeframe', 'open', 'high', 'low', 'close',
                          'volume', 'open_interest', 'source', 'created_at']
                return dict(zip(columns, result))
            return None
            
        finally:
            conn.close()
    
    def get_kline_date_range(self, symbol: str, timeframe: str = 'daily') -> Optional[Dict[str, Any]]:
        """
        获取K线数据日期范围
        
        Args:
            symbol: 品种代码
            timeframe: 时间周期
        
        Returns:
            日期范围字典
        """
        conn = self._get_conn()
        try:
            result = conn.execute("""
                SELECT 
                    MIN(timestamp) as earliest,
                    MAX(timestamp) as latest,
                    COUNT(*) as count
                FROM klines
                WHERE symbol = ? AND timeframe = ?
            """, [symbol, timeframe]).fetchone()
            
            if result and result[0]:
                return {
                    'earliest': result[0],
                    'latest': result[1],
                    'count': result[2]
                }
            return None
            
        finally:
            conn.close()
    
    # ============================================================
    # 技术指标操作
    # ============================================================
    
    def save_indicators(self, symbol: str, df: pd.DataFrame, 
                       indicator_names: List[str] = None):
        """
        保存技术指标数据
        
        Args:
            symbol: 品种代码
            df: DataFrame，包含指标列
            indicator_names: 指标名称列表
        """
        if df is None or df.empty:
            return
        
        # 确定指标列
        if indicator_names is None:
            # 自动检测指标列（排除 date/timestamp 和 OHLCV）
            exclude_cols = {'date', 'timestamp', 'datetime', 'open', 'high', 'low', 'close', 
                          'volume', 'open_interest'}
            indicator_names = [col for col in df.columns if col.lower() not in exclude_cols]
        
        if not indicator_names:
            return
        
        conn = self._get_conn()
        try:
            # 准备数据
            records = []
            
            for _, row in df.iterrows():
                timestamp = row.get('date') or row.get('timestamp') or row.get('datetime')
                if timestamp is None:
                    continue
                
                timestamp = pd.to_datetime(timestamp)
                
                for indicator_name in indicator_names:
                    if indicator_name in row.index and pd.notna(row[indicator_name]):
                        records.append({
                            'symbol': symbol,
                            'timestamp': timestamp,
                            'indicator_name': indicator_name,
                            'value': float(row[indicator_name]),
                            'created_at': datetime.now()
                        })
            
            if not records:
                return
            
            # 转换为 DataFrame
            indicators_df = pd.DataFrame(records)
            
            # 删除已有数据
            min_date = indicators_df['timestamp'].min()
            max_date = indicators_df['timestamp'].max()
            
            conn.execute("""
                DELETE FROM indicators 
                WHERE symbol = ? AND timestamp >= ? AND timestamp <= ?
                AND indicator_name IN ({})
            """.format(','.join(['?' * len(indicator_names)])), 
                [symbol, min_date, max_date] + indicator_names)
            
            # 插入新数据
            conn.execute("""
                INSERT INTO indicators (symbol, timestamp, indicator_name, value, created_at)
                SELECT symbol, timestamp, indicator_name, value, created_at
                FROM indicators_df
            """)
            
        finally:
            conn.close()
    
    def get_indicators(self, symbol: str, indicator_names: List[str] = None,
                      days: int = 120) -> Optional[pd.DataFrame]:
        """
        获取技术指标数据
        
        Args:
            symbol: 品种代码
            indicator_names: 指标名称列表
            days: 获取天数
        
        Returns:
            DataFrame
        """
        conn = self._get_conn()
        try:
            start_date = datetime.now() - timedelta(days=days)
            
            if indicator_names:
                placeholders = ','.join(['?' * len(indicator_names)])
                df = conn.execute(f"""
                    SELECT symbol, timestamp, indicator_name, value
                    FROM indicators
                    WHERE symbol = ? AND timestamp >= ?
                    AND indicator_name IN ({placeholders})
                    ORDER BY timestamp, indicator_name
                """, [symbol, start_date] + indicator_names).fetchdf()
            else:
                df = conn.execute("""
                    SELECT symbol, timestamp, indicator_name, value
                    FROM indicators
                    WHERE symbol = ? AND timestamp >= ?
                    ORDER BY timestamp, indicator_name
                """, [symbol, start_date]).fetchdf()
            
            if df.empty:
                return None
            
            # 转换为宽表格式
            pivot_df = df.pivot(index='timestamp', columns='indicator_name', values='value')
            pivot_df = pivot_df.reset_index()
            pivot_df = pivot_df.rename(columns={'timestamp': 'date'})
            
            return pivot_df
            
        finally:
            conn.close()
    
    # ============================================================
    # 行情快照操作
    # ============================================================
    
    def save_quote(self, symbol: str, quote: Dict[str, Any], source: str = 'tqsdk'):
        """
        保存行情快照
        
        Args:
            symbol: 品种代码
            quote: 行情数据
            source: 数据来源
        """
        conn = self._get_conn()
        try:
            timestamp = quote.get('timestamp', datetime.now())
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            conn.execute("""
                INSERT INTO quotes (symbol, timestamp, last_price, open_interest, volume,
                                   bid_price1, ask_price1, highest, lowest, pre_close, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                symbol, timestamp,
                quote.get('last_price'),
                quote.get('open_interest'),
                quote.get('volume'),
                quote.get('bid_price1'),
                quote.get('ask_price1'),
                quote.get('highest'),
                quote.get('lowest'),
                quote.get('pre_close'),
                source
            ])
            
        finally:
            conn.close()
    
    def get_latest_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取最新行情快照
        
        Args:
            symbol: 品种代码
        
        Returns:
            行情数据字典
        """
        conn = self._get_conn()
        try:
            result = conn.execute("""
                SELECT * FROM quotes
                WHERE symbol = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, [symbol]).fetchone()
            
            if result:
                columns = ['symbol', 'timestamp', 'last_price', 'open_interest', 'volume',
                          'bid_price1', 'ask_price1', 'highest', 'lowest', 'pre_close',
                          'source', 'created_at']
                return dict(zip(columns, result))
            return None
            
        finally:
            conn.close()
    
    # ============================================================
    # 统计查询
    # ============================================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取数据库统计信息
        
        Returns:
            统计信息字典
        """
        conn = self._get_conn()
        try:
            stats = {}
            
            # K线统计
            result = conn.execute("""
                SELECT 
                    COUNT(DISTINCT symbol) as symbols,
                    COUNT(*) as records,
                    MIN(timestamp) as earliest,
                    MAX(timestamp) as latest
                FROM klines
            """).fetchone()
            
            stats['klines'] = {
                'symbols': result[0],
                'records': result[1],
                'earliest': str(result[2]) if result[2] else None,
                'latest': str(result[3]) if result[3] else None
            }
            
            # 指标统计
            result = conn.execute("""
                SELECT 
                    COUNT(DISTINCT symbol) as symbols,
                    COUNT(DISTINCT indicator_name) as indicators,
                    COUNT(*) as records
                FROM indicators
            """).fetchone()
            
            stats['indicators'] = {
                'symbols': result[0],
                'indicator_types': result[1],
                'records': result[2]
            }
            
            # 行情统计
            result = conn.execute("""
                SELECT 
                    COUNT(DISTINCT symbol) as symbols,
                    COUNT(*) as records,
                    MAX(timestamp) as latest
                FROM quotes
            """).fetchone()
            
            stats['quotes'] = {
                'symbols': result[0],
                'records': result[1],
                'latest': str(result[2]) if result[2] else None
            }
            
            # 数据库大小
            if os.path.exists(self.db_path):
                stats['db_size_mb'] = os.path.getsize(self.db_path) / (1024 * 1024)
            
            return stats
            
        finally:
            conn.close()
    
    def list_symbols(self) -> List[str]:
        """
        列出所有有数据的品种
        
        Returns:
            品种代码列表
        """
        conn = self._get_conn()
        try:
            result = conn.execute("""
                SELECT DISTINCT symbol FROM klines
                UNION
                SELECT DISTINCT symbol FROM indicators
                UNION
                SELECT DISTINCT symbol FROM quotes
                ORDER BY symbol
            """).fetchdf()
            
            return result['symbol'].tolist()
            
        finally:
            conn.close()
