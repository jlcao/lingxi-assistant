#!/usr/bin/env python3
"""测试用户目录路径"""

from pathlib import Path

print("获取用户目录路径")
print(f"用户目录: {Path.home()}")
print(f".lingxi 目录: {Path.home() / '.lingxi'}")
print(f"配置文件路径: {Path.home() / '.lingxi' / 'conf' / 'config.yml'}")
