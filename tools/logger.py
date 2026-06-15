"""
统一日志格式模块

提供结构化的 JSON 日志输出，支持 trace_id 追踪完整链路。

使用方式：
    from logger import AgentLogger
    
    logger = AgentLogger("scanner")
    logger.info("扫描完成", {"symbols_scanned": 30, "signals_found": 3})
    logger.warn("数据不足", {"symbol": "DCE.jm2609", "data_count": 21})
    logger.error("TqSdk 连接失败", {"error": "timeout"})
"""

import json
import os
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

# 日志目录
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')


class AgentLogger:
    """Agent 统一日志"""
    
    def __init__(self, component: str, trace_id: str = None):
        """
        初始化日志器
        
        参数:
            component: 组件名称（scanner/reasoner/debater/monitor/evolver/orchestrator）
            trace_id: 追踪 ID（用于链路追踪）
        """
        self.component = component
        self.trace_id = trace_id or str(uuid.uuid4())[:8]
        self.log_file = os.path.join(LOG_DIR, f"{datetime.now().strftime('%Y-%m-%d')}.jsonl")
        
        # 确保日志目录存在
        os.makedirs(LOG_DIR, exist_ok=True)
    
    def _log(self, level: str, message: str, context: Dict[str, Any] = None):
        """写入日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "component": self.component,
            "level": level,
            "trace_id": self.trace_id,
            "message": message,
            "context": context or {}
        }
        
        # 写入文件
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        
        # 输出到控制台（简化格式）
        time_str = datetime.now().strftime('%H:%M:%S')
        context_str = ""
        if context:
            context_items = [f"{k}={v}" for k, v in context.items()]
            context_str = f" [{', '.join(context_items)}]"
        print(f"[{time_str}] [{self.component}] [{level}] {message}{context_str}")
    
    def info(self, message: str, context: Dict[str, Any] = None):
        """信息日志"""
        self._log("INFO", message, context)
    
    def warn(self, message: str, context: Dict[str, Any] = None):
        """警告日志"""
        self._log("WARN", message, context)
    
    def error(self, message: str, context: Dict[str, Any] = None):
        """错误日志"""
        self._log("ERROR", message, context)
    
    def debug(self, message: str, context: Dict[str, Any] = None):
        """调试日志"""
        self._log("DEBUG", message, context)
    
    def create_child(self, component: str) -> 'AgentLogger':
        """创建子日志器（共享 trace_id）"""
        return AgentLogger(component, self.trace_id)


def create_trace() -> str:
    """创建新的追踪 ID"""
    return str(uuid.uuid4())[:8]


def get_logger(component: str, trace_id: str = None) -> AgentLogger:
    """获取日志器实例"""
    return AgentLogger(component, trace_id)


# 示例使用
if __name__ == "__main__":
    # 创建追踪
    trace_id = create_trace()
    
    # 创建日志器
    scanner_logger = get_logger("scanner", trace_id)
    scanner_logger.info("开始扫描", {"symbols": ["SHFE.rb", "DCE.jm"]})
    scanner_logger.info("扫描完成", {"total_scanned": 30, "signals_found": 3})
    
    # 创建子日志器（共享 trace_id）
    reasoner_logger = scanner_logger.create_child("reasoner")
    reasoner_logger.info("开始推理", {"signals": 3})
    reasoner_logger.info("推理完成", {"confidence": 0.75})
    
    # 创建子日志器
    debater_logger = reasoner_logger.create_child("debater")
    debater_logger.info("开始辩论", {"symbol": "DCE.jm2609"})
    debater_logger.warn("分歧度高", {"divergence_level": "HIGH"})
    
    print(f"\n追踪链路: {trace_id}")
    print(f"日志文件: {scanner_logger.log_file}")
