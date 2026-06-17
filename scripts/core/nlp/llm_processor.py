"""
LLM 处理器

使用大语言模型理解自然语言：
- 意图理解
- 任务规划
- 命令生成
- 上下文管理
"""

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LLMProcessor:
    """LLM 处理器"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        """
        初始化 LLM 处理器

        Args:
            api_key: API 密钥
            model: 模型名称
        """
        self.api_key = api_key
        self.model = model
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return """你是一个期货交易系统的智能助手。你的职责是：

1. 理解用户的自然语言指令
2. 将指令转换为系统可执行的命令
3. 生成清晰的执行计划

可用的系统命令：
- scan: 扫描市场信号（分析全部品种，给出操作建议）
- health_check: 检查持仓健康度
- signals: 查看当前信号
- status: 查看系统状态
- evolve: 执行因子进化
- sync: 同步数据
- arbitrage: 执行套利分析

请根据用户输入，返回 JSON 格式的响应：
{
    "action": "命令名称",
    "parameters": {},
    "explanation": "执行说明"
}

如果没有匹配的命令，返回：
{
    "action": "unknown",
    "explanation": "抱歉，我无法理解这个指令"
}"""

    def process(self, user_input: str) -> Dict[str, Any]:
        """
        处理用户输入

        Args:
            user_input: 用户输入

        Returns:
            处理结果
        """
        try:
            # 构建提示词
            user_prompt = f"用户指令：{user_input}"

            # 调用 LLM（这里使用简化的本地实现）
            response = self._call_llm(user_prompt)

            # 解析响应
            return self._parse_response(response)

        except Exception as e:
            logger.error(f"LLM 处理失败: {e}")
            return {
                "action": "unknown",
                "explanation": f"处理失败: {e}",
            }

    def _call_llm(self, prompt: str) -> str:
        """
        调用 LLM

        这里使用简化的本地实现，实际应该调用真正的 LLM API
        """
        # 简化的本地实现：基于关键词匹配
        prompt_lower = prompt.lower()

        # 分析用户意图
        if any(word in prompt_lower for word in ["扫描", "分析", "全部", "品种", "机会", "做", "建议"]):
            return json.dumps({
                "action": "scan",
                "explanation": "执行市场扫描，分析全部品种"
            })
        elif any(word in prompt_lower for word in ["持仓", "健康", "检查", "评估"]):
            return json.dumps({
                "action": "health_check",
                "explanation": "检查持仓健康度"
            })
        elif any(word in prompt_lower for word in ["信号", "当前", "查看"]):
            return json.dumps({
                "action": "signals",
                "explanation": "查看当前信号"
            })
        elif any(word in prompt_lower for word in ["状态", "运行", "系统"]):
            return json.dumps({
                "action": "status",
                "explanation": "查看系统状态"
            })
        elif any(word in prompt_lower for word in ["进化", "因子"]):
            return json.dumps({
                "action": "evolve",
                "explanation": "执行因子进化"
            })
        elif any(word in prompt_lower for word in ["同步", "数据"]):
            return json.dumps({
                "action": "sync",
                "explanation": "同步数据"
            })
        elif any(word in prompt_lower for word in ["套利", "价差"]):
            return json.dumps({
                "action": "arbitrage",
                "explanation": "执行套利分析"
            })
        elif any(word in prompt_lower for word in ["帮助", "怎么用", "说明"]):
            return json.dumps({
                "action": "help",
                "explanation": "显示帮助信息"
            })
        elif any(word in prompt_lower for word in ["黑色", "螺纹", "铁矿", "焦煤", "焦炭"]):
            return json.dumps({
                "action": "scan",
                "explanation": "扫描黑色系品种"
            })
        else:
            return json.dumps({
                "action": "scan",
                "explanation": "执行市场扫描"
            })

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析 LLM 响应"""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {
                "action": "unknown",
                "explanation": "响应解析失败",
            }


class EnhancedLLMProcessor(LLMProcessor):
    """增强版 LLM 处理器（支持真正的 LLM API）"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        super().__init__(api_key, model)

    def _call_llm(self, prompt: str) -> str:
        """
        调用真正的 LLM API

        这里提供 OpenAI API 的实现示例
        """
        if not self.api_key:
            # 如果没有 API 密钥，使用本地实现
            return super()._call_llm(prompt)

        try:
            import openai

            client = openai.OpenAI(api_key=self.api_key)

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=200,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI API 调用失败: {e}")
            return super()._call_llm(prompt)
