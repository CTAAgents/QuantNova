"""
因子进化层

提供因子发现和进化功能：
- FactorGenerator: 因子生成
- FactorEvaluator: 因子评估
- FactorGate: 门控决策
- FactorEvolutionEngine: 闭环进化
- FactorParamOptimizer: 参数优化
- SeedFactorPool: 种子因子池
- MultiFactorModel: 多因子模型
- FactorExperienceDB: 经验数据库
- WalkForwardValidator: Walk-Forward 验证
- VisibilityGraph: 可见图指标
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trend_scanner.factor_generator import FactorGenerator
from trend_scanner.factor_evaluator import FactorEvaluator
from trend_scanner.factor_gate import FactorGate
from trend_scanner.factor_evolution_engine import FactorEvolutionEngine
from trend_scanner.factor_param_optimizer import FactorParamOptimizer
from trend_scanner.seed_factor_pool import SeedFactorPool
from trend_scanner.multi_factor_model import MultiFactorModel
from trend_scanner.factor_experience_db import FactorExperienceDB
from trend_scanner.walk_forward_validator import WalkForwardValidator
from trend_scanner.visibility_graph import VisibilityGraph

__all__ = [
    "FactorGenerator",
    "FactorEvaluator",
    "FactorGate",
    "FactorEvolutionEngine",
    "FactorParamOptimizer",
    "SeedFactorPool",
    "MultiFactorModel",
    "FactorExperienceDB",
    "WalkForwardValidator",
    "VisibilityGraph",
]
