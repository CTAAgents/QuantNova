"""
因子生命周期单元测试

测试因子生命周期状态机的完整功能。
"""

import sys
from pathlib import Path

import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "scripts"))

from trend_scanner.factor_lifecycle import (
    FactorAsset,
    FactorLifecycleManager,
    InvalidTransitionError,
    LifecycleState,
    STATE_NAMES,
    VALID_TRANSITIONS,
)


class TestLifecycleState:
    """测试生命周期状态定义"""

    def test_all_states_exist(self):
        """测试所有8个状态都存在"""
        states = list(LifecycleState)
        assert len(states) == 8

    def test_state_values(self):
        """测试状态值格式"""
        assert LifecycleState.RAW.value == "S0_raw"
        assert LifecycleState.CANDIDATE.value == "S1_candidate"
        assert LifecycleState.DRAFT.value == "S2_draft"
        assert LifecycleState.VERIFIED.value == "S3_verified"
        assert LifecycleState.RELEASED.value == "S4_released"
        assert LifecycleState.DEGRADED.value == "S5_degraded"
        assert LifecycleState.DEPRECATED.value == "S6_deprecated"
        assert LifecycleState.ARCHIVED.value == "S7_archived"

    def test_state_names(self):
        """测试状态中文名称"""
        assert STATE_NAMES[LifecycleState.RAW] == "原始"
        assert STATE_NAMES[LifecycleState.RELEASED] == "已发布"
        assert STATE_NAMES[LifecycleState.ARCHIVED] == "已归档"

    def test_valid_transitions_cover_all_states(self):
        """测试所有状态都有转换规则"""
        for state in LifecycleState:
            assert state in VALID_TRANSITIONS

    def test_archived_is_terminal(self):
        """测试归档状态是终态"""
        assert VALID_TRANSITIONS[LifecycleState.ARCHIVED] == []


class TestValidTransitions:
    """测试有效状态转换"""

    def test_raw_to_candidate(self):
        """S0 → S1: 原始到候选"""
        assert LifecycleState.CANDIDATE in VALID_TRANSITIONS[LifecycleState.RAW]

    def test_candidate_to_draft(self):
        """S1 → S2: 候选到草案"""
        assert LifecycleState.DRAFT in VALID_TRANSITIONS[LifecycleState.CANDIDATE]

    def test_draft_to_verified(self):
        """S2 → S3: 草案到已验证"""
        assert LifecycleState.VERIFIED in VALID_TRANSITIONS[LifecycleState.DRAFT]

    def test_verified_to_released(self):
        """S3 → S4: 已验证到已发布"""
        assert LifecycleState.RELEASED in VALID_TRANSITIONS[LifecycleState.VERIFIED]

    def test_released_to_degraded(self):
        """S4 → S5: 已发布到退化"""
        assert LifecycleState.DEGRADED in VALID_TRANSITIONS[LifecycleState.RELEASED]

    def test_degraded_to_draft(self):
        """S5 → S2: 退化到草案（修复后重新验证）"""
        assert LifecycleState.DRAFT in VALID_TRANSITIONS[LifecycleState.DEGRADED]

    def test_deprecated_to_archived(self):
        """S6 → S7: 已弃用到已归档"""
        assert LifecycleState.ARCHIVED in VALID_TRANSITIONS[LifecycleState.DEPRECATED]

    def test_invalid_raw_to_released(self):
        """S0 → S4: 无效转换"""
        assert LifecycleState.RELEASED not in VALID_TRANSITIONS[LifecycleState.RAW]

    def test_invalid_archived_to_any(self):
        """S7 → ?: 无效转换（终态）"""
        assert len(VALID_TRANSITIONS[LifecycleState.ARCHIVED]) == 0


