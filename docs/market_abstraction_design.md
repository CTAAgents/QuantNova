# 市场抽象层设计文档

> 版本：v1.0 | 创建日期：2026-06-18
> 关联：dual_subsystem_implementation_plan.md Phase 1

---

## 一、设计目标

创建市场抽象层，为期货和证券子系统提供统一的数据接口和风险管理接口。

---

## 二、核心接口设计

### 2.1 MarketProvider 抽象基类

```python
class MarketProvider(ABC):
    """市场数据提供者抽象基类"""
    
    @abstractmethod
    def _get_market_type(self) -> MarketType:
        """获取市场类型"""
        pass
    
    @abstractmethod
    def get_kline(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        """获取K线数据"""
        pass
    
    @abstractmethod
    def get_realtime_quote(self, symbol: str) -> Dict[str, Any]:
        """获取实时行情"""
        pass
    
    @abstractmethod
    def get_symbols(self) -> List[str]:
        """获取可用品种列表"""
        pass
    
    @abstractmethod
    def get_fundamental(self, symbol: str) -> Dict[str, Any]:
        """获取基本面数据"""
        pass
    
    def validate_symbol(self, symbol: str) -> bool:
        """验证品种代码是否有效"""
        pass
```

### 2.2 BaseRiskManager 抽象基类

```python
class BaseRiskManager(ABC):
    """风险管理器抽象基类"""
    
    @abstractmethod
    def calculate_position_size(self, signal: float, capital: float, current_price: float) -> float:
        """计算仓位大小"""
        pass
    
    @abstractmethod
    def calculate_stop_loss(self, entry_price: float, signal: float) -> float:
        """计算止损价格"""
        pass
    
    @abstractmethod
    def calculate_take_profit(self, entry_price: float, signal: float) -> float:
        """计算止盈价格"""
        pass
    
    @abstractmethod
    def check_stop_loss(self, position: Dict[str, Any], current_price: float) -> bool:
        """检查是否触发止损"""
        pass
    
    @abstractmethod
    def check_take_profit(self, position: Dict[str, Any], current_price: float) -> bool:
        """检查是否触发止盈"""
        pass
    
    @abstractmethod
    def get_risk_metrics(self, position: Dict[str, Any], current_price: float) -> RiskMetrics:
        """获取风险指标"""
        pass
    
    def validate_trade(self, signal: float, capital: float, current_price: float) -> tuple[bool, str]:
        """验证交易是否合法"""
        pass
```

### 2.3 数据模型

```python
class MarketType(Enum):
    """市场类型"""
    FUTURES = "futures"
    SECURITIES = "securities"

@dataclass
class RiskMetrics:
    """风险指标"""
    position_size: float
    stop_loss_price: float
    take_profit_price: float
    risk_reward_ratio: float
    max_drawdown: float
    risk_level: RiskLevel
    warnings: List[str]

class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
```

---

## 三、设计约束

1. **抽象基类不能被直接实例化**
2. **所有公共方法必须有类型提示和文档字符串**
3. **使用 Google 风格文档字符串**
4. **错误处理要具体，不使用裸 except**

---

## 四、测试要求

详见 `tests/test_market_abstraction.py`

---

*本文档由 WorkBuddy 于 2026-06-18 创建*
