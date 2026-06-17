"""
CircuitBreaker — 策略级熔断机制 v1.0

基于 Kevin J. Davey《构建盈利的算法交易系统》中的 Step 7：
为每个策略预设停止交易的阈值，防止失效策略造成灾难性亏损。

核心规则：
1. 最大亏损：累计亏损超过阈值（如 $5000/合约）
2. 最大回撤：权益回撤超过阈值（如 20%）
3. 连续亏损：连续亏损次数超过阈值（如 10次）
4. 冷却期：熔断后暂停交易的天数（如 30天）

使用方式：
    from circuit_breaker import CircuitBreaker
    cb = CircuitBreaker()
    result = cb.check("strategy_001", equity_curve, trades)
    if result.triggered:
        print(f"熔断触发: {result.trigger_reason}")

版本：v1.0
创建日期：2026-06-17
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd


logger = logging.getLogger(__name__)


# ===================== 数据模型 =====================


@dataclass
class CircuitBreakerConfig:
    """熔断配置"""

    max_loss_per_strategy: float = 5000.0  # 每策略最大亏损（美元）
    max_drawdown_pct: float = 0.20  # 最大回撤百分比
    max_consecutive_losses: int = 10  # 最大连续亏损次数
    cooldown_days: int = 30  # 冷却期天数
    max_loss_per_contract: float = 5000.0  # 每合约最大亏损

    def to_dict(self) -> dict:
        return {
            "max_loss_per_strategy": self.max_loss_per_strategy,
            "max_drawdown_pct": self.max_drawdown_pct,
            "max_consecutive_losses": self.max_consecutive_losses,
            "cooldown_days": self.cooldown_days,
            "max_loss_per_contract": self.max_loss_per_contract,
        }


@dataclass
class CircuitBreakerResult:
    """熔断检查结果"""

    strategy_id: str
    triggered: bool
    trigger_reason: str
    metrics: dict  # 当前指标值
    cooldown_remaining: int = 0  # 冷却剩余天数
    recommendation: str = "continue"  # "continue" | "pause" | "terminate"

    def to_dict(self) -> dict:
        return {
            "strategy_id": self.strategy_id,
            "triggered": self.triggered,
            "trigger_reason": self.trigger_reason,
            "metrics": self.metrics,
            "cooldown_remaining": self.cooldown_remaining,
            "recommendation": self.recommendation,
        }


@dataclass
class StrategyState:
    """策略状态"""

    strategy_id: str
    is_paused: bool = False
    pause_reason: str = ""
    pause_time: datetime | None = None
    total_loss: float = 0.0
    max_drawdown: float = 0.0
    consecutive_losses: int = 0
    last_check_time: datetime | None = None
    check_count: int = 0

    def to_dict(self) -> dict:
        return {
            "strategy_id": self.strategy_id,
            "is_paused": self.is_paused,
            "pause_reason": self.pause_reason,
            "pause_time": self.pause_time.isoformat() if self.pause_time else None,
            "total_loss": self.total_loss,
            "max_drawdown": self.max_drawdown,
            "consecutive_losses": self.consecutive_losses,
            "last_check_time": self.last_check_time.isoformat() if self.last_check_time else None,
            "check_count": self.check_count,
        }


# ===================== 熔断器 =====================


class CircuitBreaker:
    """
    策略级熔断机制

    为每个策略预设停止交易的阈值，防止失效策略造成灾难性亏损。
    """

    def __init__(self, config: dict = None, storage_path: str = None):
        """
        参数:
            config: 熔断配置字典
            storage_path: 状态存储路径（JSON）
        """
        config = config or {}
        self.config = CircuitBreakerConfig(
            max_loss_per_strategy=config.get("max_loss_per_strategy", 5000.0),
            max_drawdown_pct=config.get("max_drawdown_pct", 0.20),
            max_consecutive_losses=config.get("max_consecutive_losses", 10),
            cooldown_days=config.get("cooldown_days", 30),
            max_loss_per_contract=config.get("max_loss_per_contract", 5000.0),
        )

        self.storage_path = storage_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "circuit_breaker_state.json"
        )

        # 策略状态 {strategy_id: StrategyState}
        self._states: dict[str, StrategyState] = {}

        # 加载已有状态
        self._load_states()

    def check(
        self,
        strategy_id: str,
        equity_curve: pd.Series = None,
        trades: list[dict] = None,
        initial_capital: float = 100000,
    ) -> CircuitBreakerResult:
        """
        检查策略是否触发熔断

        参数:
            strategy_id: 策略ID
            equity_curve: 权益曲线（可选）
            trades: 交易记录列表（每笔含 pnl 字段）
            initial_capital: 初始资金

        返回:
            CircuitBreakerResult
        """
        # 获取或创建策略状态
        if strategy_id not in self._states:
            self._states[strategy_id] = StrategyState(strategy_id=strategy_id)

        state = self._states[strategy_id]
        state.last_check_time = datetime.now()
        state.check_count += 1

        # 检查冷却期
        if state.is_paused and state.pause_time:
            days_in_cooldown = (datetime.now() - state.pause_time).days
            if days_in_cooldown < self.config.cooldown_days:
                remaining = self.config.cooldown_days - days_in_cooldown
                return CircuitBreakerResult(
                    strategy_id=strategy_id,
                    triggered=True,
                    trigger_reason=f"冷却期中: 剩余{remaining}天",
                    metrics={},
                    cooldown_remaining=remaining,
                    recommendation="pause",
                )
            else:
                # 冷却期结束，自动恢复
                state.is_paused = False
                state.pause_reason = ""
                state.consecutive_losses = 0
                logger.info(f"策略 {strategy_id} 冷却期结束，自动恢复")

        # 计算指标
        metrics = {}
        triggered = False
        trigger_reason = ""

        if trades:
            # 计算累计亏损
            total_pnl = sum(t.get("pnl", 0) for t in trades)
            state.total_loss = total_pnl
            metrics["total_pnl"] = total_pnl

            # 检查最大亏损
            if total_pnl < -self.config.max_loss_per_strategy:
                triggered = True
                trigger_reason = f"累计亏损{abs(total_pnl):.0f}超过阈值{self.config.max_loss_per_strategy:.0f}"

            # 计算连续亏损
            consecutive = 0
            for t in reversed(trades):
                if t.get("pnl", 0) < 0:
                    consecutive += 1
                else:
                    break
            state.consecutive_losses = consecutive
            metrics["consecutive_losses"] = consecutive

            # 检查连续亏损
            if consecutive >= self.config.max_consecutive_losses:
                triggered = True
                trigger_reason = f"连续亏损{consecutive}次超过阈值{self.config.max_consecutive_losses}"

        if equity_curve is not None and len(equity_curve) > 0:
            # 计算最大回撤
            running_max = equity_curve.cummax()
            drawdown = (running_max - equity_curve) / running_max.replace(0, np.nan)
            max_dd = float(drawdown.max()) if not drawdown.empty else 0
            state.max_drawdown = max_dd
            metrics["max_drawdown"] = max_dd
            metrics["current_equity"] = float(equity_curve.iloc[-1])

            # 检查最大回撤
            if max_dd > self.config.max_drawdown_pct:
                triggered = True
                trigger_reason = f"最大回撤{max_dd:.2%}超过阈值{self.config.max_drawdown_pct:.2%}"

        # 触发熔断
        if triggered and not state.is_paused:
            state.is_paused = True
            state.pause_reason = trigger_reason
            state.pause_time = datetime.now()
            logger.warning(f"策略 {strategy_id} 熔断触发: {trigger_reason}")

        # 生成建议
        if state.is_paused:
            recommendation = "pause"
        elif triggered:
            recommendation = "terminate"
        else:
            recommendation = "continue"

        # 保存状态
        self._save_states()

        return CircuitBreakerResult(
            strategy_id=strategy_id,
            triggered=triggered or state.is_paused,
            trigger_reason=trigger_reason or ("冷却期中" if state.is_paused else "未触发"),
            metrics=metrics,
            cooldown_remaining=self.config.cooldown_days if state.is_paused else 0,
            recommendation=recommendation,
        )

    def reset(self, strategy_id: str) -> None:
        """重置策略的熔断状态"""
        if strategy_id in self._states:
            state = self._states[strategy_id]
            state.is_paused = False
            state.pause_reason = ""
            state.consecutive_losses = 0
            self._save_states()
            logger.info(f"策略 {strategy_id} 熔断状态已重置")

    def get_status(self, strategy_id: str) -> dict:
        """获取策略的熔断状态"""
        if strategy_id not in self._states:
            return {"strategy_id": strategy_id, "is_paused": False, "check_count": 0}

        state = self._states[strategy_id]
        return {
            "strategy_id": state.strategy_id,
            "is_paused": state.is_paused,
            "pause_reason": state.pause_reason,
            "total_loss": state.total_loss,
            "max_drawdown": state.max_drawdown,
            "consecutive_losses": state.consecutive_losses,
            "last_check_time": state.last_check_time.isoformat() if state.last_check_time else None,
            "check_count": state.check_count,
        }

    def get_all_status(self) -> dict[str, dict]:
        """获取所有策略的熔断状态"""
        return {sid: self.get_status(sid) for sid in self._states}

    def get_paused_strategies(self) -> list[str]:
        """获取所有已暂停的策略ID"""
        return [sid for sid, state in self._states.items() if state.is_paused]

    # ===================== 持久化 =====================

    def _load_states(self):
        """从文件加载状态"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, encoding="utf-8") as f:
                    data = json.load(f)
                for sid, sdata in data.items():
                    state = StrategyState(
                        strategy_id=sdata["strategy_id"],
                        is_paused=sdata.get("is_paused", False),
                        pause_reason=sdata.get("pause_reason", ""),
                        pause_time=datetime.fromisoformat(sdata["pause_time"]) if sdata.get("pause_time") else None,
                        total_loss=sdata.get("total_loss", 0),
                        max_drawdown=sdata.get("max_drawdown", 0),
                        consecutive_losses=sdata.get("consecutive_losses", 0),
                        last_check_time=datetime.fromisoformat(sdata["last_check_time"])
                        if sdata.get("last_check_time")
                        else None,
                        check_count=sdata.get("check_count", 0),
                    )
                    self._states[sid] = state
            except Exception as e:
                logger.warning(f"加载熔断状态失败: {e}")

    def _save_states(self):
        """保存状态到文件"""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            data = {sid: state.to_dict() for sid, state in self._states.items()}
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存熔断状态失败: {e}")
