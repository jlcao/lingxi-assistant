#!/usr/bin/env python3
"""
测试安全沙箱配置功能
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from lingxi.core.utils.security import SecuritySandbox
from lingxi.utils.config import get_config, reload_config


def test_security_config():
    """测试安全沙箱配置"""
    print("=== 测试安全沙箱配置 ===")
    
    # 重新加载配置
    config = reload_config()
    print("\n1. 配置加载情况：")
    print(f"   安全沙箱配置: {config.get('security', {}).get('sandbox', {})}")
    
    # 测试1: 使用默认配置初始化
    print("\n2. 测试1: 使用默认配置初始化安全沙箱")
    sandbox = SecuritySandbox()
    print(f"   工作目录: {sandbox.workspace_root}")
    print(f"   最大文件大小: {sandbox.max_file_size}")
    print(f"   安全模式: {sandbox.safety_mode}")
    print(f"   允许的命令: {sorted(sandbox.allowed_commands)}")
    print(f"   白名单路径: {[str(p) for p in sandbox.white_list_paths]}")
    
    # 测试2: 测试路径验证
    print("\n3. 测试2: 路径验证")
    # 测试工作目录内的路径
    test_path = Path("./test.txt")
    is_valid, message = sandbox.validate_path(test_path)
    print(f"   验证工作目录内路径 {test_path}: {'有效' if is_valid else '无效'} - {message}")
    
    # 测试绝对路径（应该无效，除非在白名单中）
    absolute_path = Path.home() / "test.txt"
    is_valid, message = sandbox.validate_path(absolute_path)
    print(f"   验证绝对路径 {absolute_path}: {'有效' if is_valid else '无效'} - {message}")
    
    print("\n=== 测试完成 ===")


if __name__ == "__main__":
    test_security_config()
