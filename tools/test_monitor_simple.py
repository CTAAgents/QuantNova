#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("[调试] 开始导入模块...")

try:
    from trend_scanner.data_source import DataSourceFactory
    print("[调试] data_source 导入成功")
except Exception as e:
    print(f"[错误] data_source 导入失败: {e}")
    sys.exit(1)

try:
    from trend_scanner.indicators import IndicatorEngine
    print("[调试] indicators 导入成功")
except Exception as e:
    print(f"[错误] indicators 导入失败: {e}")
    sys.exit(1)

try:
    from data_formats import load_config
    print("[调试] data_formats 导入成功")
except Exception as e:
    print(f"[错误] data_formats 导入失败: {e}")
    sys.exit(1)

print("[调试] 所有模块导入成功")
print("[调试] 尝试创建数据源...")

try:
    data_source = DataSourceFactory.create()
    print(f"[调试] 数据源创建成功: {type(data_source)}")
except Exception as e:
    print(f"[错误] 数据源创建失败: {e}")
    sys.exit(1)

print("[调试] 测试完成")
