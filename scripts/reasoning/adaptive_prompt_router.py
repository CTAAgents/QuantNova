"""
自适应Prompt路由器

基于 V3.0 方案第二章的三级自适应Prompt模板：
- 极简模板：纯指标解读、静态历史复盘
- 标准模板：常规品种日线行情研判
- 深度模板：重仓研判、跨品种对冲、宏观驱动分析

核心功能：
1. 场景识别
2. 模板路由
3. 动态Few-Shot样本选择
4. 模板组装
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class PromptTemplateType(Enum):
    """Prompt模板类型"""
    MINIMAL = "minimal"  # 极简模板
    STANDARD = "standard"  # 标准模板
    DEEP = "deep"  # 深度模板


@dataclass
class PromptTemplate:
    """Prompt模板"""
    template_type: PromptTemplateType
    name: str
    description: str
    system_prompt: str
    reasoning_steps: int
    constraints: List[str]
    few_shot_count: int = 3


class AdaptivePromptRouter:
    """
    自适应Prompt路由器
    
    基于 V3.0 方案的三级Prompt模板
    """
    
    def __init__(self):
        """初始化自适应Prompt路由器"""
        self.templates = self._init_templates()
    
    def _init_templates(self) -> Dict[PromptTemplateType, PromptTemplate]:
        """初始化模板库"""
        return {
            PromptTemplateType.MINIMAL: PromptTemplate(
                template_type=PromptTemplateType.MINIMAL,
                name="极简模板",
                description="纯指标解读、静态历史复盘",
                system_prompt=self._get_minimal_system_prompt(),
                reasoning_steps=3,
                constraints=[
                    "仅使用提供的技术指标数据",
                    "不进行主观推演",
                    "直接输出指标解读结论",
                ],
                few_shot_count=2,
            ),
            PromptTemplateType.STANDARD: PromptTemplate(
                template_type=PromptTemplateType.STANDARD,
                name="标准模板",
                description="常规品种日线行情研判",
                system_prompt=self._get_standard_system_prompt(),
                reasoning_steps=7,
                constraints=[
                    "必须包含多空双方逻辑",
                    "必须附带概率区间",
                    "必须标注数据可信度",
                    "禁止100%确定性结论",
                ],
                few_shot_count=3,
            ),
            PromptTemplateType.DEEP: PromptTemplate(
                template_type=PromptTemplateType.DEEP,
                name="深度模板",
                description="重仓研判、跨品种对冲、宏观驱动分析",
                system_prompt=self._get_deep_system_prompt(),
                reasoning_steps=10,
                constraints=[
                    "必须包含完整风险评估",
                    "必须进行情景推演（基准/利多/利空）",
                    "必须评估流动性风险",
                    "必须进行跨品种相关性分析",
                    "必须包含宏观因子分析",
                    "必须附带止损建议",
                ],
                few_shot_count=5,
            ),
        }
    
    def route(self, 
              query: str, 
              context: Optional[dict] = None) -> PromptTemplate:
        """
        根据查询内容路由到合适的模板
        
        Args:
            query: 用户查询
            context: 上下文信息（可选）
            
        Returns:
            PromptTemplate: 选中的模板
        """
        # 识别场景
        scenario = self._identify_scenario(query, context)
        
        # 路由到模板
        if scenario == "minimal":
            return self.templates[PromptTemplateType.MINIMAL]
        elif scenario == "deep":
            return self.templates[PromptTemplateType.DEEP]
        else:
            return self.templates[PromptTemplateType.STANDARD]
    
    def _identify_scenario(self, query: str, context: Optional[dict] = None) -> str:
        """识别查询场景"""
        query_lower = query.lower()
        
        # 深度模板关键词
        deep_keywords = [
            "重仓", "对冲", "套利", "跨品种", "宏观", "风险评估",
            "情景推演", "止损", "仓位", "组合", "极端",
        ]
        
        # 极简模板关键词
        minimal_keywords = [
            "指标", "解读", "复盘", "回顾", "历史", "数据",
        ]
        
        # 检查深度模板
        if any(keyword in query_lower for keyword in deep_keywords):
            return "deep"
        
        # 检查极简模板
        if any(keyword in query_lower for keyword in minimal_keywords):
            return "minimal"
        
        # 默认标准模板
        return "standard"
    
    def assemble_prompt(self, 
                       template: PromptTemplate,
                       query: str,
                       data_context: str,
                       few_shot_samples: Optional[List[str]] = None) -> str:
        """
        组装完整Prompt
        
        Args:
            template: 选中的模板
            query: 用户查询
            data_context: 数据上下文
            few_shot_samples: Few-Shot样本
            
        Returns:
            str: 完整Prompt
        """
        parts = []
        
        # 系统提示
        parts.append(f"## 系统角色\n{template.system_prompt}")
        
        # 约束条件
        parts.append("\n## 约束条件")
        for i, constraint in enumerate(template.constraints, 1):
            parts.append(f"{i}. {constraint}")
        
        # Few-Shot样本
        if few_shot_samples:
            parts.append("\n## 参考示例")
            for i, sample in enumerate(few_shot_samples[:template.few_shot_count], 1):
                parts.append(f"### 示例{i}\n{sample}")
        
        # 数据上下文
        parts.append(f"\n## 数据上下文\n{data_context}")
        
        # 用户查询
        parts.append(f"\n## 分析要求\n{query}")
        
        # 推理步骤提示
        parts.append(f"\n## 推理要求\n请按照{template.reasoning_steps}个步骤进行分步推理，输出完整分析报告。")
        
        return "\n".join(parts)
    
    def _get_minimal_system_prompt(self) -> str:
        return """你是一个专业的CTA量化分析师。
请基于提供的技术指标数据，直接给出简洁的指标解读。
不需要主观推演，仅做客观数据分析。"""
    
    def _get_standard_system_prompt(self) -> str:
        return """你是一个有十年经验的CTA量化分析师。
请基于以下四维分析框架进行研判：
1. 趋势分析（技术面）
2. 基差与价差结构
3. 库存周期（基本面）
4. 宏观流动性

要求：
- 多空双方逻辑对称
- 所有预判附带概率区间
- 标注数据可信度等级
- 禁止100%确定性结论"""
    
    def _get_deep_system_prompt(self) -> str:
        return """你是一个资深CTA量化分析师，擅长重仓研判和跨品种对冲分析。
请进行深度、全面、多维度的分析：

分析框架：
1. 趋势与动量分析
2. 基差与期限结构
3. 库存周期与供需平衡
4. 宏观因子传导
5. 跨品种相关性
6. 流动性风险评估
7. 情景推演（基准/利多/利空）
8. 风险控制建议

必须包含：
- 完整的多空逻辑
- 三种情景的详细推演
- 止损位和仓位建议
- 相关性风险提示"""
    
    def get_template_info(self) -> str:
        """获取模板信息"""
        lines = [
            "=== 自适应Prompt模板信息 ===",
            "",
        ]
        
        for template_type, template in self.templates.items():
            lines.append(f"## {template.name}")
            lines.append(f"类型: {template_type.value}")
            lines.append(f"描述: {template.description}")
            lines.append(f"推理步骤: {template.reasoning_steps}")
            lines.append(f"约束条件: {len(template.constraints)}条")
            lines.append(f"Few-Shot样本数: {template.few_shot_count}")
            lines.append("")
        
        return "\n".join(lines)
