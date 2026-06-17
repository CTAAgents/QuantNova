"""
推理层

提供 LLM 推理和决策生成功能：
- ReasoningEngine: LLM 推理引擎
- DebateEngine: 多角色辩论
- ScenarioAnalyzer: 场景分析
- BriefGenerator: 决策简报生成
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trend_scanner.reasoning import (
    ReasoningEngine,
    LLMProvider,
    WorkBuddyAgentProvider,
    CustomLLMProvider,
    ConstraintGenerator,
)
from trend_scanner.debate_engine import DebateReasoningEngine
from trend_scanner.scenario_analyzer import ScenarioAnalyzer
from trend_scanner.brief import BriefGenerator

__all__ = [
    "ReasoningEngine",
    "LLMProvider",
    "WorkBuddyAgentProvider",
    "CustomLLMProvider",
    "ConstraintGenerator",
    "DebateReasoningEngine",
    "ScenarioAnalyzer",
    "BriefGenerator",
]
