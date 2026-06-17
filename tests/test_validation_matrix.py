"""
ValidationMatrix 单元测试

覆盖:
- 7 种改动类型的验证要求查询
- validate_route 红线检查
- to_reasoner_context 文本生成
- list_all_types 完整性
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from scripts.trend_scanner.validation_matrix import (
    ValidationMatrix, ValidationRequirement, VALIDATION_MATRIX
)


class TestValidationRequirement:
    """ValidationRequirement 数据类测试"""

    def test_creation(self):
        req = ValidationRequirement(
            minimum="测试标准",
            checks=["检查1"],
            red_flags=["红线1"],
            validator="test_validator",
            description="测试描述",
        )
        assert req.minimum == "测试标准"
        assert req.checks == ["检查1"]
        assert req.red_flags == ["红线1"]
        assert req.validator == "test_validator"
        assert req.description == "测试描述"

    def test_defaults(self):
        req = ValidationRequirement(minimum="标准")
        assert req.checks == []
        assert req.red_flags == []
        assert req.validator == ""
        assert req.description == ""


class TestValidationMatrix:
    """ValidationMatrix 核心功能测试"""

    def setup_method(self):
        self.vm = ValidationMatrix()

    def test_all_seven_types_exist(self):
        """验证矩阵包含全部 7 种改动类型"""
        expected = {
            "adjust_position", "add_indicator", "modify_threshold",
            "new_entry", "exit", "strategy_logic", "risk_parameter"
        }
        assert set(self.vm.list_all_types()) == expected

    def test_get_requirement_adjust_position(self):
        req = self.vm.get_requirement("adjust_position")
        assert req is not None
        assert "回测" in req.minimum
        assert req.validator == "walk_forward_validator"
        assert len(req.checks) >= 3
        assert len(req.red_flags) >= 1

    def test_get_requirement_add_indicator(self):
        req = self.vm.get_requirement("add_indicator")
        assert req is not None
        assert "单元测试" in req.minimum
        assert req.validator == "factor_evaluator"

    def test_get_requirement_modify_threshold(self):
        req = self.vm.get_requirement("modify_threshold")
        assert req is not None
        assert "回测" in req.minimum
        assert req.validator == "walk_forward_validator"

    def test_get_requirement_new_entry(self):
        req = self.vm.get_requirement("new_entry")
        assert req is not None
        assert "Walk-Forward" in req.minimum

    def test_get_requirement_exit(self):
        req = self.vm.get_requirement("exit")
        assert req is not None
        assert req.validator == "walk_forward_validator"

    def test_get_requirement_strategy_logic(self):
        req = self.vm.get_requirement("strategy_logic")
        assert req is not None
        assert "蒙特卡洛" in req.minimum
        assert req.validator == "overfitting_auditor"

    def test_get_requirement_risk_parameter(self):
        req = self.vm.get_requirement("risk_parameter")
        assert req is not None
        assert "风险" in req.minimum

    def test_get_requirement_unknown(self):
        """未知改动类型返回 None"""
        assert self.vm.get_requirement("unknown_type") is None

    def test_get_minimum_standard(self):
        standard = self.vm.get_minimum_standard("adjust_position")
        assert "回测" in standard

    def test_get_minimum_standard_unknown(self):
        assert self.vm.get_minimum_standard("unknown") == "未定义"

    def test_list_all_types_count(self):
        assert len(self.vm.list_all_types()) == 7


class TestValidateRoute:
    """validate_route 红线检查测试"""

    def setup_method(self):
        self.vm = ValidationMatrix()

    def test_pass_no_red_flags(self):
        """无红线触发时通过"""
        result = self.vm.validate_route("adjust_position", {
            "walk_forward_validator": {
                "warnings": [],
                "known_issues": [],
            }
        })
        assert result["passed"] is True
        assert result["red_flags_triggered"] == []

    def test_fail_red_flag_triggered(self):
        """红线触发时失败"""
        result = self.vm.validate_route("adjust_position", {
            "walk_forward_validator": {
                "warnings": [],
                "known_issues": ["PnL 改善伴随换手率同步恶化且未解释"],
            }
        })
        assert result["passed"] is False
        assert len(result["red_flags_triggered"]) >= 1

    def test_unknown_change_type(self):
        result = self.vm.validate_route("unknown", {})
        assert result["passed"] is False
        assert "未知改动类型" in result["warnings"][0]

    def test_add_indicator_lookahead_bias(self):
        """add_indicator 前视偏差红线"""
        result = self.vm.validate_route("add_indicator", {
            "factor_evaluator": {
                "known_issues": ["存在前视偏差（使用了未来数据）"],
            }
        })
        assert result["passed"] is False

    def test_strategy_logic_narrow_parameter(self):
        """strategy_logic 参数稳定域过窄红线"""
        result = self.vm.validate_route("strategy_logic", {
            "overfitting_auditor": {
                "known_issues": ["参数稳定域过窄（10% 微调即失效）"],
            }
        })
        assert result["passed"] is False


class TestToReasonerContext:
    """to_reasoner_context 文本生成测试"""

    def setup_method(self):
        self.vm = ValidationMatrix()

    def test_known_type(self):
        ctx = self.vm.to_reasoner_context("adjust_position")
        assert "adjust_position" in ctx
        assert "最低验证标准" in ctx
        assert "检查要点" in ctx
        assert "红线" in ctx

    def test_unknown_type(self):
        ctx = self.vm.to_reasoner_context("unknown")
        assert "无预定义验证标准" in ctx

    def test_all_types_produce_context(self):
        """所有改动类型都能生成上下文"""
        for change_type in self.vm.list_all_types():
            ctx = self.vm.to_reasoner_context(change_type)
            assert len(ctx) > 50
