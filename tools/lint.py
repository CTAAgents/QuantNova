#!/usr/bin/env python3
"""
代码风格检查与自动修复脚本

使用 ruff 进行代码风格检查和自动修复。

用法：
    python tools/lint.py              # 检查代码风格
    python tools/lint.py --fix        # 自动修复
    python tools/lint.py --format     # 格式化代码
    python tools/lint.py --check-only # 仅检查，不修复
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list, description: str) -> int:
    """运行命令并返回退出码"""
    print(f"\n{'=' * 60}")
    print(f"  {description}")
    print(f"{'=' * 60}")
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    return result.returncode


def main():
    """主函数"""
    args = sys.argv[1:]
    project_root = Path(__file__).parent.parent
    
    # 检查 ruff 是否安装
    try:
        subprocess.run(
            ["ruff", "--version"],
            capture_output=True,
            check=True,
        )
    except FileNotFoundError:
        print("错误: ruff 未安装")
        print("请运行: pip install ruff")
        return 1
    
    # 定义目标目录
    target_dirs = ["scripts", "tools", "tests"]
    existing_dirs = [d for d in target_dirs if (project_root / d).exists()]
    
    if not existing_dirs:
        print("错误: 未找到目标目录")
        return 1
    
    exit_code = 0
    
    if "--format" in args:
        # 仅格式化
        exit_code = run_command(
            ["ruff", "format"] + existing_dirs,
            "格式化代码"
        )
    elif "--fix" in args:
        # 检查 + 修复
        exit_code = run_command(
            ["ruff", "check", "--fix"] + existing_dirs,
            "检查并修复代码风格"
        )
        # 格式化
        format_code = run_command(
            ["ruff", "format"] + existing_dirs,
            "格式化代码"
        )
        if format_code != 0:
            exit_code = format_code
    elif "--check-only" in args:
        # 仅检查
        exit_code = run_command(
            ["ruff", "check"] + existing_dirs,
            "检查代码风格"
        )
    else:
        # 默认：检查 + 显示建议
        exit_code = run_command(
            ["ruff", "check", "--show-fixes"] + existing_dirs,
            "检查代码风格（显示可修复项）"
        )
        
        # 同时检查格式
        format_check = run_command(
            ["ruff", "format", "--check"] + existing_dirs,
            "检查代码格式"
        )
        if format_check != 0:
            exit_code = format_check
    
    # 总结
    print(f"\n{'=' * 60}")
    if exit_code == 0:
        print("  ✓ 代码风格检查通过")
    else:
        print("  ✗ 发现代码风格问题")
        print("  运行 `python tools/lint.py --fix` 自动修复")
    print(f"{'=' * 60}\n")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
