"""
市场数据提供者抽象基类

为期货和证券子系统提供统一的数据接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List

import pandas as pd


class MarketType(Enum):
    """市场类型"""
    FUTURES = "futures"
    SECURITIES = "securities"


@dataclass
class KlineData:
    """K线数据"""
    symbol: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class MarketProvider(ABC):
    """
    市场数据提供者抽象基类

    为期货和证券子系统提供统一的数据接口
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化市场数据提供者

        Args:
            config: 配置字典
        """
        self.config = config
        self.market_type = self._get_market_type()

    @abstractmethod
    def _get_market_type(self) -> MarketType:
        """获取市场类型"""
        pass

    @abstractmethod
    def get_kline(
        self,
        symbol: str,
        timeframe: str = "daily",
        count: int = 100,
    ) -> pd.DataFrame:
        """
        获取K线数据

        Args:
            symbol: 品种代码
            timeframe: 时间周期
            count: 数据条数

        Returns:
            DataFrame: K线数据
        """
        pass

    @abstractmethod
    def get_realtime_quote(self, symbol: str) -> Dict[str, Any]:
        """
        获取实时行情

        Args:
            symbol: 品种代码

        Returns:
            Dict: 实时行情数据
        """
        pass

    @abstractmethod
    def get_symbols(self) -> List[str]:
        """
        获取可用品种列表

        Returns:
            List[str]: 品种代码列表
        """
        pass

    @abstractmethod
    def get_fundamental(self, symbol: str) -> Dict[str, Any]:
        """
        获取基本面数据

        Args:
            symbol: 品种代码

        Returns:
            Dict: 基本面数据
        """
        pass

    def validate_symbol(self, symbol: str) -> bool:
        """
        验证品种代码是否有效

        Args:
            symbol: 品种代码

        Returns:
            bool: 是否有效
        """
        symbols = self.get_symbols()
        return symbol in symbols
