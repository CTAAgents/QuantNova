"""
供需数据接口

提供期货品种的供需数据获取功能，支持：
- 库存数据（交易所库存、社会库存）
- 产量数据（月度产量、开工率）
- 消费数据（表观消费量）
- 进出口数据（海关统计）

数据源：
- 东方财富（免费数据）
- 各行业协会官网
- 海关总署（进出口数据）

使用方式：
    from fundamental.supply_demand import SupplyDemandProvider
    
    provider = SupplyDemandProvider()
    data = provider.get_supply_demand(symbol="SC")
"""

import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta
from typing import Any

import requests

# 导入数据模型
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from trend_scanner.models import SupplyDemandData

logger = logging.getLogger(__name__)


class DataSource:
    """数据源基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
    
    def get_inventory(self, symbol: str) -> dict:
        """获取库存数据"""
        raise NotImplementedError
    
    def get_production(self, symbol: str) -> dict:
        """获取产量数据"""
        raise NotImplementedError
    
    def get_consumption(self, symbol: str) -> dict:
        """获取消费数据"""
        raise NotImplementedError


class EastmoneySupplyDemand(DataSource):
    """东方财富供需数据"""
    
    def __init__(self):
        super().__init__("东方财富")
        self.base_url = "https://datacenter-web.eastmoney.com"
    
    def get_inventory(self, symbol: str) -> dict:
        """获取库存数据"""
        try:
            # 东方财富期货库存数据API
            url = f"{self.base_url}/api/data/v1/get"
            params = {
                "reportName": "RPT_FUTU_INVENTORY",
                "columns": "ALL",
                "filter": f"(VARIETY_CODE=\"{symbol}\")",
                "pageNumber": 1,
                "pageSize": 1,
                "sortColumns": "TRADE_DATE",
                "sortTypes": -1,
            }
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("result") and data["result"].get("data"):
                    item = data["result"]["data"][0]
                    return {
                        "inventory_exchange": item.get("EXCHANGE_INVENTORY", 0),
                        "inventory_social": item.get("SOCIAL_INVENTORY", 0),
                        "inventory_change_pct": item.get("INVENTORY_CHANGE_PCT", 0),
                        "timestamp": item.get("TRADE_DATE", ""),
                    }
        except Exception as e:
            logger.warning(f"东方财富库存数据获取失败: {e}")
        return {}
    
    def get_production(self, symbol: str) -> dict:
        """获取产量数据"""
        try:
            # 东方财富产量数据API
            url = f"{self.base_url}/api/data/v1/get"
            params = {
                "reportName": "RPT_FUTU_PRODUCTION",
                "columns": "ALL",
                "filter": f"(VARIETY_CODE=\"{symbol}\")",
                "pageNumber": 1,
                "pageSize": 1,
                "sortColumns": "REPORT_DATE",
                "sortTypes": -1,
            }
            response = self.session.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("result") and data["result"].get("data"):
                    item = data["result"]["data"][0]
                    return {
                        "production": item.get("PRODUCTION_VOLUME", 0),
                        "production_change_pct": item.get("PRODUCTION_CHANGE_PCT", 0),
                        "capacity_utilization": item.get("CAPACITY_UTILIZATION", 0),
                        "timestamp": item.get("REPORT_DATE", ""),
                    }
        except Exception as e:
            logger.warning(f"东方财富产量数据获取失败: {e}")
        return {}


class SupplyDemandProvider:
    """
    供需数据提供者
    
    从多个数据源获取期货品种的供需数据。
    """
    
    # 品种分类
    SYMBOL_CATEGORIES = {
        # 能源
        "SC": "energy", "FU": "energy", "BU": "energy", "LU": "energy",
        # 化工
        "BZ": "chemical", "TA": "chemical", "MA": "chemical", "EG": "chemical",
        "EB": "chemical", "PP": "chemical", "V": "chemical", "L": "chemical",
        # 黑色系
        "RB": "ferrous", "HC": "ferrous", "I": "ferrous", "J": "ferrous", "JM": "ferrous",
        # 有色金属
        "CU": "nonferrous", "AL": "nonferrous", "ZN": "nonferrous", "NI": "nonferrous",
        # 农产品
        "CF": "agricultural", "SR": "agricultural", "M": "agricultural",
        "Y": "agricultural", "P": "agricultural",
        # 贵金属
        "AU": "precious", "AG": "precious",
    }
    
    def __init__(self, cache_dir: str = None):
        """
        初始化供需数据提供者
        
        Args:
            cache_dir: 缓存目录
        """
        self.sources = [
            EastmoneySupplyDemand(),
        ]
        
        # 缓存目录
        self.cache_dir = cache_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "supply_demand_cache"
        )
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 缓存有效期（小时）
        self.cache_hours = 24
    
    def _get_cache_path(self, symbol: str, data_type: str) -> str:
        """获取缓存文件路径"""
        return os.path.join(self.cache_dir, f"{symbol}_{data_type}.json")
    
    def _load_cache(self, symbol: str, data_type: str) -> dict:
        """加载缓存数据"""
        cache_path = self._get_cache_path(symbol, data_type)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, encoding="utf-8") as f:
                    cache_data = json.load(f)
                    # 检查缓存是否过期
                    cache_time = datetime.fromisoformat(cache_data.get("timestamp", "2000-01-01"))
                    if datetime.now() - cache_time < timedelta(hours=self.cache_hours):
                        return cache_data.get("data", {})
            except Exception:
                pass
        return {}
    
    def _save_cache(self, symbol: str, data_type: str, data: dict):
        """保存缓存数据"""
        cache_path = self._get_cache_path(symbol, data_type)
        try:
            cache_data = {
                "timestamp": datetime.now().isoformat(),
                "data": data,
            }
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存缓存失败: {e}")
    
    def get_supply_demand(self, symbol: str) -> SupplyDemandData:
        """
        获取供需数据
        
        Args:
            symbol: 品种代码
            
        Returns:
            供需数据对象
        """
        logger.info(f"获取{symbol}供需数据")
        
        # 创建供需数据对象
        supply_demand = SupplyDemandData(
            symbol=symbol,
            timestamp=datetime.now().isoformat(),
        )
        
        # 尝试从缓存加载
        cached_data = self._load_cache(symbol, "supply_demand")
        if cached_data:
            # 更新对象属性
            for key, value in cached_data.items():
                if hasattr(supply_demand, key):
                    setattr(supply_demand, key, value)
            logger.info(f"从缓存加载{symbol}供需数据")
            return supply_demand
        
        # 从数据源获取
        inventory_data = {}
        production_data = {}
        
        for source in self.sources:
            try:
                # 获取库存数据
                if not inventory_data:
                    inventory_data = source.get_inventory(symbol)
                
                # 获取产量数据
                if not production_data:
                    production_data = source.get_production(symbol)
                
                # 如果获取到数据，停止尝试其他源
                if inventory_data or production_data:
                    break
                    
            except Exception as e:
                logger.warning(f"从{source.name}获取{symbol}数据失败: {e}")
        
        # 更新供需数据对象
        if inventory_data:
            supply_demand.inventory_exchange = inventory_data.get("inventory_exchange", 0)
            supply_demand.inventory_social = inventory_data.get("inventory_social", 0)
            supply_demand.inventory_change_pct = inventory_data.get("inventory_change_pct", 0)
        
        if production_data:
            supply_demand.production = production_data.get("production", 0)
            supply_demand.production_change_pct = production_data.get("production_change_pct", 0)
            supply_demand.capacity_utilization = production_data.get("capacity_utilization", 0)
        
        # 计算供需平衡状态
        supply_demand.balance_status = self._calculate_balance_status(supply_demand)
        
        # 保存到缓存
        self._save_cache(symbol, "supply_demand", supply_demand.to_dict())
        
        return supply_demand
    
    def _calculate_balance_status(self, supply_demand: SupplyDemandData) -> str:
        """
        计算供需平衡状态
        
        Args:
            supply_demand: 供需数据
            
        Returns:
            平衡状态：surplus/balanced/deficit
        """
        # 简化判断逻辑
        # 实际应用中应该基于更复杂的模型
        
        # 如果库存增加，可能供过于求
        if supply_demand.inventory_change_pct > 5:
            return "surplus"
        
        # 如果库存减少，可能供不应求
        if supply_demand.inventory_change_pct < -5:
            return "deficit"
        
        # 默认供需平衡
        return "balanced"
    
    def get_batch_supply_demand(self, symbols: list[str]) -> dict[str, SupplyDemandData]:
        """
        批量获取供需数据
        
        Args:
            symbols: 品种代码列表
            
        Returns:
            品种代码到供需数据的映射
        """
        result = {}
        for symbol in symbols:
            try:
                result[symbol] = self.get_supply_demand(symbol)
            except Exception as e:
                logger.warning(f"获取{symbol}供需数据失败: {e}")
        return result


# 测试代码
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # 测试供需数据获取
    provider = SupplyDemandProvider()
    
    # 测试原油供需数据
    print("=== 测试原油供需数据 ===")
    data = provider.get_supply_demand("SC")
    print(f"品种：{data.symbol}")
    print(f"交易所库存：{data.inventory_exchange}")
    print(f"库存变化：{data.inventory_change_pct}%")
    print(f"产量：{data.production}")
    print(f"供需状态：{data.balance_status}")
    print()
    
    # 测试焦煤供需数据
    print("=== 测试焦煤供需数据 ===")
    data = provider.get_supply_demand("JM")
    print(f"品种：{data.symbol}")
    print(f"交易所库存：{data.inventory_exchange}")
    print(f"库存变化：{data.inventory_change_pct}%")
    print(f"产量：{data.production}")
    print(f"供需状态：{data.balance_status}")