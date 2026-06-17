#!/usr/bin/env python3
"""
启动文件监控自动 Git 推送脚本

此脚本会检查 auto_git_push.py 是否在运行，如果没有运行则启动它。
可以用 cron 或 WorkBuddy automation 定期调用此脚本来确保监控持续运行。

用法：
    python tools/start_auto_git_push.py
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

import psutil


def is_script_running(script_name: str = "auto_git_push.py") -> bool:
    """检查脚本是否已在运行"""
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = proc.info["cmdline"]
            if cmdline and script_name in " ".join(cmdline):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False


def start_script():
    """启动监控脚本"""
    repo_dir = Path(__file__).parent.parent.resolve()
    script_path = Path(__file__).parent / "auto_git_push.py"
    log_dir = repo_dir / ".workbuddy" / "memory"
    log_file = log_dir / "auto_git_push.log"

    # 创建日志目录
    log_dir.mkdir(parents=True, exist_ok=True)

    # 检查是否已在运行
    if is_script_running():
        msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] auto_git_push.py 已在运行，跳过启动"
        print(msg)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
        return

    # 启动脚本
    msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 启动 auto_git_push.py..."
    print(msg)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

    # 使用 nohup 在后台启动
    python_exe = sys.executable
    cmd = [python_exe, str(script_path), "--debounce", "5", "--branch", "main"]

    try:
        # 在 Windows 上使用 CREATE_NEW_PROCESS_GROUP
        if sys.platform == "win32":
            process = subprocess.Popen(
                cmd,
                stdout=open(log_file, "a"),
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                cwd=str(repo_dir),
            )
        else:
            process = subprocess.Popen(
                cmd, stdout=open(log_file, "a"), stderr=subprocess.STDOUT, start_new_session=True, cwd=str(repo_dir)
            )

        msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] auto_git_push.py 启动成功，PID: {process.pid}"
        print(msg)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(msg + "\n")

    except Exception as e:
        msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] auto_git_push.py 启动失败: {e}"
        print(msg, file=sys.stderr)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(msg + "\n")


if __name__ == "__main__":
    try:
        import psutil
    except ImportError:
        print("错误：需要安装 psutil 库")
        print("请运行：pip install psutil")
        sys.exit(1)

    start_script()
