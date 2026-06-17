"""
Phase 5 & 6 测试：多因子组合模型 + 失败经验库
"""

import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd
import pytest


sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))


def generate_mock_data(n_symbols: int = 20, days: int = 120) -> dict:
    """生成模拟数据"""
    symbols = [f"TEST{i:02d}" for i in range(n_symbols)]
    dates = pd.date_range(end=pd.Timestamp("2026-06-15"), periods=days, freq="B")
    data = {}
    for i, sym in enumerate(symbols):
        np.random.seed(42 + i)
        prices = 100 * np.exp(np.cumsum(np.random.normal(0.0005, 0.02, days)))
        data[sym] = pd.DataFrame(
            {
                "date": dates,
                "open": prices * (1 + np.random.uniform(-0.01, 0.01, days)),
                "high": prices * 1.01,
                "low": prices * 0.99,
                "close": prices,
                "volume": np.random.randint(10000, 100000, days).astype(float),
                "open_interest": np.random.randint(50000, 500000, days).astype(float),
            }
        )
    return data


def generate_mock_factor_data(n_symbols: int = 20, days: int = 100, n_factors: int = 3) -> dict:
    """生成模拟因子值数据"""
    dates = pd.date_range(end=pd.Timestamp("2026-06-15"), periods=days, freq="B")
    symbols = [f"TEST{i:02d}" for i in range(n_symbols)]
    factor_data = {}

    for f_idx in range(n_factors):
        np.random.seed(100 + f_idx)
        values = np.random.randn(days, n_symbols) * 0.1
        factor_data[f"factor_{f_idx}"] = pd.DataFrame(values, index=dates, columns=symbols)

    return factor_data


# ============================================================
# Phase 5: MultiFactorModel 测试
# ============================================================


class TestMultiFactorModel:
    """MultiFactorModel 测试"""

    def setup_method(self):
        from trend_scanner.multi_factor_model import MultiFactorModel

        self.model = MultiFactorModel(model_type="lightgbm")
        self.factor_data = generate_mock_factor_data()

        # 生成收益率
        dates = list(self.factor_data.values())[0].index
        symbols = list(self.factor_data.values())[0].columns
        np.random.seed(42)
        returns = pd.DataFrame(np.random.randn(len(dates), len(symbols)) * 0.02, index=dates, columns=symbols)
        self.returns = returns

    def test_train_lightgbm(self):
        """测试 LightGBM 模型训练"""
        result = self.model.train(self.factor_data, self.returns)

        assert result.model_name == "lightgbm"
        assert result.n_features == 3
        assert result.n_train_days > 0
        assert result.n_oos_days > 0

    def test_train_ridge(self):
        """测试 Ridge 模型训练"""
        from trend_scanner.multi_factor_model import MultiFactorModel

        model = MultiFactorModel(model_type="ridge")
        result = model.train(self.factor_data, self.returns)

        assert result.model_name == "ridge"

    def test_train_equal_weight(self):
        """测试等权模型训练"""
        from trend_scanner.multi_factor_model import MultiFactorModel

        model = MultiFactorModel(model_type="equal_weight")
        result = model.train(self.factor_data, self.returns)

        assert result.model_name == "equal_weight"

    def test_feature_importance(self):
        """测试特征重要性"""
        result = self.model.train(self.factor_data, self.returns)

        assert len(result.feature_importance) == 3
        total = sum(result.feature_importance.values())
        assert abs(total - 1.0) < 0.01  # 重要性总和应约等于 1

    def test_predict(self):
        """测试预测"""
        self.model.train(self.factor_data, self.returns)
        signal = self.model.predict(self.factor_data)

        assert not signal.empty
        assert signal.shape[1] == 20  # 20 个品种

    def test_result_serialization(self):
        """测试结果序列化"""
        result = self.model.train(self.factor_data, self.returns)
        d = result.to_dict()

        assert "model_name" in d
        assert "feature_importance" in d
        assert "oos_icir" in d

    def test_insufficient_data(self):
        """测试数据不足"""
        small_data = {k: v.head(5) for k, v in self.factor_data.items()}
        small_returns = self.returns.head(5)

        result = self.model.train(small_data, small_returns)
        assert result.n_features == 0


# ============================================================
# Phase 6: FactorExperienceDB 测试
# ============================================================


