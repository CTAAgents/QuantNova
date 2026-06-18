"""
Prompt路由器

根据市场类型选择对应的Prompt模板
"""

import logging
from typing import Dict

from .futures_prompt import FUTURES_SYSTEM_PROMPT
from .securities_prompt import SECURITIES_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class PromptRouter:
    """
    Prompt路由器

    根据市场类型选择对应的Prompt模板
    """

    def __init__(self):
        """初始化Prompt路由器"""
        self.prompts: Dict[str, str] = {
            "futures": FUTURES_SYSTEM_PROMPT,
            "securities": SECURITIES_SYSTEM_PROMPT,
        }

    def get_prompt(self, market_type: str) -> str:
        """
        获取对应市场的Prompt

        Args:
            market_type: 市场类型（futures/securities）

        Returns:
            str: Prompt模板
        """
        if market_type in self.prompts:
            return self.prompts[market_type]
        else:
            logger.warning(f"未知市场类型: {market_type}，使用默认Prompt")
            return FUTURES_SYSTEM_PROMPT

    def register_prompt(self, market_type: str, prompt: str):
        """
        注册新的Prompt模板

        Args:
            market_type: 市场类型
            prompt: Prompt模板
        """
        self.prompts[market_type] = prompt
        logger.info(f"已注册Prompt模板: {market_type}")

    def list_market_types(self) -> list:
        """
        列出所有支持的市场类型

        Returns:
            list: 市场类型列表
        """
        return list(self.prompts.keys())
