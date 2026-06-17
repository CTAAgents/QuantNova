# Config 统一化 + ElegantRL 融合实施计划

> 版本：v1.0 | 创建日期：2026-06-17
> 状态：进行中

---

## 一、项目概述

### 1.1 目标

1. **Config 统一化**：创建统一的 `TrendScannerConfig` 对象，消除配置分散问题
2. **ElegantRL 融合**：借鉴 ElegantRL 的架构设计模式，引入真正的 RL 训练能力

### 1.2 背景

当前系统存在两个核心问题：
1. 配置分散在多个 JSON 文件和代码硬编码中，难以统一管理
2. 只有 LLM 引导的 RL 接口设计（rl_interface_designer.py），没有真正的 RL 训练能力

### 1.3 范围

- Phase 1-2：Config 统一化（基础层）
- Phase 3-4：Gym 环境封装 + PPO 训练器（ElegantRL 融合）
- Phase 5：Walk-Forward + RL 验证（集成验证）

---

## 二、任务清单

### Phase 1: Config 统一化（基础层）

| 任务 | 描述 | 状态 | 交付物 |
|------|------|------|--------|
| 1.1 设计 TrendScannerConfig | 统一配置数据类，覆盖所有模块 | ⬜ | config.py |
| 1.2 实现配置加载器 | 支持 JSON/YAML/环境变量 | ⬜ | config_loader.py |
| 1.3 迁移现有配置 | 将 config/*.json 迁移到新结构 | ⬜ | 配置文件更新 |
| 1.4 更新 Scanner/Reasoner/Evolver | 使用统一配置 | ⬜ | 模块更新 |
| 1.5 编写单元测试 | 测试配置加载和验证 | ⬜ | test_config.py |

### Phase 2: RL 基础设施（ElegantRL 借鉴）

| 任务 | 描述 | 状态 | 交付物 |
|------|------|------|--------|
| 2.1 AgentBase 基类 | 定义统一的 Agent 生命周期 | ⬜ | base.py |
| 2.2 ReplayBuffer 实现 | 借鉴 ElegantRL 的向量化缓冲区 | ⬜ | replay_buffer.py |
| 2.3 Evaluator 实现 | 训练内评估 + 学习曲线 | ⬜ | evaluator.py |
| 2.4 编写单元测试 | 测试基础设施 | ⬜ | test_rl_base.py |

### Phase 3: Gym 环境封装

| 任务 | 描述 | 状态 | 交付物 |
|------|------|------|--------|
| 3.1 FuturesTradingEnv | 期货交易 Gym 环境 | ⬜ | futures_env.py |
| 3.2 状态空间实现 | 基于 rl_interface_designer 的输出 | ⬜ | 状态特征映射 |
| 3.3 奖励函数实现 | 基于 RewardFunctionDesign | ⬜ | 奖励计算 |
| 3.4 多品种 VecEnv | 并行环境封装 | ⬜ | vec_env.py |
| 3.5 编写单元测试 | 测试环境兼容性 | ⬜ | test_futures_env.py |

### Phase 4: PPO 训练器集成

| 任务 | 描述 | 状态 | 交付物 |
|------|------|------|--------|
| 4.1 ActorPPO 网络 | 策略网络（含状态归一化） | ⬜ | networks.py |
| 4.2 CriticPPO 网络 | 价值网络 | ⬜ | networks.py |
| 4.3 AgentPPO 实现 | PPO 算法（GAE + Clipping） | ⬜ | agent_ppo.py |
| 4.4 训练循环 | 单进程训练主循环 | ⬜ | trainer.py |
| 4.5 编写单元测试 | 测试 PPO 训练 | ⬜ | test_ppo.py |

### Phase 5: Walk-Forward + RL 验证

| 任务 | 描述 | 状态 | 交付物 |
|------|------|------|--------|
| 5.1 WalkForwardRLValidator | 扩展 WF 支持 RL 策略 | ⬜ | walk_forward_rl.py |
| 5.2 IS/OOS 一致性检查 | RL 策略的泛化验证 | ⬜ | 验证逻辑 |
| 5.3 集成到 Evolver | RL 诊断注入进化流程 | ⬜ | evolver 更新 |
| 5.4 编写单元测试 | 测试验证流程 | ⬜ | test_walk_forward_rl.py |

---

## 三、技术设计

### 3.1 TrendScannerConfig 设计

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class DataConfig:
    """数据源配置"""
    primary_source: str = "tqsdk"  # tqsdk, duckdb, tdx
    fallback_sources: List[str] = field(default_factory=lambda: ["duckdb", "tdx"])
    cache_dir: str = "data/cache"
    db_path: str = "data/market.db"

@dataclass
class ScannerConfig:
    """Scanner 配置"""
    scan_symbols: List[str] = field(default_factory=lambda: ["RB", "I", "J", "JM"])
    use_multi_dimension: bool = True
    dimension_weights: Dict[str, float] = field(default_factory=lambda: {
        "trend": 0.30,
        "momentum": 0.25,
        "volume": 0.20,
        "volatility": 0.15,
        "channel": 0.10
    })

@dataclass
class ReasonerConfig:
    """Reasoner 配置"""
    llm_model: str = "mimo-v2.5-pro"
    llm_endpoint: str = "https://token-plan-cn.xiaomimimo.com/v1"
    output_level: str = "standard"  # formal, standard, brief
    use_knowledge_anchors: bool = True

@dataclass
class EvolverConfig:
    """Evolver 配置"""
    walk_forward_window: int = 30
    walk_forward_test_days: int = 7
    min_trades: int = 10
    min_sharpe: float = 0.5
    max_drawdown: float = 0.20

@dataclass
class RLConfig:
    """RL 训练配置"""
    enabled: bool = False
    algorithm: str = "ppo"  # ppo, sac
    net_dims: List[int] = field(default_factory=lambda: [128, 128])
    gamma: float = 0.99
    lambda_gae: float = 0.95
    learning_rate: float = 2e-4
    batch_size: int = 256
    horizon_len: int = 2048
    repeat_times: int = 10

@dataclass
class TrendScannerConfig:
    """统一配置对象"""
    data: DataConfig = field(default_factory=DataConfig)
    scanner: ScannerConfig = field(default_factory=ScannerConfig)
    reasoner: ReasonerConfig = field(default_factory=ReasonerConfig)
    evolver: EvolverConfig = field(default_factory=EvolverConfig)
    rl: RLConfig = field(default_factory=RLConfig)
    
    @classmethod
    def from_json(cls, path: str) -> 'TrendScannerConfig':
        """从 JSON 文件加载配置"""
        import json
        with open(path, 'r') as f:
            data = json.load(f)
        return cls(**data)
    
    def to_json(self, path: str):
        """保存配置到 JSON 文件"""
        import json
        from dataclasses import asdict
        with open(path, 'w') as f:
            json.dump(asdict(self), f, indent=2)
```

### 3.2 AgentBase 设计（借鉴 ElegantRL）

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple

class AgentBase(ABC):
    """Agent 基类，定义统一生命周期"""
    
    def __init__(self, config: TrendScannerConfig):
        self.config = config
    
    @abstractmethod
    def perceive(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """感知：从环境中获取信息"""
        pass
    
    @abstractmethod
    def reason(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """推理：基于观察做出判断"""
        pass
    
    @abstractmethod
    def act(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """行动：执行决策"""
        pass
    
    @abstractmethod
    def reflect(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """反思：评估结果，更新记忆"""
        pass
    
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """完整流程：感知→推理→行动→反思"""
        obs = self.perceive(context)
        decision = self.reason(obs)
        result = self.act(decision)
        reflection = self.reflect(result)
        return reflection
```

### 3.3 FuturesTradingEnv 设计（Gym 兼容）

```python
import gymnasium as gym
import numpy as np
from typing import Tuple, Dict, Any

class FuturesTradingEnv(gym.Env):
    """期货交易 Gym 环境"""
    
    metadata = {'render_modes': ['human']}
    
    def __init__(self, 
                 data: np.ndarray,
                 state_features: List[str],
                 reward_components: List[Dict],
                 transaction_cost: float = 0.00012,
                 slippage: float = 1.0):
        super().__init__()
        
        self.data = data  # K线数据
        self.state_features = state_features
        self.reward_components = reward_components
        self.transaction_cost = transaction_cost
        self.slippage = slippage
        
        # 状态空间：技术指标 + 持仓状态
        self.observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf,
            shape=(len(state_features) + 1,),  # +1 for position
            dtype=np.float32
        )
        
        # 动作空间：[-1, 1] 表示仓位方向和大小
        self.action_space = gym.spaces.Box(
            low=-1.0, high=1.0,
            shape=(1,),
            dtype=np.float32
        )
        
        self.current_step = 0
        self.position = 0.0
        self.entry_price = 0.0
    
    def reset(self, seed=None, options=None) -> Tuple[np.ndarray, Dict]:
        """重置环境"""
        super().reset(seed=seed)
        self.current_step = 0
        self.position = 0.0
        self.entry_price = 0.0
        return self._get_observation(), {}
    
    def step(self, action: float) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """执行一步"""
        # 解析动作
        target_position = float(action)
        
        # 计算交易成本
        position_change = abs(target_position - self.position)
        cost = position_change * self.transaction_cost * self.data[self.current_step, 3]  # close price
        cost += position_change * self.slippage
        
        # 更新持仓
        self.position = target_position
        self.entry_price = self.data[self.current_step, 3]
        
        # 移动到下一步
        self.current_step += 1
        
        # 计算收益
        if self.current_step < len(self.data) - 1:
            price_return = (self.data[self.current_step, 3] - self.entry_price) / self.entry_price
            reward = self.position * price_return - cost
        else:
            reward = -cost  # 最后一步强制平仓
        
        # 检查是否结束
        terminated = self.current_step >= len(self.data) - 1
        truncated = False
        
        return self._get_observation(), reward, terminated, truncated, {}
    
    def _get_observation(self) -> np.ndarray:
        """获取当前观察"""
        # 这里应该根据 state_features 计算技术指标
        # 简化版本：返回价格和持仓
        obs = np.array([
            self.data[self.current_step, 3],  # close price
            self.position
        ], dtype=np.float32)
        return obs
```

---

## 四、测试用例

### 4.1 Config 测试

| 测试场景 | 输入 | 预期输出 | 状态 |
|----------|------|----------|------|
| 默认配置 | 无 | 各字段有默认值 | ⬜ |
| JSON 加载 | config.json | 正确解析所有字段 | ⬜ |
| 环境变量覆盖 | TQ_USER=xxx | 优先使用环境变量 | ⬜ |
| 配置验证 | 无效值 | 抛出 ValidationError | ⬜ |

### 4.2 Gym 环境测试

| 测试场景 | 输入 | 预期输出 | 状态 |
|----------|------|----------|------|
| reset() | 无 | 返回初始状态 | ⬜ |
| step(0.5) | 持仓0→0.5 | 正确计算收益和成本 | ⬜ |
| step(-1.0) | 持仓0.5→-1 | 平仓+开空，成本正确 | ⬜ |
| check_env() | 环境实例 | 通过 Gym 兼容性检查 | ⬜ |

### 4.3 PPO 训练测试

| 测试场景 | 输入 | 预期输出 | 状态 |
|----------|------|----------|------|
| 网络前向传播 | 状态向量 | 动作/价值输出 | ⬜ |
| GAE 计算 | 奖励序列 | 优势函数 | ⬜ |
| PPO 更新 | buffer 数据 | loss 收敛 | ⬜ |
| 10k 步训练 | 简单环境 | 平均回报 > 0 | ⬜ |

---

## 五、时间表

| 阶段 | 时间 | 交付物 | 验证指标 |
|------|------|--------|----------|
| Phase 1 | Day 1-2 | TrendScannerConfig + 加载器 | 单元测试通过 |
| Phase 2 | Day 3-4 | AgentBase + ReplayBuffer | 单元测试通过 |
| Phase 3 | Day 5-7 | FuturesTradingEnv | check_env() 通过 |
| Phase 4 | Day 8-10 | AgentPPO + 训练循环 | 10k 步 loss 收敛 |
| Phase 5 | Day 11-12 | WalkForwardRL | IS/OOS 一致性检查 |

---

## 六、进度跟踪

### 2026-06-17
- [x] 创建实施计划文档
- [x] Phase 1: TrendScannerConfig 设计（完成）
  - 创建 `scripts/trend_scanner/trend_scanner_config.py`
  - 创建 `tests/test_trend_scanner_config.py`（31个测试全部通过）
  - 更新 `scripts/trend_scanner/__init__.py` 导出配置模块
- [x] Phase 2: AgentBase + ReplayBuffer（完成）
  - 创建 `scripts/trend_scanner/rl/__init__.py`
  - 创建 `scripts/trend_scanner/rl/base.py`（AgentBase, ReplayBuffer, Evaluator）
  - 创建 `scripts/trend_scanner/rl/futures_env.py`（FuturesTradingEnv, MultiAssetVecEnv）
  - 创建 `tests/test_rl_base.py`（19个测试全部通过）
- [x] Phase 3: PPO 训练器（完成）
  - 创建 `scripts/trend_scanner/rl/networks.py`（ActorPPO, CriticPPO, ActorCriticPPO, CriticEnsemble, StateNormalizer）
  - 创建 `scripts/trend_scanner/rl/agent_ppo.py`（AgentPPO, AgentPPOShared）
  - 创建 `scripts/trend_scanner/rl/trainer.py`（RLTrainer, TrainingLogger, evaluate_agent）
  - 创建 `tests/test_ppo.py`（30个测试全部通过）
