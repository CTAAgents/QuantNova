"""
趋势跟踪决策辅助系统

系统提供态势研判、风险提示与操作建议，最终决策权在交易者手中。

模块结构：
- models: 数据模型（MarketContext, Experience, Route, TradingBrief 等）
- indicators: 技术指标计算（感知层）
- context: 上下文组装器（感知层输出）
- experience: 经验记忆池（类比推理基础）
- reasoning: 推理引擎（系统大脑）
- brief: 交易决策简报生成器（交互层）
- assistant: 主协调器（交易辅助系统）
- data_store: 数据持久化
"""

# 版本信息
from .__version__ import (
    __version__,
    __version_info__,
    format_version,
    get_version,
    get_version_info,
)

# 分析工具
from .analytics import KPICalculator, StateAccuracyTracker, TradeAttributor

# 回测框架
from .backtest import MonteCarloValidator, WalkForwardBacktester

# 信念传播与概念性反馈（FinCon 架构）
from .belief_propagation import BeliefPropagationManager

# 交互层
from .brief import BriefFormatter, BriefGenerator
from .conceptual_feedback import ConceptualFeedbackGenerator
from .context import ContextAssembler

# 控制变量隔离
from .control_variable import (
    ControlVariableAnalyzer,
    analyze_llm_contribution,
    get_fixed_layers,
    get_llm_layers,
    get_system_layers,
)

# 数据源适配器
from .data_source import (
    CsvSource,
    DataSource,
    DataSourceFactory,
    TqSdkSource,
    get_active_symbols,
    get_kline,
    get_quote,
)

# 数据存储
from .data_store import ConfigManager, DataStore

# 辩论引擎（路径④）
from .debate_engine import DebateReasoningEngine, create_debate_engine

# 进化引擎
from .evolution import (
    EnhancedEvolutionEngine,
    OverfittingGuard,
    SelfMonitor,
    StrategyWeightAdjuster,
    WalkForwardOptimizer,
)

# 进化管理器（连接推理架构与自进化能力）
from .evolution_manager import EvolutionManager, EvolutionManagerFactory

# 执行引擎
from .execution import ExecutionEngine, PositionState, RiskGuard, TradeFilter

# 经验层
from .experience import ExperienceMemory

# v5.0 因子进化子系统
from .factor_evaluator import (
    BUILTIN_FACTORS,
    FactorEvaluationResult,
    FactorEvaluator,
)
from .factor_evolution_engine import EvolutionResult, FactorEvolutionEngine
from .factor_executor import FactorExecutor
from .factor_experience_db import FactorExperienceDB
from .factor_gate import FactorGate, GateDecision

# 因子生成与验证
from .factor_generator import (
    FactorGenerator,
    FactorKnowledgeManager,
    FactorResult,
    FactorValidator,
)
from .factor_param_optimizer import FactorParamOptimizer, OptimizationResult
from .factor_validator import FactorValidator as FactorCodeValidator

# 感知层
from .indicators import IndicatorEngine
from .llm_factor_client import LLMClient

# 宏观状态检测
from .macro_state import MacroStateDetector

# 市场分析
from .market_analysis import (
    LLMReasoningLayer,
    MarketStateClassifier,
    MultiIndicatorConsensus,
    TrendPhaseDetector,
)

# 记忆桥接器
from .memory_bridge import MemoryBridge

# 向量化记忆
from .memory_vectorizer import (
    MemoryEntry,
    MemoryVectorizer,
    SearchResult,
    create_vectorizer,
    encode_text,
    search_memories,
)

# 元学习
from .meta_learner import (
    BayesianScoringOptimizer,
    MetaLearningEngine,
    OptimizationResult,
    ParameterSpace,
)

# 元技能引擎
from .meta_skill_engine import (
    AuditReport,
    AuditResult,
    GeneratedSkill,
    MetaSkillEngine,
    SkillEvolution,
    SkillGenerationPhase,
)

# 数据模型（v3.0 核心）
# 交易记录（兼容旧版测试）
from .models import (
    Constraint,
    Experience,
    ExperienceMatch,
    IndicatorSnapshot,
    MarketAssessment,
    MarketContext,
    MarketStructure,
    MomentumState,
    Route,
    ScoringFeedback,
    TradeRecord,
    TradeSignal,
    TradingBrief,
    TrendPhase,
    TrendPhaseInfo,
    Uncertainty,
    UserFeedback,
    VolatilityState,
)
from .multi_factor_model import ModelResult, MultiFactorModel

# 叙事生成器（路径①）
from .narrative_generator import (
    NarrativeGenerator,
    RuleGenerator,
    generate_narrative,
    generate_rules_from_narrative,
)

# 主协调器
from .navigator import TradingAssistant, TradingAssistantFactory

# 过拟合审计
from .overfitting_audit import (
    AuditCheck,
    AuditCheckType,
    AuditSeverity,
    OverfittingAuditor,
)

# 过拟合检测
from .overfitting_detector import OverfittingDetector

# 组合管理
from .portfolio import PortfolioManager

# 持仓健康度评估
from .position_health import PositionHealthChecker

