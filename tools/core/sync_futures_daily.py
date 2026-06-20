#!/usr/bin/env python3
"""
期货数据每日同步脚本

功能：
1. 获取所有期货品种列表（通过FuturesProvider.get_symbols()）
2. 获取过去250个交易日的日线数据
3. 保存到DuckDB数据库 data/futures.db
4. 计算技术指标并保存
5. 记录更新日志
6. 跳过获取失败的品种，继续处理其他品种

使用方式：
    python tools/core/sync_futures_daily.py [--days 250] [--force]
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "scripts"))

from futures.provider import FuturesProvider, FUTURES_SYMBOLS
from indicators.indicator_engine import IndicatorEngine

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(project_root / "data" / "sync_futures.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class FuturesDailySync:
    """期货每日数据同步器"""
    
    def __init__(self, db_path: str = "data/futures.db", days: int = 250):
        """
        初始化同步器
        
        Args:
            db_path: DuckDB数据库路径
            days: 获取天数（交易日）
        """
        self.db_path = project_root / db_path
        self.days = days
        self.conn = None
        
        # 确保目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化DuckDB连接
        self._init_duckdb()
        
        # 初始化TqSdk数据源
        self._init_tqsdk()
        
        # 同步结果统计
        self.stats = {
            "total_symbols": 0,
            "synced": 0,
            "failed": 0,
            "skipped": 0,
            "indicators_computed": 0,
            "start_time": None,
            "end_time": None,
        }
    
    def _init_duckdb(self):
        """初始化DuckDB数据库"""
        try:
            import duckdb
            
            # 清理可能存在的锁文件
            self._cleanup_lock_files()
            
            # 连接数据库（使用read_only=False确保可以写入）
            self.conn = duckdb.connect(str(self.db_path), read_only=False)
            self._create_tables()
            logger.info(f"DuckDB连接成功: {self.db_path}")
        except ImportError:
            logger.error("DuckDB未安装，请运行: pip install duckdb")
            raise
        except Exception as e:
            logger.error(f"DuckDB连接失败: {e}")
            # 尝试删除可能损坏的数据库文件
            if os.path.exists(self.db_path):
                try:
                    os.remove(self.db_path)
                    logger.info(f"删除可能损坏的数据库文件: {self.db_path}")
                    # 清理锁文件
                    self._cleanup_lock_files()
                    # 重新连接
                    self.conn = duckdb.connect(str(self.db_path), read_only=False)
                    self._create_tables()
                    logger.info(f"DuckDB重新连接成功: {self.db_path}")
                except Exception as e2:
                    logger.error(f"DuckDB重新连接失败: {e2}")
                    raise
            else:
                raise
    
    def _create_tables(self):
        """创建数据库表"""
        if not self.conn:
            return
        
        # 1. K线数据表
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS klines (
            symbol VARCHAR NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            timeframe VARCHAR NOT NULL,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume DOUBLE,
            open_interest DOUBLE,
            source VARCHAR DEFAULT 'tqsdk',
            created_at TIMESTAMP DEFAULT current_timestamp,
            PRIMARY KEY (symbol, timestamp, timeframe)
        )
        """)
        
        # 2. 技术指标表
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS indicators (
            symbol VARCHAR NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            indicator_name VARCHAR NOT NULL,
            value DOUBLE,
            parameters VARCHAR,
            created_at TIMESTAMP DEFAULT current_timestamp,
            PRIMARY KEY (symbol, timestamp, indicator_name)
        )
        """)
        
        # 3. 同步日志表
        self.conn.execute("""
        CREATE TABLE IF NOT EXISTS sync_log (
            sync_id VARCHAR PRIMARY KEY,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            total_symbols INTEGER,
            synced_count INTEGER,
            failed_count INTEGER,
            skipped_count INTEGER,
            indicators_count INTEGER,
            status VARCHAR,
            error_message VARCHAR,
            details VARCHAR
        )
        """)
        
        # 创建索引
        try:
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_klines_symbol_time ON klines(symbol, timestamp)")
            self.conn.execute("CREATE INDEX IF NOT EXISTS idx_indicators_symbol_name ON indicators(symbol, indicator_name)")
        except:
            pass
    
    def _init_tqsdk(self):
        """初始化TqSdk数据源"""
        try:
            from tqsdk import TqApi, TqAuth
            
            # 检查环境变量
            user = os.environ.get("TQ_USER")
            password = os.environ.get("TQ_PASSWORD")
            
            if not user or not password:
                logger.warning("TqSdk环境变量未设置，将使用模拟数据")
                self.tqsdk_api = None
                return
            
            # 连接TqSdk
            self.tqsdk_api = TqApi(auth=TqAuth(user, password))
            logger.info("TqSdk连接成功")
            
        except ImportError:
            logger.warning("TqSdk未安装，请运行: pip install tqsdk")
            self.tqsdk_api = None
        except Exception as e:
            logger.error(f"TqSdk连接失败: {e}")
            self.tqsdk_api = None
    
    def _get_main_contract_symbol(self, symbol: str) -> str:
        """获取主力连续合约代码"""
        # 交易所映射
        exchange_map = {
            "RB": "SHFE", "HC": "SHFE", "SS": "SHFE", "CU": "SHFE",
            "AL": "SHFE", "ZN": "SHFE", "PB": "SHFE", "NI": "SHFE", "SN": "SHFE",
            "AU": "SHFE", "AG": "SHFE", "FU": "SHFE", "BU": "SHFE", "SP": "SHFE",
            "RU": "SHFE", "NR": "INE", "SC": "INE",
            "I": "DCE", "J": "DCE", "JM": "DCE", "M": "DCE", "Y": "DCE",
            "P": "DCE", "C": "DCE", "CS": "DCE", "A": "DCE", "B": "DCE",
            "RR": "DCE", "L": "DCE", "V": "DCE", "EB": "DCE", "EG": "DCE",
            "PG": "DCE", "JD": "DCE", "LH": "DCE",
            "TA": "CZCE", "MA": "CZCE", "SR": "CZCE", "CF": "CZCE",
            "RM": "CZCE", "OI": "CZCE", "FG": "CZCE", "SA": "CZCE",
            "ZC": "CZCE", "SF": "CZCE", "SM": "CZCE", "AP": "CZCE",
            "CJ": "CZCE", "PK": "CZCE",
            "IF": "CFFEX", "IC": "CFFEX", "IH": "CFFEX", "IM": "CFFEX",
            "T": "CFFEX", "TF": "CFFEX", "TS": "CFFEX",
        }
        
        exchange = exchange_map.get(symbol, "UNKNOWN")
        symbol_lower = symbol.lower()
        return f"KQ.m@{exchange}.{symbol_lower}"
    
    def _fetch_kline_data(self, symbol: str) -> pd.DataFrame:
        """
        获取K线数据
        
        Args:
            symbol: 品种代码
            
        Returns:
            DataFrame: K线数据
        """
        if self.tqsdk_api is None:
            logger.warning(f"TqSdk未连接，无法获取{symbol}数据")
            return pd.DataFrame()
        
        try:
            # 获取主力连续合约
            contract = self._get_main_contract_symbol(symbol)
            
            # 获取日线数据（86400秒 = 1天）
            # 添加超时处理
            import threading
            result = [None]
            error = [None]
            
            def fetch_data():
                try:
                    klines = self.tqsdk_api.get_kline_serial(contract, 86400, self.days)
                    result[0] = klines
                except Exception as e:
                    error[0] = e
            
            # 创建线程并设置超时
            thread = threading.Thread(target=fetch_data)
            thread.daemon = True
            thread.start()
            thread.join(timeout=30)  # 30秒超时
            
            if thread.is_alive():
                logger.warning(f"获取{symbol}数据超时，跳过")
                return pd.DataFrame()
            
            if error[0]:
                raise error[0]
            
            klines = result[0]
            if klines is None:
                logger.warning(f"获取{symbol}数据为空")
                return pd.DataFrame()
            
            # 转换为DataFrame
            df = pd.DataFrame({
                "timestamp": pd.to_datetime(klines["datetime"], unit="ns"),
                "open": klines["open"],
                "high": klines["high"],
                "low": klines["low"],
                "close": klines["close"],
                "volume": klines["volume"],
                "open_interest": klines.get("open_oi", 0),
            })
            
            df.set_index("timestamp", inplace=True)
            
            # 数据清洗
            df = df.dropna(subset=["open", "high", "low", "close"])
            df = df[df["volume"] > 0]  # 过滤零成交量
            
            logger.info(f"获取{symbol}数据: {len(df)}条记录")
            return df
            
        except Exception as e:
            logger.error(f"获取{symbol}K线数据失败: {e}")
            return pd.DataFrame()
    
    def _compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标
        
        Args:
            df: K线数据
            
        Returns:
            DataFrame: 包含技术指标的数据
        """
        if df.empty:
            return df
        
        try:
            # 创建指标引擎
            engine = IndicatorEngine(df)
            
            # 计算所有指标
            engine.compute_all()
            
            logger.info(f"技术指标计算完成，共{len(engine.df.columns)}列")
            return engine.df
            
        except Exception as e:
            logger.error(f"技术指标计算失败: {e}")
            return df
    
    def _save_to_duckdb(self, symbol: str, df: pd.DataFrame):
        """
        保存数据到DuckDB
        
        Args:
            symbol: 品种代码
            df: 包含K线和指标的数据
        """
        if df.empty or not self.conn:
            return
        
        try:
            # 1. 保存K线数据
            kline_df = df[["open", "high", "low", "close", "volume", "open_interest"]].copy()
            kline_df["symbol"] = symbol
            kline_df["timeframe"] = "daily"
            kline_df["source"] = "tqsdk"
            kline_df = kline_df.reset_index()
            
            # 确保timestamp列是datetime类型
            if not pd.api.types.is_datetime64_any_dtype(kline_df["timestamp"]):
                kline_df["timestamp"] = pd.to_datetime(kline_df["timestamp"])
            
            # 删除已存在的数据（避免重复）
            self.conn.execute("""
            DELETE FROM klines 
            WHERE symbol = ? AND timeframe = 'daily' 
            AND timestamp >= ? AND timestamp <= ?
            """, [symbol, kline_df["timestamp"].min(), kline_df["timestamp"].max()])
            
            # 插入新数据
            self.conn.execute("""
            INSERT INTO klines (symbol, timestamp, timeframe, open, high, low, close, volume, open_interest, source)
            SELECT symbol, timestamp, timeframe, open, high, low, close, volume, open_interest, source
            FROM kline_df
            """)
            
            # 2. 保存技术指标
            indicator_cols = [col for col in df.columns if col not in [
                "open", "high", "low", "close", "volume", "open_interest"
            ]]
            
            if indicator_cols:
                # 转换为长格式（只保存数值类型的指标）
                indicator_data = []
                for col in indicator_cols:
                    for timestamp, value in df[col].items():
                        if pd.notna(value):
                            # 尝试转换为数值类型，跳过字符串类型的指标（如'NEUTRAL'）
                            try:
                                numeric_value = float(value)
                                indicator_data.append({
                                    "symbol": symbol,
                                    "timestamp": timestamp,
                                    "indicator_name": col,
                                    "value": numeric_value,
                                    "parameters": json.dumps({"period": 14})  # 默认参数
                                })
                            except (ValueError, TypeError):
                                # 跳过非数值类型的指标
                                continue
                
                if indicator_data:
                    indicator_df = pd.DataFrame(indicator_data)
                    
                    # 确保timestamp列是datetime类型
                    if not pd.api.types.is_datetime64_any_dtype(indicator_df["timestamp"]):
                        indicator_df["timestamp"] = pd.to_datetime(indicator_df["timestamp"])
                    
                    # 删除已存在的指标数据
                    self.conn.execute("""
                    DELETE FROM indicators 
                    WHERE symbol = ? 
                    AND timestamp >= ? AND timestamp <= ?
                    """, [symbol, df.index.min(), df.index.max()])
                    
                    # 插入新指标数据
                    self.conn.execute("""
                    INSERT INTO indicators (symbol, timestamp, indicator_name, value, parameters)
                    SELECT symbol, timestamp, indicator_name, value, parameters
                    FROM indicator_df
                    """)
                    
                    logger.info(f"保存{symbol}技术指标: {len(indicator_cols)}个指标")
            
            logger.info(f"保存{symbol}数据完成")
            
        except Exception as e:
            logger.error(f"保存{symbol}数据到DuckDB失败: {e}")
    
    def _log_sync_result(self, sync_id: str, status: str, error_message: str = None):
        """
        记录同步日志
        
        Args:
            sync_id: 同步ID
            status: 同步状态
            error_message: 错误信息
        """
        if not self.conn:
            return
        
        try:
            details = json.dumps({
                "days": self.days,
                "db_path": str(self.db_path),
                "stats": self.stats
            }, ensure_ascii=False)
            
            self.conn.execute("""
            INSERT INTO sync_log (sync_id, start_time, end_time, total_symbols, synced_count, 
                                 failed_count, skipped_count, indicators_count, status, error_message, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                sync_id,
                self.stats["start_time"],
                self.stats["end_time"],
                self.stats["total_symbols"],
                self.stats["synced"],
                self.stats["failed"],
                self.stats["skipped"],
                self.stats["indicators_computed"],
                status,
                error_message,
                details
            ])
            
            logger.info(f"同步日志已记录: {sync_id}")
            
        except Exception as e:
            logger.error(f"记录同步日志失败: {e}")
    
    def run(self, force: bool = False):
        """
        执行同步任务
        
        Args:
            force: 是否强制同步所有品种
        """
        logger.info("=" * 60)
        logger.info("开始期货数据每日同步")
        logger.info("=" * 60)
        
        self.stats["start_time"] = datetime.now().isoformat()
        
        # 生成同步ID
        sync_id = f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            # 1. 获取所有期货品种
            symbols = FUTURES_SYMBOLS
            self.stats["total_symbols"] = len(symbols)
            
            logger.info(f"获取到{len(symbols)}个期货品种")
            
            # 2. 逐个品种同步
            for i, symbol in enumerate(symbols, 1):
                logger.info(f"[{i}/{len(symbols)}] 同步{symbol}...")
                
                try:
                    # 检查是否需要同步（非强制模式）
                    if not force:
                        # 检查最新数据时间
                        result = self.conn.execute("""
                        SELECT MAX(timestamp) as latest 
                        FROM klines 
                        WHERE symbol = ? AND timeframe = 'daily'
                        """, [symbol]).fetchone()
                        
                        if result and result[0]:
                            latest = result[0]
                            days_since = (datetime.now() - latest).days
                            
                            if days_since <= 1:
                                logger.info(f"  {symbol}数据已是最新，跳过")
                                self.stats["skipped"] += 1
                                continue
                    
                    # 获取K线数据
                    df = self._fetch_kline_data(symbol)
                    
                    if df.empty:
                        logger.warning(f"  {symbol}无数据，跳过")
                        self.stats["skipped"] += 1
                        continue
                    
                    # 计算技术指标
                    df_with_indicators = self._compute_indicators(df)
                    
                    # 保存到DuckDB
                    self._save_to_duckdb(symbol, df_with_indicators)
                    
                    # 统计指标数量
                    indicator_cols = [col for col in df_with_indicators.columns if col not in [
                        "open", "high", "low", "close", "volume", "open_interest"
                    ]]
                    self.stats["indicators_computed"] += len(indicator_cols)
                    
                    self.stats["synced"] += 1
                    logger.info(f"  {symbol}同步成功，{len(df)}条K线，{len(indicator_cols)}个指标")
                    
                    # 避免请求过快
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"  {symbol}同步失败: {e}")
                    self.stats["failed"] += 1
                    continue
            
            self.stats["end_time"] = datetime.now().isoformat()
            
            # 记录同步日志
            self._log_sync_result(sync_id, "success")
            
            # 打印统计信息
            self._print_statistics()
            
            logger.info("=" * 60)
            logger.info("期货数据每日同步完成")
            logger.info("=" * 60)
            
        except Exception as e:
            self.stats["end_time"] = datetime.now().isoformat()
            self._log_sync_result(sync_id, "failed", str(e))
            logger.error(f"同步任务失败: {e}")
            raise
    
    def _print_statistics(self):
        """打印统计信息"""
        logger.info("\n" + "=" * 60)
        logger.info("同步统计信息")
        logger.info("=" * 60)
        
        logger.info(f"总品种数: {self.stats['total_symbols']}")
        logger.info(f"成功同步: {self.stats['synced']}")
        logger.info(f"同步失败: {self.stats['failed']}")
        logger.info(f"跳过品种: {self.stats['skipped']}")
        logger.info(f"技术指标: {self.stats['indicators_computed']}")
        logger.info(f"开始时间: {self.stats['start_time']}")
        logger.info(f"结束时间: {self.stats['end_time']}")
        
        # 计算耗时
        if self.stats["start_time"] and self.stats["end_time"]:
            start = datetime.fromisoformat(self.stats["start_time"])
            end = datetime.fromisoformat(self.stats["end_time"])
            duration = (end - start).total_seconds()
            logger.info(f"耗时: {duration:.1f}秒")
        
        # 数据库统计
        if self.conn:
            try:
                kline_count = self.conn.execute("SELECT COUNT(*) FROM klines").fetchone()[0]
                indicator_count = self.conn.execute("SELECT COUNT(*) FROM indicators").fetchone()[0]
                symbol_count = self.conn.execute("SELECT COUNT(DISTINCT symbol) FROM klines").fetchone()[0]
                
                logger.info(f"\n数据库统计:")
                logger.info(f"  K线记录: {kline_count}")
                logger.info(f"  指标记录: {indicator_count}")
                logger.info(f"  品种数量: {symbol_count}")
                
                # 数据库大小
                db_size = os.path.getsize(self.db_path) / (1024 * 1024)
                logger.info(f"  数据库大小: {db_size:.2f}MB")
                
            except Exception as e:
                logger.error(f"获取数据库统计失败: {e}")
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            try:
                self.conn.close()
                logger.info("DuckDB连接已关闭")
            except Exception as e:
                logger.error(f"关闭DuckDB连接失败: {e}")
            finally:
                self.conn = None
    
    def _cleanup_lock_files(self):
        """清理数据库锁文件"""
        lock_files = [
            str(self.db_path) + ".lock",
            str(self.db_path) + ".wal",
            str(self.db_path) + ".shm",
        ]
        
        for lock_file in lock_files:
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                    logger.info(f"清理锁文件: {lock_file}")
                except Exception as e:
                    logger.warning(f"无法清理锁文件 {lock_file}: {e}")


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(description="期货数据每日同步")
    parser.add_argument("--days", type=int, default=250, help="获取天数（默认250个交易日）")
    parser.add_argument("--force", action="store_true", help="强制同步所有品种")
    parser.add_argument("--db", type=str, default="data/futures.db", help="数据库路径")
    
    args = parser.parse_args()
    
    # 创建同步器
    syncer = FuturesDailySync(db_path=args.db, days=args.days)
    
    try:
        # 执行同步
        syncer.run(force=args.force)
    finally:
        # 关闭连接
        syncer.close()


if __name__ == "__main__":
    main()