class TestFactorAsset:
    """测试因子资产"""

    def test_create_factor(self):
        """测试创建因子"""
        factor = FactorAsset(
            id="test_001",
            name="测试因子",
            code="def factor(df): return df['close'].pct_change()",
            description="测试用因子",
        )
        assert factor.id == "test_001"
        assert factor.lifecycle_state == LifecycleState.RAW
        assert factor.version == 1

    def test_factor_default_timestamps(self):
        """测试默认时间戳"""
        factor = FactorAsset(id="test_002", name="测试", code="")
        assert factor.created_at != ""
        assert factor.updated_at != ""

    def test_can_transition_to(self):
        """测试状态转换检查"""
        factor = FactorAsset(id="test_003", name="测试", code="")
        assert factor.can_transition_to(LifecycleState.CANDIDATE) is True
        assert factor.can_transition_to(LifecycleState.RELEASED) is False

    def test_transition_success(self):
        """测试成功状态转换"""
        factor = FactorAsset(id="test_004", name="测试", code="")
        transition = factor.transition(
            LifecycleState.CANDIDATE,
            reason="通过语法检查",
            metrics={"syntax_valid": True},
        )
        assert factor.lifecycle_state == LifecycleState.CANDIDATE
        assert len(factor.lifecycle_history) == 1
        assert transition.from_state == LifecycleState.RAW
        assert transition.to_state == LifecycleState.CANDIDATE

    def test_transition_invalid(self):
        """测试无效状态转换"""
        factor = FactorAsset(id="test_005", name="测试", code="")
        with pytest.raises(InvalidTransitionError):
            factor.transition(LifecycleState.RELEASED, reason="跳过中间状态")

    def test_multiple_transitions(self):
        """测试连续状态转换"""
        factor = FactorAsset(id="test_006", name="测试", code="")

        # S0 → S1
        factor.transition(LifecycleState.CANDIDATE, "通过筛选")
        assert factor.lifecycle_state == LifecycleState.CANDIDATE

        # S1 → S2
        factor.transition(LifecycleState.DRAFT, "代码实现完成")
        assert factor.lifecycle_state == LifecycleState.DRAFT

        # S2 → S3
        factor.transition(LifecycleState.VERIFIED, "Walk-Forward验证通过")
        assert factor.lifecycle_state == LifecycleState.VERIFIED

        # S3 → S4
        factor.transition(LifecycleState.RELEASED, "进入实盘观察")
        assert factor.lifecycle_state == LifecycleState.RELEASED

        assert len(factor.lifecycle_history) == 4

    def test_save_version_snapshot(self):
        """测试保存版本快照"""
        factor = FactorAsset(
            id="test_007",
            name="测试",
            code="def factor(df): return df['close']",
            evaluation={"sharpe": 1.5},
        )
        factor.save_version_snapshot("初始版本")
        assert factor.version == 2
        assert len(factor.versions) == 1
        assert factor.versions[0]["version"] == 1

    def test_check_health_healthy(self):
        """测试健康度检查 - 健康"""
        factor = FactorAsset(
            id="test_008",
            name="测试",
            code="",
            evaluation={"sharpe": 1.5, "max_drawdown": 0.1, "ic": 0.05},
        )
        report = factor.check_health()
        assert report["is_healthy"] is True
        assert len(report["issues"]) == 0

    def test_check_health_unhealthy(self):
        """测试健康度检查 - 不健康"""
        factor = FactorAsset(
            id="test_009",
            name="测试",
            code="",
            evaluation={"sharpe": 0.3, "max_drawdown": 0.2, "ic": 0.01},
        )
        report = factor.check_health()
        assert report["is_healthy"] is False
        assert len(report["issues"]) >= 2  # 夏普低 + 回撤高

    def test_to_dict(self):
        """测试转换为字典"""
        factor = FactorAsset(id="test_010", name="测试", code="return 0")
        data = factor.to_dict()
        assert data["id"] == "test_010"
        assert data["lifecycle_state"] == "S0_raw"
        assert "lifecycle_history" in data

    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "id": "test_011",
            "name": "测试",
            "code": "return 0",
            "lifecycle_state": "S2_draft",
            "lifecycle_history": [
                {
                    "from_state": "S0_raw",
                    "to_state": "S1_candidate",
                    "timestamp": "2026-01-01T00:00:00",
                    "reason": "测试",
                }
            ],
        }
        factor = FactorAsset.from_dict(data)
        assert factor.id == "test_011"
        assert factor.lifecycle_state == LifecycleState.DRAFT
        assert len(factor.lifecycle_history) == 1