# 仓位管理
from .position_sizer import PositionSizer

# 推理层
from .reasoning import (
    ConstraintGenerator,
    CustomLLMProvider,
    LLMProvider,
    ReasoningEngine,
    WorkBuddyAgentProvider,
)

# 机制门
from .regime_gate import (
    RegimeAwareRetriever,
    RegimeGate,
    RegimeMatchResult,
)

# 分层机制检测
from .regime_segmenter import (
    HierarchicalRegimeDetector,
    PhaseLabeler,
    RegimeSegment,
    RegimeSegmenter,
)

# 研报解析
from .report_parser import ReportParser

# 风险管理
from .risk_management import ExitSignalGenerator, RiskManager

# RL 接口设计（GIFT 架构）
from .rl_interface_designer import RLInterfaceDesigner

# 主扫描器
from .scanner import AdaptiveTrendSystem, TrendScanner

# 打分分析
from .scoring_analytics import ScoringAnalytics
from .seed_factor_pool import SeedFactorPool

# 选择性更新
from .selective_update import (
    DecayConfig,
    ExperiencePoolManager,
    KnowledgeDistiller,
    SelectiveUpdater,
)

# 静默旁路检测
from .silent_bypass_detector import (
    ActionRecommendation,
    BypassPattern,
    BypassReason,
    BypassReport,
    SilentBypassDetector,
    StrategyUsageStats,
)

# 技能反思
from .skill_reflection import (
    EvidenceType,
    GuidanceReinforcement,
    ReflectionEvidence,
    RevisionAction,
    SkillAwareReflector,
    SkillReflection,
)

# 止损管理
from .stop_loss import StopLossCalculator

# 策略池
from .strategy import StrategyPool

# 策略健康度
from .strategy_health import StrategyHealthChecker

# 阈值优化
from .threshold_optimizer import ThresholdOptimizer

# 交易日志
from .trade_journal import (
    EntryCategory,
    PatternDetector,
    RecurringPattern,
    RulePromoter,
    StrategyRule,
    TradeJournal,
    TradeJournalEntry,
)

# 轨迹分析
from .trajectory_analysis import (
    AdaptationProposal,
    AdaptationStatus,
    Fault,
    StrategyAdapter,
    TradeFaultAttributor,
    TradeTrajectory,
    TradeTrajectoryAnalyzer,
)

# 向量增强
from .vector_enhancement import (
    FeatureVector,
    MultiGranularityRetriever,
    VectorEnhancer,
)

# v6.0 新增模块（论文吸收 arXiv:2605.01300）
from .visibility_graph import (
    VGRSI,
    MultiTimeframeVGRSI,
    MultiTimeframeVGRSIFactor,
    VisibilityGraph,
    calculate_vgrsi,
    calculate_vgrsi_multi_timeframe,
    consensus_factor,
)
from .visibility_graph_operator import (
    VisibilityGraphOperator,
    get_visibility_example_factors,
    get_visibility_operator_descriptions,
)
from .volatility_anchor import (
    VolatilityAnchor,
    volatility_anchor,
)
from .walk_forward_validator import (
    WalkForwardConfig,
    WalkForwardResult,
    WalkForwardValidator,
    walk_forward_validate,
)

# 权重优化
from .weight_optimizer import WeightOptimizer


