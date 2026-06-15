#!/usr/bin/env python3
import sys
print("开始")
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    print("watchdog 导入成功")
except Exception as e:
    print(f"watchdog 导入失败: {e}")
print("结束")