class TestFactorLifecycleManager:
    """测试生命周期管理器"""

    def setup_method(self):
        self.manager = FactorLifecycleManager()

    def test_register_factor(self):
        """测试注册因子"""
        factor = FactorAsset(id="mgr_001", name="测试", code="")
        self.manager.register_factor(factor)
        assert self.manager.get_factor("mgr_001") is not None

    def test_list_factors_by_state(self):
        """测试按状态列出因子"""
        f1 = FactorAsset(id="mgr_002", name="f1", code="")
        f2 = FactorAsset(id="mgr_003", name="f2", code="")
        f2.lifecycle_state = LifecycleState.RELEASED

        self.manager.register_factor(f1)
        self.manager.register_factor(f2)

        raw_factors = self.manager.list_factors_by_state(LifecycleState.RAW)
        released_factors = self.manager.list_factors_by_state(LifecycleState.RELEASED)

        assert len(raw_factors) == 1
        assert len(released_factors) == 1

    def test_advance_factor(self):
        """测试推进因子状态"""
        factor = FactorAsset(id="mgr_004", name="测试", code="")
        self.manager.register_factor(factor)

        transition = self.manager.advance_factor(
            "mgr_004",
            LifecycleState.CANDIDATE,
            reason="通过初步筛选",
        )
        assert factor.lifecycle_state == LifecycleState.CANDIDATE

    def test_advance_nonexistent_factor(self):
        """测试推进不存在的因子"""
        with pytest.raises(ValueError):
            self.manager.advance_factor(
                "nonexistent",
                LifecycleState.CANDIDATE,
                reason="测试",
            )

    def test_check_all_health(self):
        """测试检查所有因子健康度"""
        f1 = FactorAsset(
            id="mgr_005",
            name="健康因子",
            code="",
            lifecycle_state=LifecycleState.RELEASED,
            evaluation={"sharpe": 1.5, "max_drawdown": 0.1, "ic": 0.05},
        )
        f2 = FactorAsset(
            id="mgr_006",
            name="不健康因子",
            code="",
            lifecycle_state=LifecycleState.RELEASED,
            evaluation={"sharpe": 0.3, "max_drawdown": 0.2, "ic": 0.01},
        )

        self.manager.register_factor(f1)
        self.manager.register_factor(f2)

        results = self.manager.check_all_health()
        assert len(results) == 2
        assert results["mgr_005"]["is_healthy"] is True
        assert results["mgr_006"]["is_healthy"] is False

    def test_generate_maintenance_proposals(self):
        """测试生成维护提案"""
        f1 = FactorAsset(
            id="mgr_007",
            name="退化因子",
            code="",
            lifecycle_state=LifecycleState.RELEASED,
            evaluation={"sharpe": 0.3, "max_drawdown": 0.2, "ic": 0.01},
        )
        self.manager.register_factor(f1)

        proposals = self.manager.generate_maintenance_proposals()
        assert len(proposals) == 1
        assert proposals[0]["proposed_action"] == "degrade"

    def test_get_statistics(self):
        """测试获取统计信息"""
        f1 = FactorAsset(id="mgr_008", name="f1", code="")
        f2 = FactorAsset(id="mgr_009", name="f2", code="")
        f2.lifecycle_state = LifecycleState.RELEASED

        self.manager.register_factor(f1)
        self.manager.register_factor(f2)

        stats = self.manager.get_statistics()
        assert stats["total_factors"] == 2
        assert stats["active_factors"] == 1


class TestFullLifecycle:
    """测试完整生命周期流程"""

    def test_complete_lifecycle(self):
        """测试因子从创建到归档的完整生命周期"""
        manager = FactorLifecycleManager()

        # 创建因子
        factor = FactorAsset(
            id="lifecycle_001",
            name="完整生命周期测试因子",
            code="def factor(df): return df['close'].pct_change(5)",
            description="测试完整生命周期",
            category="momentum",
        )
        manager.register_factor(factor)

        # S0 → S1: 原始到候选
        manager.advance_factor(
            "lifecycle_001",
            LifecycleState.CANDIDATE,
            reason="通过语法检查和初步筛选",
            metrics={"syntax_valid": True, "complexity": "low"},
        )
        assert factor.lifecycle_state == LifecycleState.CANDIDATE

        # S1 → S2: 候选到草案
        manager.advance_factor(
            "lifecycle_001",
            LifecycleState.DRAFT,
            reason="代码实现完成，可运行",
            metrics={"runnable": True},
        )
        assert factor.lifecycle_state == LifecycleState.DRAFT
        factor.save_version_snapshot("v1.0 初始实现")

        # S2 → S3: 草案到已验证
        manager.advance_factor(
            "lifecycle_001",
            LifecycleState.VERIFIED,
            reason="Walk-Forward验证通过",
            metrics={"walk_forward_sharpe": 1.2, "max_drawdown": 0.1},
        )
        assert factor.lifecycle_state == LifecycleState.VERIFIED

        # S3 → S4: 已验证到已发布
        manager.advance_factor(
            "lifecycle_001",
            LifecycleState.RELEASED,
            reason="进入实盘观察期",
            metrics={"live_start_date": "2026-06-01"},
        )
        assert factor.lifecycle_state == LifecycleState.RELEASED

        # 检查健康度
        health = factor.check_health()
        # 由于没有评估指标，健康度检查会标记为不健康
        assert health["is_healthy"] is False

        # 添加评估指标后重新检查
        factor.evaluation = {
            "sharpe": 1.5,
            "max_drawdown": 0.1,
            "ic": 0.05,
        }
        health = factor.check_health()
        assert health["is_healthy"] is True

        # S4 → S5: 已发布到退化（假设市场变化导致退化）
        manager.advance_factor(
            "lifecycle_001",
            LifecycleState.DEGRADED,
            reason="滚动夏普比率降至0.4",
            metrics={"rolling_sharpe": 0.4},
        )
        assert factor.lifecycle_state == LifecycleState.DEGRADED

        # S5 → S2: 退化到草案（修复后重新验证）
        manager.advance_factor(
            "lifecycle_001",
            LifecycleState.DRAFT,
            reason="参数调整后重新验证",
            metrics={"param_adjusted": True},
        )
        assert factor.lifecycle_state == LifecycleState.DRAFT
        factor.save_version_snapshot("v1.1 参数调整")

        # 验证历史记录
        assert len(factor.lifecycle_history) == 6
        assert len(factor.versions) == 2

        # 获取统计
        stats = manager.get_statistics()
        assert stats["total_factors"] == 1