class TestFactorExperienceDB:
    """FactorExperienceDB 测试"""

    def setup_method(self):
        from trend_scanner.factor_experience_db import FactorExperienceDB

        self.db = FactorExperienceDB(db_path="data/test_factor_experience.json")

    def teardown_method(self):
        if os.path.exists("data/test_factor_experience.json"):
            os.remove("data/test_factor_experience.json")

    def test_record_trajectory(self):
        """测试记录演化轨迹"""
        trajectory = [
            {
                "round": 1,
                "factor_name": "momentum_20d",
                "logic": "20日动量",
                "params": {"window": 20},
                "icir": 0.24,
                "t_stat": 1.8,
                "decision": "eliminate",
                "reasons": ["ICIR=0.24 < 0.5"],
            },
        ]
        self.db.record_trajectory("momentum_20d", trajectory)

        assert len(self.db.experiences) == 1
        assert self.db.experiences[0].factor_id == "momentum_20d"

    def test_get_failure_lessons(self):
        """测试获取失败教训"""
        trajectory = [
            {
                "round": 1,
                "factor_name": "test_factor",
                "logic": "test",
                "params": {},
                "icir": 0.1,
                "t_stat": 0.5,
                "decision": "eliminate",
                "reasons": ["ICIR=0.1 < 0.5"],
            },
        ]
        self.db.record_trajectory("test_factor", trajectory)

        lessons = self.db.get_failure_lessons()
        assert len(lessons) > 0

    def test_generate_feedback_prompt(self):
        """测试生成反馈提示词"""
        trajectory = [
            {
                "round": 1,
                "factor_name": "bad_factor",
                "logic": "bad logic",
                "params": {},
                "icir": 0.1,
                "t_stat": 0.5,
                "decision": "eliminate",
                "reasons": ["ICIR too low"],
            },
        ]
        self.db.record_trajectory("bad_factor", trajectory)

        prompt = self.db.generate_feedback_prompt()
        assert "失败" in prompt or "教训" in prompt or "避免" in prompt

    def test_get_summary(self):
        """测试获取摘要"""
        trajectory = [
            {
                "round": 1,
                "factor_name": "f1",
                "logic": "l1",
                "params": {},
                "icir": 0.1,
                "t_stat": 0.5,
                "decision": "eliminate",
                "reasons": ["r1"],
            },
        ]
        self.db.record_trajectory("f1", trajectory, category="momentum")

        summary = self.db.get_summary()
        assert summary["total_experiences"] == 1
        assert summary["categories"]["momentum"] == 1

    def test_persistence(self):
        """测试持久化"""
        from trend_scanner.factor_experience_db import FactorExperienceDB

        trajectory = [
            {
                "round": 1,
                "factor_name": "f1",
                "logic": "l1",
                "params": {},
                "icir": 0.1,
                "t_stat": 0.5,
                "decision": "eliminate",
                "reasons": ["r1"],
            },
        ]
        self.db.record_trajectory("f1", trajectory)

        # 重新加载
        db2 = FactorExperienceDB(db_path="data/test_factor_experience.json")
        assert len(db2.experiences) == 1
        assert db2.experiences[0].factor_id == "f1"

    def test_record_from_evolution_result(self):
        """测试从进化结果记录经验"""
        from trend_scanner.factor_evolution_engine import EvolutionResult, EvolutionRound

        result = EvolutionResult(
            total_rounds=1,
            total_candidates=2,
            promoted_factors=[],
            rounds=[
                EvolutionRound(
                    round_num=1,
                    candidates=[{"name": "f1", "source": "test"}],
                    evaluations={},
                    decisions=[
                        {"factor_name": "f1", "decision": "eliminate", "score": 0.1, "reasons": ["ICIR=0.1 < 0.5"]},
                    ],
                    promoted=[],
                    eliminated=["f1"],
                    timestamp=datetime.now().isoformat(),
                ),
            ],
            duration_seconds=1.0,
            status="max_rounds",
        )

        self.db.record_from_evolution_result(result)
        assert len(self.db.experiences) > 0

    def test_clear(self):
        """测试清空"""
        trajectory = [
            {
                "round": 1,
                "factor_name": "f1",
                "logic": "l1",
                "params": {},
                "icir": 0.1,
                "t_stat": 0.5,
                "decision": "eliminate",
                "reasons": ["r1"],
            },
        ]
        self.db.record_trajectory("f1", trajectory)
        self.db.clear()
        assert len(self.db.experiences) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
