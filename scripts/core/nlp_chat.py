#!/usr/bin/env python3
"""
自然语言交互 CLI

允许用户通过自然语言与系统交互：
- 查询信号
- 执行操作
- 查看状态
- 获取帮助

用法：
    python scripts/core/nlp_chat.py
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "scripts"))

from core.nlp import NLPEngine


def main():
    """主函数"""
    print("=" * 60)
    print("Trend Scanner Agent - 自然语言交互")
    print("=" * 60)
    print("输入自然语言指令，系统会自动识别并执行。")
    print("输入 'help' 查看帮助，输入 'quit' 退出。")
    print("=" * 60)
    print()

    engine = NLPEngine()

    while True:
        try:
            # 获取用户输入
            user_input = input("您: ").strip()

            # 检查退出命令
            if user_input.lower() in ["quit", "exit", "q", "退出"]:
                print("再见！")
                break

            # 检查空输入
            if not user_input:
                continue

            # 处理自然语言
            response = engine.process(user_input)

            # 显示响应
            print(f"系统: {response}")
            print()

        except KeyboardInterrupt:
            print("\n再见！")
            break
        except Exception as e:
            print(f"错误: {e}")
            print()


if __name__ == "__main__":
    main()
