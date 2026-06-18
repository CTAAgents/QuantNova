"""
期货数据路由

统一管理期货数据获取、存储、更新
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb
import pandas as pd

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)


class FuturesDataRouter:
    """
    期货数据路由
    
    统一管理期货数据获取、存储、更新
    """
    
    def __init__(self, db_path: str = "data/futures.db"):
        """
        初始化数据路由
        
        Args:
            db_path: DuckDB数据库路径
        """
        self.db_path = db_path
        self.db = duckdb.connect(db_path)
        self._init_tables()
        
        # 数据源适配器
        self._tqsdk_provider = None
        self._tdx_provider = None
        self._akshare_provider = None
    
    def _init_tables(self):
        """初始化数据库表"""
        # K线数据表
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS futures_kline (
                symbol VARCHAR NOT NULL,
                date DATE NOT NULL,
                open DOUBLE,
                high DOUBLE,
                low DOUBLE,
                close DOUBLE,
                volume BIGINT,
                open_interest BIGINT,
                close_oi BIGINT,
                data_source VARCHAR,
                update_time TIMESTAMP,
                PRIMARY KEY (symbol, date)
            )
        """)
        
        # 库存数据表
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS futures_inventory (
                symbol VARCHAR NOT NULL,
                date DATE NOT NULL,
                inventory BIGINT,
                change_amount BIGINT,
                data_source VARCHAR,
                update_time TIMESTAMP,
                PRIMARY KEY (symbol, date)
            )
        """)
        
        # 仓单数据表
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS futures_warehouse_receipt (
                symbol VARCHAR NOT NULL,
                date DATE NOT NULL,
                exchange VARCHAR,
                warehouse VARCHAR,
                receipt_amount BIGINT,
                change_amount BIGINT,
                data_source VARCHAR,
                update_time TIMESTAMP,
                PRIMARY KEY (symbol, date, warehouse)
            )
        """)
        
        # 基差数据表
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS futures_basis (
                symbol VARCHAR NOT NULL,
                date DATE NOT NULL,
                spot_price DOUBLE,
                futures_price DOUBLE,
                basis DOUBLE,
                basis_rate DOUBLE,
                data_source VARCHAR,
                update_time TIMESTAMP,
                PRIMARY KEY (symbol, date)
            )
        """)
        
        # 期限结构表
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS futures_term_structure (
                symbol VARCHAR NOT NULL,
                date DATE NOT NULL,
                near_month VARCHAR,
                near_price DOUBLE,
                far_month VARCHAR,
                far_price DOUBLE,
                roll_yield DOUBLE,
                structure_type VARCHAR,
                data_source VARCHAR,
                update_time TIMESTAMP,
                PRIMARY KEY (symbol, date)
            )
        """)
        
        # 持仓排名表
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS futures_position_rank (
                symbol VARCHAR NOT NULL,
                date DATE NOT NULL,
                rank_type VARCHAR,
                rank_number INT,
                member_name VARCHAR,
                position_volume BIGINT,
                change_volume BIGINT,
                data_source VARCHAR,
                update_time TIMESTAMP,
                PRIMARY KEY (symbol, date, rank_type, rank_number)
            )
        """)
        
        # 宏观数据表
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS macro_data (
                subject VARCHAR NOT NULL,
                indicator VARCHAR NOT NULL,
                date DATE NOT NULL,
                value DOUBLE,
                unit VARCHAR,
                data_source VARCHAR,
                update_time TIMESTAMP,
                PRIMARY KEY (subject, indicator, date)
            )
        """)
        
        # 研报数据表
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS research_report (
                symbol VARCHAR,
                title VARCHAR,
                author VARCHAR,
                rating VARCHAR,
                target_price DOUBLE,
                summary TEXT,
                publish_date DATE,
                data_source VARCHAR,
                update_time TIMESTAMP,
                PRIMARY KEY (title, publish_date)
            )
        """)
        
        # 数据更新日志表
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS data_update_log (
                update_id SERIAL PRIMARY KEY,
                table_name VARCHAR NOT NULL,
                symbol VARCHAR,
                update_type VARCHAR,
                status VARCHAR,
                records_count INT,
                error_message TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                data_source VARCHAR
            )
        """)
        
        # 交易日历表
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS trading_calendar (
                date DATE PRIMARY KEY,
                is_trading_day BOOLEAN,
                exchange VARCHAR,
                update_time TIMESTAMP
            )
        """)
    
    def get_kline(self, symbol: str, timeframe: str = "daily", count: int = 100) -> pd.DataFrame:
        """
        获取K线数据
        
        Args:
            symbol: 品种代码
            timeframe: 时间周期
            count: 数据条数
            
        Returns:
            DataFrame: K线数据
        """
        # 优先从数据库读取
        df = self.db.execute(f"""
            SELECT * FROM futures_kline 
            WHERE symbol = '{symbol}' 
            ORDER BY date DESC 
            LIMIT {count}
        """).fetchdf()
        
        if len(df) >= count:
            return df.sort_values('date')
        
        # 数据不足，从TqSdk获取
        try:
            from scripts.futures.provider import FuturesProvider
            provider = FuturesProvider({})
            df = provider.get_kline(symbol, timeframe, count)
            provider.close()
            
            # 写入数据库
            self._save_kline(symbol, df)
            
            return df
        except Exception as e:
            logger.error(f"获取{symbol}K线数据失败: {e}")
            return df.sort_values('date') if len(df) > 0 else pd.DataFrame()
    
    def _save_kline(self, symbol: str, df: pd.DataFrame):
        """保存K线数据到数据库"""
        for index, row in df.iterrows():
            try:
                self.db.execute(f"""
                    INSERT OR REPLACE INTO futures_kline 
                    (symbol, date, open, high, low, close, volume, open_interest, data_source, update_time)
                    VALUES ('{symbol}', '{index.date()}', {row['open']}, {row['high']}, 
                            {row['low']}, {row['close']}, {row['volume']}, 
                            {row.get('open_interest', 0)}, 'tqsdk', CURRENT_TIMESTAMP)
                """)
            except Exception as e:
                logger.error(f"保存{symbol}K线数据失败: {e}")
    
    def get_inventory(self, symbol: str) -> pd.DataFrame:
        """获取库存数据"""
        return self.db.execute(f"""
            SELECT * FROM futures_inventory 
            WHERE symbol = '{symbol}' 
            ORDER BY date DESC 
            LIMIT 30
        """).fetchdf()
    
    def get_basis(self, symbol: str) -> pd.DataFrame:
        """获取基差数据"""
        return self.db.execute(f"""
            SELECT * FROM futures_basis 
            WHERE symbol = '{symbol}' 
            ORDER BY date DESC 
            LIMIT 30
        """).fetchdf()
    
    def get_term_structure(self, symbol: str) -> pd.DataFrame:
        """获取期限结构数据"""
        return self.db.execute(f"""
            SELECT * FROM futures_term_structure 
            WHERE symbol = '{symbol}' 
            ORDER BY date DESC 
            LIMIT 30
        """).fetchdf()
    
    def get_position_rank(self, symbol: str) -> pd.DataFrame:
        """获取持仓排名数据"""
        return self.db.execute(f"""
            SELECT * FROM futures_position_rank 
            WHERE symbol = '{symbol}' 
            ORDER BY date DESC, rank_type, rank_number
            LIMIT 100
        """).fetchdf()
    
    def get_update_log(self, days: int = 7) -> pd.DataFrame:
        """获取更新日志"""
        return self.db.execute(f"""
            SELECT * FROM data_update_log 
            WHERE start_time >= CURRENT_DATE - INTERVAL '{days} days'
            ORDER BY start_time DESC
        """).fetchdf()
    
    def close(self):
        """关闭数据库连接"""
        if self.db:
            self.db.close()
