"""
风险管理器抽象基类

为期货和证券子系统提供统一的风险管理接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskMetrics:
    """风险指标"""
    position_size: float
    stop_loss_price: float
    take_profit_price: float
    risk_reward_ratio: float
    max_drawdown: float
    risk_level: RiskLevel
    warnings: List[str]


class BaseRiskManager(ABC):
    """
    风险管理器抽象基类

    为期货和证券子系统提供统一的风险管理接口
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化风险管理器

        Args:
            config: 配置字典
        """
        self.config = config

    @abstractmethod
    def calculate_position_size(
        self,
        signal: float,
        capital: float,
        current_price: float,
    ) -> float:
        """
        计算仓位大小

        Args:
            signal: 交易信号 (-1 到 1)
            capital: 可用资金
            current_price: 当前价格

        Returns:
            float: 仓位大小
        """
        pass

    @abstractmethod
    def calculate_stop_loss(
        self,
        entry_price: float,
        signal: float,
    ) -> float:
        """
        计算止损价格

        Args:
            entry_price: 入场价格
            signal: 交易信号 (-1 到 1)

        Returns:
            float: 止损价格
        """
        pass

    @abstractmethod
    def calculate_take_profit(
        self,
        entry_price: float,
        signal: float,
    ) -> float:
        """
        计算止盈价格

        Args:
            entry_price: 入场价格
            signal: 交易信号 (-1 到 1)

        Returns:
            float: 止盈价格
        """
        pass

    @abstractmethod
    def check_stop_loss(
        self,
        position: Dict[str, Any],
        current_price: float,
    ) -> bool:
        """
        检查是否触发止损

        Args:
            position: 持仓信息
            current_price: 当前价格

        Returns:
            bool: 是否触发止损
        """
        pass

    @abstractmethod
    def check_take_profit(
        self,
        position: Dict[str, Any],
        current_price: float,
    ) -> bool:
        """
        检查是否触发止盈

        Args:
            position: 持仓信息
            current_price: 当前价格

        Returns:
            bool: 是否触发止盈
        """
        pass

    @abstractmethod
    def get_risk_metrics(
        self,
        position: Dict[str, Any],
        current_price: float,
    ) -> RiskMetrics:
        """
        获取风险指标

        Args:
            position: 持仓信息
            current_price: 当前价格

        Returns:
            RiskMetrics: 风险指标
        """
        pass

    def validate_trade(
        self,
        signal: float,
        capital: float,
        current_price: float,
    ) -> tuple[bool, str]:
        """
        验证交易是否合法

        Args:
            signal: 交易信号
            capital: 可用资金
            current_price: 当前价格

        Returns:
            tuple[bool, str]: (是否合法, 原因)
        """
        if abs(signal) > 1:
            return False, "信号超出范围 [-1, 1]"

        if capital <= 0:
            return False, "可用资金不足"

        if current_price <= 0:
            return False, "价格无效"

        return True, "验证通过"
