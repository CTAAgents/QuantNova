"""
StrategyIncubator — 策略孵化模块 v1.0

基于 Kevin J. Davey《构建盈利的算法交易系统》中的 Step 6：
在投入真金白银前，用实盘数据进行最终验证。
策略在实时市场环境中运行，但不承担风险，通常持续3-6个月。

核心功能：
1. 创建孵化会话，记录回测预期指标
2. 实盘运行策略（不交易），记录每个信号
3. 孵化期结束后，对比回测 vs 实盘
4. 偏差超过阈值 → reject，否则 → approve

使用方式：
    from strategy_incubator import StrategyIncubator
    incubator = StrategyIncubator()
    session = incubator.start_incubation("strategy_001", {
        "expected_sharpe": 1.5,
        "expected_win_rate": 0.55,
        "expected_max_drawdown": 0.15,
    })
    # ... 实盘运行 ...
    incubator.record_signal("strategy_001", timestamp, signal, market_state)
    result = incubator.evaluate("strategy_001")

版本：v1.0
创建日期：2026-06-17
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


# ===================== 数据模型 =====================

@dataclass
class IncubationSession:
    """孵化会话"""
    strategy_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "active"  # "active" | "completed" | "failed"

    # 回测预期指标
    expected_sharpe: float = 0.0
    expected_win_rate: float = 0.0
    expected_max_drawdown: float = 0.0
    expected_annual_return: float = 0.0

    # 实盘记录
    actual_signals: List[Dict] = field(default_factory=list)

    # 配置
    incubation_days: int = 90
    max_deviation: float = 0.3  # 最大允许偏差 (30%)

    def to_dict(self) -> Dict:
        return {
            "strategy_id": self.strategy_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status,
            "expected": {
                "sharpe": self.expected_sharpe,
                "win_rate": self.expected_win_rate,
                "max_drawdown": self.expected_max_drawdown,
                "annual_return": self.expected_annual_return,
            },
            "incubation_days": self.incubation_days,
            "max_deviation": self.max_deviation,
            "signals_count": len(self.actual_signals),
        }


@dataclass
class IncubationResult:
    """孵化评估结果"""
    strategy_id: str
    passed: bool
    signal_consistency: float  # 信号一致性 (0-1)
    latency_avg: float         # 平均信号延迟（秒）
    deviation_sharpe: float    # 夏普偏差
    deviation_win_rate: float  # 胜率偏差
    deviation_drawdown: float  # 回撤偏差
    recommendation: str        # "approve" | "reject" | "extend"
    details: str

    def to_dict(self) -> Dict:
        return {
            "strategy_id": self.strategy_id,
            "passed": self.passed,
            "signal_consistency": round(self.signal_consistency, 4),
            "latency_avg": round(self.latency_avg, 2),
            "deviation": {
                "sharpe": round(self.deviation_sharpe, 4),
                "win_rate": round(self.deviation_win_rate, 4),
                "drawdown": round(self.deviation_drawdown, 4),
            },
            "recommendation": self.recommendation,
            "details": self.details,
        }


# ===================== 孵化器 =====================

class StrategyIncubator:
    """
    策略孵化器

    管理多个策略的孵化会话，记录实盘信号，评估回测 vs 实盘偏差。
    """

    def __init__(self, storage_path: str = None,
                 default_incubation_days: int = 90,
                 default_max_deviation: float = 0.3):
        """
        参数:
            storage_path: 孵化数据存储路径（JSON）
            default_incubation_days: 默认孵化期天数
            default_max_deviation: 默认最大允许偏差
        """
        self.storage_path = storage_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data", "incubation_sessions.json"
        )
        self.default_incubation_days = default_incubation_days
        self.default_max_deviation = default_max_deviation

        # 内存中的会话 {strategy_id: IncubationSession}
        self._sessions: Dict[str, IncubationSession] = {}

        # 加载已有会话
        self._load_sessions()

    def start_incubation(self, strategy_id: str,
                          strategy_config: Dict) -> IncubationSession:
        """
        开始孵化会话

        参数:
            strategy_id: 策略ID
            strategy_config: 策略配置，包含：
                - expected_sharpe: 预期夏普比率
                - expected_win_rate: 预期胜率
                - expected_max_drawdown: 预期最大回撤
                - expected_annual_return: 预期年化收益（可选）
                - incubation_days: 孵化期天数（可选）
                - max_deviation: 最大允许偏差（可选）

        返回:
            IncubationSession
        """
        if strategy_id in self._sessions:
            existing = self._sessions[strategy_id]
            if existing.status == "active":
                raise ValueError(f"策略 {strategy_id} 已有活跃的孵化会话")
            # 如果是已完成/失败的，允许重新开始

        session = IncubationSession(
            strategy_id=strategy_id,
            start_time=datetime.now(),
            status="active",
            expected_sharpe=strategy_config.get("expected_sharpe", 0),
            expected_win_rate=strategy_config.get("expected_win_rate", 0),
            expected_max_drawdown=strategy_config.get("expected_max_drawdown", 0),
            expected_annual_return=strategy_config.get("expected_annual_return", 0),
            incubation_days=strategy_config.get("incubation_days", self.default_incubation_days),
            max_deviation=strategy_config.get("max_deviation", self.default_max_deviation),
        )

        self._sessions[strategy_id] = session
        self._save_sessions()

        logger.info(f"开始孵化策略 {strategy_id}，预期夏普={session.expected_sharpe:.2f}，"
                    f"孵化期={session.incubation_days}天")

        return session

    def record_signal(self, strategy_id: str,
                       timestamp: datetime,
                       signal: float,
                       market_state: Dict = None,
                       expected_signal: float = None) -> None:
        """
        记录实盘信号

        参数:
            strategy_id: 策略ID
            timestamp: 信号时间
            signal: 实盘信号值（如 +1.0=做多, -1.0=做空, 0=无信号）
            market_state: 当时的市场状态（可选）
            expected_signal: 回测预期信号值（可选，用于计算一致性）
        """
        if strategy_id not in self._sessions:
            raise ValueError(f"策略 {strategy_id} 没有活跃的孵化会话")

        session = self._sessions[strategy_id]
        if session.status != "active":
            raise ValueError(f"策略 {strategy_id} 的孵化会话已{session.status}")

        signal_record = {
            "timestamp": timestamp.isoformat(),
            "signal": signal,
            "market_state": market_state or {},
            "expected_signal": expected_signal,
        }

        session.actual_signals.append(signal_record)
        self._save_sessions()

    def evaluate(self, strategy_id: str) -> IncubationResult:
        """
        评估孵化结果

        对比回测预期 vs 实盘表现，输出评估结果。

        参数:
            strategy_id: 策略ID

        返回:
            IncubationResult
        """
        if strategy_id not in self._sessions:
            raise ValueError(f"策略 {strategy_id} 没有孵化会话")

        session = self._sessions[strategy_id]

        # 检查孵化期是否足够
        days_elapsed = (datetime.now() - session.start_time).days
        if days_elapsed < session.incubation_days * 0.5:
            # 孵化期不足一半，建议延长
            return IncubationResult(
                strategy_id=strategy_id,
                passed=False,
                signal_consistency=0.0,
                latency_avg=0.0,
                deviation_sharpe=0.0,
                deviation_win_rate=0.0,
                deviation_drawdown=0.0,
                recommendation="extend",
                details=f"孵化期不足：已运行{days_elapsed}天，需至少{session.incubation_days}天",
            )

        # 计算实盘指标
        signals = [s["signal"] for s in session.actual_signals]
        if not signals:
            return IncubationResult(
                strategy_id=strategy_id,
                passed=False,
                signal_consistency=0.0,
                latency_avg=0.0,
                deviation_sharpe=0.0,
                deviation_win_rate=0.0,
                deviation_drawdown=0.0,
                recommendation="reject",
                details="无实盘信号记录",
            )

        # 信号一致性
        expected_signals = [s.get("expected_signal") for s in session.actual_signals
                           if s.get("expected_signal") is not None]
        if expected_signals and len(expected_signals) == len(signals):
            matches = sum(1 for e, a in zip(expected_signals, signals)
                         if (e > 0 and a > 0) or (e < 0 and a < 0) or (e == 0 and a == 0))
            signal_consistency = matches / len(signals)
        else:
            # 无预期信号时，用信号方向一致性估算
            signal_consistency = 0.5  # 默认中性

        # 实盘夏普估算（简化版）
        if len(signals) > 1:
            signal_returns = np.diff(signals)
            if np.std(signal_returns) > 0:
                actual_sharpe = float(np.mean(signal_returns) / np.std(signal_returns) * np.sqrt(252))
            else:
                actual_sharpe = 0.0
        else:
            actual_sharpe = 0.0

        # 实盘胜率（信号方向正确的比例）
        positive_signals = sum(1 for s in signals if s > 0)
        actual_win_rate = positive_signals / len(signals) if signals else 0

        # 计算偏差
        deviation_sharpe = abs(actual_sharpe - session.expected_sharpe) / max(abs(session.expected_sharpe), 0.1)
        deviation_win_rate = abs(actual_win_rate - session.expected_win_rate) / max(session.expected_win_rate, 0.1)
        deviation_drawdown = 0.0  # 简化版，实际需要计算实盘回撤

        # 判断是否通过
        max_dev = session.max_deviation
        passed = (deviation_sharpe <= max_dev and
                  deviation_win_rate <= max_dev and
                  signal_consistency >= 0.5)

        # 生成建议
        if passed:
            recommendation = "approve"
            details = (f"孵化通过：信号一致性={signal_consistency:.2f}，"
                      f"夏普偏差={deviation_sharpe:.2f}，胜率偏差={deviation_win_rate:.2f}")
        elif days_elapsed < session.incubation_days:
            recommendation = "extend"
            details = (f"建议延长孵化：信号一致性={signal_consistency:.2f}，"
                      f"偏差较大但孵化期不足")
        else:
            recommendation = "reject"
            details = (f"孵化失败：信号一致性={signal_consistency:.2f}，"
                      f"夏普偏差={deviation_sharpe:.2f}，胜率偏差={deviation_win_rate:.2f}")

        # 更新会话状态
        session.end_time = datetime.now()
        session.status = "completed" if passed else "failed"
        self._save_sessions()

        return IncubationResult(
            strategy_id=strategy_id,
            passed=passed,
            signal_consistency=signal_consistency,
            latency_avg=0.0,  # 简化版
            deviation_sharpe=deviation_sharpe,
            deviation_win_rate=deviation_win_rate,
            deviation_drawdown=deviation_drawdown,
            recommendation=recommendation,
            details=details,
        )

    def get_session(self, strategy_id: str) -> Optional[IncubationSession]:
        """获取策略的孵化会话"""
        return self._sessions.get(strategy_id)

    def get_all_sessions(self) -> List[IncubationSession]:
        """获取所有孵化会话"""
        return list(self._sessions.values())

    def get_active_sessions(self) -> List[IncubationSession]:
        """获取所有活跃的孵化会话"""
        return [s for s in self._sessions.values() if s.status == "active"]

    def force_complete(self, strategy_id: str, status: str = "completed") -> None:
        """强制完成孵化会话"""
        if strategy_id in self._sessions:
            self._sessions[strategy_id].end_time = datetime.now()
            self._sessions[strategy_id].status = status
            self._save_sessions()

    # ===================== 持久化 =====================

    def _load_sessions(self):
        """从文件加载会话"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for sid, sdata in data.items():
                    session = IncubationSession(
                        strategy_id=sdata["strategy_id"],
                        start_time=datetime.fromisoformat(sdata["start_time"]),
                        end_time=datetime.fromisoformat(sdata["end_time"]) if sdata.get("end_time") else None,
                        status=sdata.get("status", "active"),
                        expected_sharpe=sdata.get("expected", {}).get("sharpe", 0),
                        expected_win_rate=sdata.get("expected", {}).get("win_rate", 0),
                        expected_max_drawdown=sdata.get("expected", {}).get("max_drawdown", 0),
                        expected_annual_return=sdata.get("expected", {}).get("annual_return", 0),
                        actual_signals=sdata.get("actual_signals", []),
                        incubation_days=sdata.get("incubation_days", 90),
                        max_deviation=sdata.get("max_deviation", 0.3),
                    )
                    self._sessions[sid] = session
            except Exception as e:
                logger.warning(f"加载孵化会话失败: {e}")

    def _save_sessions(self):
        """保存会话到文件"""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            data = {}
            for sid, session in self._sessions.items():
                data[sid] = session.to_dict()
                data[sid]["actual_signals"] = session.actual_signals

            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存孵化会话失败: {e}")
