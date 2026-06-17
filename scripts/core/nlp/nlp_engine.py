"""
NLP 引擎

整合自然语言处理组件：
- 意图识别
- 命令解析
- 上下文管理
- 响应生成
"""

import asyncio
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from .intent_recognizer import IntentRecognizer, Intent, IntentType
from .command_parser import CommandParser, Command
from .context_manager import ContextManager
from .response_generator import ResponseGenerator, Response

logger = logging.getLogger(__name__)


class NLPEngine:
    """NLP 引擎"""

    def __init__(self):
        self.intent_recognizer = IntentRecognizer()
        self.command_parser = CommandParser()
        self.context_manager = ContextManager()
        self.response_generator = ResponseGenerator()

    def process(self, user_input: str) -> str:
        """处理用户输入"""
        # 1. 识别意图
        intent = self.intent_recognizer.recognize(user_input)

        # 2. 解析命令
        command = self.command_parser.parse(intent)

        # 3. 执行命令
        if command:
            result = self._execute_command(command)
        else:
            result = self._handle_unknown(intent)

        # 4. 记录对话
        self.context_manager.add_turn(
            user_input=user_input,
            system_response=result,
            intent=intent.action,
        )

        return result

    def _execute_command(self, command: Command) -> str:
        """执行命令"""
        try:
            # 构建完整命令
            full_cmd = [sys.executable] + command.command.split()[1:] + command.args

            # 添加超时选项
            if "--timeout" not in " ".join(command.args):
                full_cmd.extend(["--timeout", "30"])

            # 执行命令
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(Path(__file__).parent.parent.parent.parent),
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                if output:
                    # 过滤掉网络错误信息，只保留有用输出
                    lines = output.split('\n')
                    filtered_lines = [l for l in lines if not l.startswith('[错误]') and '搜索失败' not in l]
                    filtered_output = '\n'.join(filtered_lines).strip()
                    if filtered_output:
                        return filtered_output
                    else:
                        return command.description + " 完成（但无有效输出）。"
                else:
                    return command.description + " 完成。"
            else:
                # 过滤错误输出中的网络错误
                error_lines = result.stderr.strip().split('\n')
                filtered_errors = [l for l in error_lines if '搜索失败' not in l and '超时' not in l]
                if filtered_errors:
                    return f"命令执行失败：{' '.join(filtered_errors[:3])}"
                else:
                    return command.description + " 执行完成（部分功能可能不可用）。"

        except subprocess.TimeoutExpired:
            return "命令执行超时（超过2分钟）。可能原因：\n1. 网络连接问题\n2. TqSdk 服务不稳定\n\n建议：请稍后重试。"
        except Exception as e:
            return f"执行命令时出错：{e}"

    def _handle_unknown(self, intent: Intent) -> str:
        """处理未知意图"""
        if intent.intent_type == IntentType.HELP:
            return self.command_parser.get_help()
        else:
            return self.response_generator.generate("unknown").text

    def get_help(self) -> str:
        """获取帮助信息"""
        help_text = """
我是 Trend Scanner Agent 的自然语言助手。您可以这样和我交流：

查询类：
  - "查看当前信号"
  - "显示持仓状态"
  - "什么品种有信号"

操作类：
  - "扫描一下"
  - "运行进化"
  - "同步数据"
  - "检查健康度"
  - "套利分析"

分析类：
  - "分析一下螺纹钢"
  - "为什么铜在涨"
  - "预测一下原油走势"

状态类：
  - "系统状态"
  - "是否在运行"

帮助类：
  - "帮助"
  - "怎么用"
"""
        return help_text

    def get_context_summary(self) -> str:
        """获取上下文摘要"""
        return self.context_manager.get_summary()
