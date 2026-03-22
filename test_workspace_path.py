#!/usr/bin/env python3
"""测试工作目录路径获取功能"""

from lingxi.utils.config import get_workspace_path
from lingxi.core.soul import SoulInjector
from lingxi.core.memory import MemoryManager
from lingxi.core.session import SessionManager

print("测试 get_workspace_path() 函数")
workspace_path = get_workspace_path()
print(f"当前工作目录: {workspace_path}")

print("\n测试 SoulInjector")
soul_injector = SoulInjector()
soul_injector.load()
print(f"SOUL.md 路径: {soul_injector.get_soul_path()}")

print("\n测试 MemoryManager")
memory_manager = MemoryManager()
print(f"MEMORY.md 路径: {memory_manager.get_memory_file()}")

print("\n测试 SessionManager")
session_manager = SessionManager()
print("SessionManager 初始化成功")

print("\n所有测试完成，代码运行正常！")
