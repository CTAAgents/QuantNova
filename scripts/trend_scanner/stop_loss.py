"""
动态止损模块

实现多种止损算法：
- ATR 倍数止损：基于波动率的动态止损
- 移动止损：跟踪最高/最低价
- 波动率调整止损：高波动时放宽，低波动时收紧
- 时间止损：持仓超过一定时间自动止损

设计原则：
- 止损是风控的核心，不是可选项
- 动态止损优于固定止损（适应市场波动率变化）
- 止损位置应基于市场结构，而非随意数字

文件：scripts/trend_scanner/stop_loss.py
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class StopLossCalculator:
    """
    动态止损计算器
    
    提供多种止损计算方法，根据市场状态动态调整止损位置。
    """
    
    def __init__(self, default_atr_multiplier: float = 2.5):
        """
        初始化止损计算器
        
        Args:
            default_atr_multiplier: 默认 ATR 倍数（2.5 倍）
        """
        self.default_atr_multiplier = default_atr_multiplier
    
    def atr_stop(
        self,
        entry_price: float,
        atr: float,
        direction: str,
        multiplier: float = None
    ) -> float:
        """
        ATR 倍数止损
        
        最常用的动态止损方法，根据市场波动率调整止损距离。
        
        Args:
            entry_price: 入场价格
            atr: ATR 值
            direction: 方向（LONG/SHORT）
            multiplier: ATR 倍数（默认使用配置值）
            
        Returns:
            止损价格
        """
        mult = multiplier or self.default_atr_multiplier
        
        if direction == "LONG":
            return entry_price - atr * mult
        else:
            return entry_price + atr * mult
    
    def trailing_stop(
        self,
        best_price: float,
        atr: float,
        direction: str,
        multiplier: float = 3.0
    ) -> float:
        """
        移动止损（跟踪止损）
        
        跟踪最高/最低价，锁定利润。
        
        Args:
            best_price: 持仓期间最优价格（多头取最高价，空头取最低价）
            atr: ATR 值
            direction: 方向（LONG/SHORT）
            multiplier: ATR 倍数（默认 3.0，比初始止损更宽）
            
        Returns:
            移动止损价格
        """
        if direction == "LONG":
            return best_price - atr * multiplier
        else:
            return best_price + atr * multiplier
    
    def volatility_adjusted_stop(
        self,
        entry_price: float,
        atr: float,
        direction: str,
        current_vol: float,
        base_vol: float = 0.2,
        multiplier: float = None
    ) -> float:
        """
        波动率调整止损
        
        高波动时放宽止损（避免被震出局），低波动时收紧止损（保护利润）。
        
        Args:
            entry_price: 入场价格
            atr: ATR 值
            direction: 方向（LONG/SHORT）
            current_vol: 当前波动率
            base_vol: 基准波动率（默认 20%）
            multiplier: 基础 ATR 倍数
            
        Returns:
            调整后的止损价格
        """
        mult = multiplier or self.default_atr_multiplier
        
        # 波动率调整系数
        vol_ratio = current_vol / max(base_vol, 0.01)
        adjustment = max(0.8, min(vol_ratio, 2.0))  # 限制在 0.8-2.0
        
        adjusted_mult = mult * adjustment
        
        if direction == "LONG":
            return entry_price - atr * adjusted_mult
        else:
            return entry_price + atr * adjusted_mult
    
    def time_stop(
        self,
        entry_time: datetime,
        max_holding_days: int = 10,
        current_time: datetime = None
    ) -> Dict[str, Any]:
        """
        时间止损
        
        持仓超过一定时间自动止损，避免资金效率过低。
        
        Args:
            entry_time: 入场时间
            max_holding_days: 最大持仓天数（默认 10 天）
            current_time: 当前时间（默认现在）
            
        Returns:
            {'should_stop': bool, 'reason': str, 'holding_days': int}
        """
        now = current_time or datetime.now()
        holding_days = (now - entry_time).days
        
        if holding_days >= max_holding_days:
            return {
                'should_stop': True,
                'reason': f'持仓 {holding_days} 天，超过 {max_holding_days} 天限制',
                'holding_days': holding_days
            }
        
        return {
            'should_stop': False,
            'reason': f'持仓 {holding_days} 天，未超限',
            'holding_days': holding_days
        }
    
    def multi_condition_stop(
        self,
        entry_price: float,
        current_price: float,
        atr: float,
        direction: str,
        best_price: float = None,
        entry_time: datetime = None,
        current_vol: float = None
    ) -> Dict[str, Any]:
        """
        多条件止损（综合判断）
        
        综合考虑 ATR 止损、移动止损、时间止损，取最严格的条件。
        
        Args:
            entry_price: 入场价格
            current_price: 当前价格
            atr: ATR 值
            direction: 方向（LONG/SHORT）
            best_price: 持仓期间最优价格
            entry_time: 入场时间
            current_vol: 当前波动率
            
        Returns:
            综合止损结果
        """
        stops = {}
        
        # 1. ATR 初始止损
        atr_stop = self.atr_stop(entry_price, atr, direction)
        stops['atr_stop'] = {
            'price': round(atr_stop, 2),
            'type': 'ATR止损',
            'active': True
        }
        
        # 2. 移动止损（如果提供了最优价格）
        if best_price is not None:
            trail_stop = self.trailing_stop(best_price, atr, direction)
            # 移动止损只在盈利时激活
            if direction == "LONG" and trail_stop > entry_price:
                stops['trailing_stop'] = {
                    'price': round(trail_stop, 2),
                    'type': '移动止损',
                    'active': True
                }
            elif direction == "SHORT" and trail_stop < entry_price:
                stops['trailing_stop'] = {
                    'price': round(trail_stop, 2),
                    'type': '移动止损',
                    'active': True
                }
        
        # 3. 波动率调整止损
        if current_vol is not None:
            vol_stop = self.volatility_adjusted_stop(entry_price, atr, direction, current_vol)
            stops['vol_adjusted_stop'] = {
                'price': round(vol_stop, 2),
                'type': '波动率调整止损',
                'active': True
            }
        
        # 4. 时间止损
        if entry_time is not None:
            time_result = self.time_stop(entry_time)
            stops['time_stop'] = {
                'active': time_result['should_stop'],
                'reason': time_result['reason'],
                'type': '时间止损'
            }
        
        # 确定最终止损价（取最严格的）
        active_stops = {k: v for k, v in stops.items() if v.get('active') and 'price' in v}
        
        if active_stops:
            if direction == "LONG":
                # 多头取最高的止损价（最严格）
                final_stop = max(v['price'] for v in active_stops.values())
            else:
                # 空头取最低的止损价（最严格）
                final_stop = min(v['price'] for v in active_stops.values())
        else:
            final_stop = atr_stop
        
        # 检查是否触发止损
        triggered = False
        trigger_reason = ""
        
        if direction == "LONG" and current_price <= final_stop:
            triggered = True
            trigger_reason = f"当前价 {current_price:.2f} <= 止损价 {final_stop:.2f}"
        elif direction == "SHORT" and current_price >= final_stop:
            triggered = True
            trigger_reason = f"当前价 {current_price:.2f} >= 止损价 {final_stop:.2f}"
        
        return {
            'triggered': triggered,
            'trigger_reason': trigger_reason,
            'final_stop_price': round(final_stop, 2),
            'stop_details': stops,
            'risk_points': abs(entry_price - final_stop),
            'risk_pct': round(abs(entry_price - final_stop) / entry_price * 100, 2)
        }