__all__ = [
    # 版本信息
    "__version__",
    "__version_info__",
    "get_version",
    "get_version_info",
    "format_version",
    # 数据模型（v3.0 核心）
    "MarketContext",
    "IndicatorSnapshot",
    "MarketStructure",
    "MomentumState",
    "VolatilityState",
    "TrendPhase",
    "Experience",
    "ExperienceMatch",
    "Route",
    "Constraint",
    "MarketAssessment",
    "Uncertainty",
    "TradingBrief",
    "UserFeedback",
    "ScoringFeedback",
    # 兼容旧版测试
    "TradeRecord",
    "TradeSignal",
    "TrendPhaseInfo",
    # 感知层
    "IndicatorEngine",
    "ContextAssembler",
    # 经验层
    "ExperienceMemory",
    # 推理层
    "ReasoningEngine",
    "LLMProvider",
    "WorkBuddyAgentProvider",
    "CustomLLMProvider",
    "ConstraintGenerator",
    # 交互层
    "BriefGenerator",
    "BriefFormatter",
    # 辩论引擎
    "DebateReasoningEngine",
    "create_debate_engine",
    # 叙事生成器
    "NarrativeGenerator",
    "RuleGenerator",
    "generate_narrative",
    "generate_rules_from_narrative",
    # 控制变量隔离
    "ControlVariableAnalyzer",
    "get_system_layers",
    "get_fixed_layers",
    "get_llm_layers",
    "analyze_llm_contribution",
    # 向量化记忆
    "MemoryVectorizer",
    "MemoryEntry",
    "SearchResult",
    "create_vectorizer",
    "encode_text",
    "search_memories",
    # 主协调器
    "TradingAssistant",
    "TradingAssistantFactory",
    # 数据存储
    "DataStore",
    "ConfigManager",
    # 市场分析
    "MultiIndicatorConsensus",
    "TrendPhaseDetector",
    "MarketStateClassifier",
    "LLMReasoningLayer",
    # 策略池
    "StrategyPool",
    # 主扫描器
    "TrendScanner",
    "AdaptiveTrendSystem",
    # 风险管理
    "RiskManager",
    "ExitSignalGenerator",
    # 持仓健康度评估
    "PositionHealthChecker",
    # 进化引擎
    "SelfMonitor",
    "WalkForwardOptimizer",
    "StrategyWeightAdjuster",
    "OverfittingGuard",
    "EnhancedEvolutionEngine",
    # 进化管理器
    "EvolutionManager",
    "EvolutionManagerFactory",
    # 轨迹分析
    "TradeTrajectoryAnalyzer",
    "TradeFaultAttributor",
    "StrategyAdapter",
    "TradeTrajectory",
    "Fault",
    "AdaptationProposal",
    "AdaptationStatus",
    # 交易日志
    "TradeJournal",
    "PatternDetector",
    "RulePromoter",
    "TradeJournalEntry",
    "RecurringPattern",
    "StrategyRule",
    "EntryCategory",
    # 技能反思
    "SkillAwareReflector",
    "SkillReflection",
    "ReflectionEvidence",
    "GuidanceReinforcement",
    "EvidenceType",
    "RevisionAction",
    # 元技能引擎
    "MetaSkillEngine",
    "GeneratedSkill",
    "SkillEvolution",
    "AuditResult",
    "AuditReport",
    "SkillGenerationPhase",
    # 过拟合审计
    "OverfittingAuditor",
    "AuditCheckType",
    "AuditSeverity",
    "AuditCheck",
    # 静默旁路检测
    "SilentBypassDetector",
    "BypassReason",
    "ActionRecommendation",
    "BypassPattern",
    "BypassReport",
    "StrategyUsageStats",
    # 分析工具
    "KPICalculator",
    "TradeAttributor",
    "StateAccuracyTracker",
    # 打分分析
    "ScoringAnalytics",
    # 权重优化
    "WeightOptimizer",
    # 阈值优化
    "ThresholdOptimizer",
    # 元学习
    "MetaLearningEngine",
    "BayesianScoringOptimizer",
    "OptimizationResult",
    "ParameterSpace",
    # 向量增强
    "FeatureVector",
    "VectorEnhancer",
    "MultiGranularityRetriever",
    # 机制门
    "RegimeGate",
    "RegimeAwareRetriever",
    "RegimeMatchResult",
    # 分层机制检测
    "RegimeSegment",
    "RegimeSegmenter",
    "PhaseLabeler",
    "HierarchicalRegimeDetector",
    # 选择性更新
    "DecayConfig",
    "SelectiveUpdater",
    "KnowledgeDistiller",
    "ExperiencePoolManager",
    # 数据源适配器
    "DataSource",
    "TqSdkSource",
    "CsvSource",
    "DataSourceFactory",
    "get_kline",
    "get_quote",
    "get_active_symbols",
    # v5.0 因子进化子系统
    "FactorEvaluator",
    "FactorEvaluationResult",
    "BUILTIN_FACTORS",
    "FactorExecutor",
    "FactorGate",
    "GateDecision",
    "FactorEvolutionEngine",
    "EvolutionResult",
    "FactorParamOptimizer",
    "OptimizationResult",
    "SeedFactorPool",
    "MultiFactorModel",
    "ModelResult",
    "FactorExperienceDB",
    # 因子生成与验证
    "FactorGenerator",
    "FactorValidator",
    "FactorKnowledgeManager",
    "FactorResult",
    "FactorCodeValidator",
    "LLMClient",
    # 研报解析
    "ReportParser",
    # 信念传播与概念性反馈
    "BeliefPropagationManager",
    "ConceptualFeedbackGenerator",
    # RL 接口设计
    "RLInterfaceDesigner",
    # 执行引擎
    "ExecutionEngine",
    "PositionState",
    "RiskGuard",
    "TradeFilter",
    # 仓位管理
    "PositionSizer",
    # 止损管理
    "StopLossCalculator",
    # 组合管理
    "PortfolioManager",
    # 回测框架
    "WalkForwardBacktester",
    "MonteCarloValidator",
    # 过拟合检测
    "OverfittingDetector",
    # 策略健康度
    "StrategyHealthChecker",
    # 宏观状态检测
    "MacroStateDetector",
    # 记忆桥接器
    "MemoryBridge",
    # v6.0 新增模块（论文吸收 arXiv:2605.01300）
    "VisibilityGraph",
    "VGRSI",
    "MultiTimeframeVGRSI",
    "MultiTimeframeVGRSIFactor",
    "consensus_factor",
    "calculate_vgrsi",
    "calculate_vgrsi_multi_timeframe",
    "WalkForwardValidator",
    "WalkForwardConfig",
    "WalkForwardResult",
    "walk_forward_validate",
    "VisibilityGraphOperator",
    "get_visibility_operator_descriptions",
    "get_visibility_example_factors",
    "VolatilityAnchor",
    "volatility_anchor",
]
