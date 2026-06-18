#!/usr/bin/env python3
import sys
from pathlib import Path


# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "scripts"))

print("[调试] 开始导入模块...")

try:
    print("[调试] data_source 导入成功")
except Exception as e:
    print(f"[错误] data_source 导入失败: {e}")
    sys.exit(1)

try:
    print("[调试] indicators 导入成功")
except Exception as e:
    print(f"[错误] indicators 导入失败: {e}")
    sys.exit(1)

print("[调试] 所有模块导入成功")
