"""
推理系统适配测试

测试期货和证券的Prompt模板
"""

import sys
from pathlib import Path

import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "scripts"))


class TestFuturesPrompt:
    """期货Prompt模板测试"""
    
    def test_import(self):
        """测试导入"""
        from reasoning.futures_prompt import FUTURES_SYSTEM_PROMPT
        assert FUTURES_SYSTEM_PROMPT is not None
    
    def test_content(self):
        """测试内容"""
        from reasoning.futures_prompt import FUTURES_SYSTEM_PROMPT
        
        assert "期货" in FUTURES_SYSTEM_PROMPT
        assert "基差" in FUTURES_SYSTEM_PROMPT
        assert "持仓量" in FUTURES_SYSTEM_PROMPT
        assert "T+0" in FUTURES_SYSTEM_PROMPT


class TestSecuritiesPrompt:
    """证券Prompt模板测试"""
    
    def test_import(self):
        """测试导入"""
        from reasoning.securities_prompt import SECURITIES_SYSTEM_PROMPT
        assert SECURITIES_SYSTEM_PROMPT is not None
    
    def test_content(self):
        """测试内容"""
        from reasoning.securities_prompt import SECURITIES_SYSTEM_PROMPT
        
        assert "证券" in SECURITIES_SYSTEM_PROMPT
        assert "PE" in SECURITIES_SYSTEM_PROMPT
        assert "T+1" in SECURITIES_SYSTEM_PROMPT


class TestPromptRouter:
    """Prompt路由测试"""
    
    def test_import(self):
        """测试导入"""
        from reasoning.prompt_router import PromptRouter
        assert PromptRouter is not None
    
    def test_get_futures_prompt(self):
        """测试获取期货Prompt"""
        from reasoning.prompt_router import PromptRouter
        
        router = PromptRouter()
        prompt = router.get_prompt("futures")
        
        assert "期货" in prompt
    
    def test_get_securities_prompt(self):
        """测试获取证券Prompt"""
        from reasoning.prompt_router import PromptRouter
        
        router = PromptRouter()
        prompt = router.get_prompt("securities")
        
        assert "证券" in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
