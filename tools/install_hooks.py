#!/usr/bin/env python3
"""
Git pre-commit hook 安装脚本

安装后，每次 git commit 会自动运行代码风格检查。

用法：
    python tools/install_hooks.py
"""

import os
import stat
from pathlib import Path


def install_pre_commit_hook():
    """安装 pre-commit hook"""
    project_root = Path(__file__).parent.parent
    hooks_dir = project_root / ".git" / "hooks"
    hook_file = hooks_dir / "pre-commit"

    # 确保 .git/hooks 目录存在
    hooks_dir.mkdir(parents=True, exist_ok=True)

    # 检查是否已有 hook
    if hook_file.exists():
        print(f"警告: {hook_file} 已存在")
        response = input("是否覆盖? (y/N): ")
        if response.lower() != "y":
            print("跳过安装")
            return False

    # 写入 hook 内容
    hook_content = '''#!/usr/bin/env python3
"""
Pre-commit hook: 代码风格检查

在 git commit 前自动运行 ruff 检查。
如检查失败，阻止提交并提示修复。
"""

import subprocess
import sys
from pathlib import Path


def main():
    """主函数"""
    project_root = Path(__file__).parent.parent.parent
    
    # 检查是否有暂存的 Python 文件
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    
    staged_files = [f for f in result.stdout.strip().split("\\n") if f.endswith(".py")]
    
    if not staged_files:
        # 没有 Python 文件，跳过检查
        return 0
    
    print(f"\\n[pre-commit] 检查 {len(staged_files)} 个 Python 文件...")
    
    # 运行 ruff check
    check_result = subprocess.run(
        ["python", "-m", "ruff", "check", "--fix"] + staged_files,
        cwd=project_root,
    )
    
    if check_result.returncode != 0:
        print("\\n[pre-commit] 代码风格检查失败")
        print("请运行 'python -m ruff check --fix <file>' 修复后再提交")
        print("或使用 'git commit --no-verify' 跳过检查\\n")
        return 1
    
    # 运行 ruff format
    format_result = subprocess.run(
        ["python", "-m", "ruff", "format"] + staged_files,
        cwd=project_root,
    )
    
    # 重新暂存格式化后的文件
    for f in staged_files:
        subprocess.run(
            ["git", "add", f],
            cwd=project_root,
        )
    
    print("[pre-commit] 代码风格检查通过\\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

    hook_file.write_text(hook_content, encoding="utf-8")

    # 设置可执行权限（Unix）
    if os.name != "nt":
        hook_file.chmod(hook_file.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    print(f"✓ pre-commit hook 已安装: {hook_file}")
    print("  每次 git commit 前会自动运行代码风格检查")
    return True


def install_commit_msg_hook():
    """安装 commit-msg hook（可选）"""
    project_root = Path(__file__).parent.parent
    hooks_dir = project_root / ".git" / "hooks"
    hook_file = hooks_dir / "commit-msg"

    hooks_dir.mkdir(parents=True, exist_ok=True)

    if hook_file.exists():
        print(f"跳过: {hook_file} 已存在")
        return False

    hook_content = '''#!/usr/bin/env python3
"""
Commit-msg hook: 验证提交信息格式

要求提交信息格式：
    <type>: <description>

type: feat, fix, docs, style, refactor, test, chore
"""

import re
import sys


def main():
    """主函数"""
    if len(sys.argv) < 2:
        return 0
    
    commit_msg_file = sys.argv[1]
    
    with open(commit_msg_file, 'r', encoding='utf-8') as f:
        commit_msg = f.read().strip()
    
    # 允许 merge commit
    if commit_msg.startswith("Merge "):
        return 0
    
    # 检查格式
    pattern = r"^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)(\\(.+\\))?: .+"
    
    if not re.match(pattern, commit_msg):
        print("\\n[commit-msg] 提交信息格式不正确")
        print("正确格式: <type>: <description>")
        print("type: feat, fix, docs, style, refactor, test, chore, perf, ci, build, revert")
        print("示例: feat: 添加新功能")
        print("      fix: 修复 bug")
        print("      docs: 更新文档\\n")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

    hook_file.write_text(hook_content, encoding="utf-8")

    if os.name != "nt":
        hook_file.chmod(hook_file.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    print(f"✓ commit-msg hook 已安装: {hook_file}")
    print("  提交信息格式: <type>: <description>")
    return True


def main():
    """主函数"""
    print("=" * 60)
    print("  安装 Git Hooks")
    print("=" * 60)

    install_pre_commit_hook()
    install_commit_msg_hook()

    print("\n" + "=" * 60)
    print("  安装完成")
    print("=" * 60)
    print("\n使用说明:")
    print("  - git commit 前自动检查代码风格")
    print("  - 提交信息格式: <type>: <description>")
    print("  - 跳过检查: git commit --no-verify")
    print()


if __name__ == "__main__":
    main()
