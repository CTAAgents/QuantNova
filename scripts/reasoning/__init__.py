"""
推理层

提供 LLM 推理和决策生成功能：
- ReasoningEngine: LLM 推理引擎
- DebateEngine: 多角色辩论
- ScenarioAnalyzer: 场景分析
- BriefGenerator: 决策简报生成
- HallucinationDetector: 幻觉检测
- AdaptivePromptRouter: 自适应Prompt路由
"""

from .hallucination_detector import HallucinationDetector, HallucinationType
from .adaptive_prompt_router import AdaptivePromptRouter, PromptTemplateType

__all__ = [
    "HallucinationDetector",
    "HallucinationType",
    "AdaptivePromptRouter",
    "PromptTemplateType",
]
