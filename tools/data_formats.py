"""
运行时数据格式定义和读写工具

定义 latest_scan.json 和 latest_monitor.json 的数据格式，
提供统一的读写接口。

数据流：
    Scanner 脚本 → write_scan_result() → latest_scan.json → Orchestrator 读取
    Monitor 脚本 → write_monitor_result() → latest_monitor.json → Orchestrator 读取
"""

import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

# 数据目录
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')

# 文件路径
LATEST_SCAN_FILE = os.path.join(DATA_DIR, 'latest_scan.json')
LATEST_MONITOR_FILE = os.path.join(DATA_DIR, 'latest_monitor.json')


# ============================================================
# Scanner 数据格式
# ============================================================

def create_scan_result(
    total_scanned: int,
    signals: List[Dict[str, Any]],
    no_signal_symbols: List[str] = None
) -> Dict[str, Any]:
    """
    创建扫描结果数据结构
    
    参数:
        total_scanned: 扫描的品种总数
        signals: 有信号的品种列表
        no_signal_symbols: 无信号的品种列表
    
    返回:
        符合格式的字典
    """
    return {
        "scan_time": datetime.now().isoformat(),
        "total_scanned": total_scanned,
        "signals": signals,
        "no_signal_symbols": no_signal_symbols or [],
        "signal_count": len(signals)
    }


def create_signal(
    symbol: str,
    trend_phase: str,
    trend_strength_composite: float,
    tsi: float,
    er: float,
    r_squared: float,
    direction: str,
    signal_strength: str,
    trigger_reason: str,
    **extra
) -> Dict[str, Any]:
    """
    创建单个信号数据结构
    
    参数:
        symbol: 品种代码（如 SHFE.rb2510）
        trend_phase: 趋势阶段（CONSOLIDATING/EMERGING/DEVELOPING/MATURE/FATIGUING/REVERSING）
        trend_strength_composite: 复合趋势强度 [0, 1]
        tsi: TSI 值 [-100, 100]
        er: 效率比 [0, 1]
        r_squared: R² 拟合度 [0, 1]
        direction: 方向（LONG/SHORT）
        signal_strength: 信号强度（WEAK/MEDIUM/STRONG）
        trigger_reason: 触发原因描述
    
    返回:
        符合格式的字典
    """
    signal = {
        "symbol": symbol,
        "trend_phase": trend_phase,
        "trend_strength_composite": round(trend_strength_composite, 3),
        "tsi": round(tsi, 2),
        "er": round(er, 3),
        "r_squared": round(r_squared, 3),
        "direction": direction,
        "signal_strength": signal_strength,
        "trigger_reason": trigger_reason
    }
    signal.update(extra)
    return signal


def write_scan_result(result: Dict[str, Any]):
    """写入扫描结果到 latest_scan.json"""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LATEST_SCAN_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


def read_scan_result() -> Optional[Dict[str, Any]]:
    """读取最新扫描结果"""
    if not os.path.exists(LATEST_SCAN_FILE):
        return None
    with open(LATEST_SCAN_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


# ============================================================
# Monitor 数据格式
# ============================================================

def create_monitor_result(
    positions_monitored: int,
    alerts: List[Dict[str, Any]],
    no_alert_positions: List[str] = None
) -> Dict[str, Any]:
    """
    创建监控结果数据结构
    
    参数:
        positions_monitored: 监控的持仓品种数
        alerts: 预警列表
        no_alert_positions: 无预警的持仓品种列表
    
    返回:
        符合格式的字典
    """
    return {
        "monitor_time": datetime.now().isoformat(),
        "positions_monitored": positions_monitored,
        "alerts": alerts,
        "no_alert_positions": no_alert_positions or [],
        "alert_count": len(alerts)
    }


def create_alert(
    symbol: str,
    alert_type: str,
    severity: str,
    indicators: Dict[str, Any],
    trigger_reason: str
) -> Dict[str, Any]:
    """
    创建单个预警数据结构
    
    参数:
        symbol: 品种代码
        alert_type: 预警类型（TREND_REVERSAL/STOP_LOSS/TAKE_PROFIT/VOLATILITY_EXPANSION）
        severity: 严重程度（LOW/MEDIUM/HIGH）
        indicators: 相关指标值
        trigger_reason: 触发原因描述
    
    返回:
        符合格式的字典
    """
    return {
        "symbol": symbol,
        "type": alert_type,
        "severity": severity,
        "indicators": indicators,
        "trigger_reason": trigger_reason,
        "alert_time": datetime.now().isoformat()
    }


def write_monitor_result(result: Dict[str, Any]):
    """写入监控结果到 latest_monitor.json"""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LATEST_MONITOR_FILE, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


def read_monitor_result() -> Optional[Dict[str, Any]]:
    """读取最新监控结果"""
    if not os.path.exists(LATEST_MONITOR_FILE):
        return None
    with open(LATEST_MONITOR_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


# ============================================================
# 配置读取
# ============================================================

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'config.json')


def load_config() -> Dict[str, Any]:
    """加载配置文件"""
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_config(config: Dict[str, Any]):
    """保存配置文件"""
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_scanner_config() -> Dict[str, Any]:
    """获取 Scanner 配置"""
    config = load_config()
    return config.get("scanner", {})


def get_monitor_config() -> Dict[str, Any]:
    """获取 Monitor 配置"""
    config = load_config()
    return config.get("monitor", {})


def get_signal_filter() -> Dict[str, Any]:
    """获取信号筛选条件"""
    scanner_config = get_scanner_config()
    return scanner_config.get("signal_filter", {
        "er_min": 0.6,
        "tsi_min": 20,
        "tsi_max": -20,
        "trend_strength_min": 0.5,
        "r2_min": 0.4
    })
