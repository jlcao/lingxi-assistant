#!/usr/bin/env python3
"""测试安全沙箱白名单功能"""

import logging
from lingxi.core.utils.security import SecuritySandbox, SecurityError
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 测试白名单功能
def test_white_list():
    print("开始测试安全沙箱白名单功能...")
    
    # 创建测试目录
    test_workspace = Path("./test_workspace")
    test_workspace.mkdir(exist_ok=True)
    
    # 创建测试文件
    test_file = test_workspace / "test.txt"
    test_file.write_text("测试文件内容")
    
    # 创建白名单目录
    white_list_dir = Path("./white_list_dir")
    white_list_dir.mkdir(exist_ok=True)
    
    # 创建白名单文件
    white_list_file = white_list_dir / "white_list.txt"
    white_list_file.write_text("白名单文件内容")
    
    # 测试 1: 初始化安全沙箱，添加白名单
    print("\n测试 1: 初始化安全沙箱，添加白名单")
    sandbox = SecuritySandbox(
        workspace_root=str(test_workspace),
        white_list_paths=[str(white_list_dir)]
    )
    
    # 测试 2: 测试工作目录内的文件访问
    print("\n测试 2: 测试工作目录内的文件访问")
    try:
        content = sandbox.safe_read(str(test_file))
        print(f"✅ 成功读取工作目录内的文件：{test_file}")
        print(f"文件内容：{content}")
    except Exception as e:
        print(f"❌ 读取工作目录内的文件失败：{e}")
    
    # 测试 3: 测试白名单目录内的文件访问
    print("\n测试 3: 测试白名单目录内的文件访问")
    try:
        content = sandbox.safe_read(str(white_list_file))
        print(f"✅ 成功读取白名单目录内的文件：{white_list_file}")
        print(f"文件内容：{content}")
    except Exception as e:
        print(f"❌ 读取白名单目录内的文件失败：{e}")
    
    # 测试 4: 测试工作目录和白名单外的文件访问
    print("\n测试 4: 测试工作目录和白名单外的文件访问")
    try:
        content = sandbox.safe_read("../README.md")
        print(f"❌ 不应该能读取工作目录外的文件：../README.md")
    except SecurityError as e:
        print(f"✅ 正确拒绝访问工作目录外的文件：{e}")
    
    # 测试 5: 动态添加白名单路径
    print("\n测试 5: 动态添加白名单路径")
    parent_dir = Path(".").resolve()
    sandbox.add_white_list_path(str(parent_dir))
    
    try:
        content = sandbox.safe_read("README.md")
        print(f"✅ 成功读取新添加的白名单路径内的文件：README.md")
    except Exception as e:
        print(f"❌ 读取新添加的白名单路径内的文件失败：{e}")
    
    # 测试 6: 移除白名单路径
    print("\n测试 6: 移除白名单路径")
    sandbox.remove_white_list_path(str(parent_dir))
    
    try:
        content = sandbox.safe_read("README.md")
        print(f"❌ 移除白名单后不应该能读取该路径内的文件：README.md")
    except SecurityError as e:
        print(f"✅ 正确拒绝访问已移除的白名单路径内的文件：{e}")
    
    # 测试 7: 测试路径验证方法
    print("\n测试 7: 测试路径验证方法")
    test_path = str(test_file)
    white_list_path = str(white_list_file)
    outside_path = "../README.md"
    
    print(f"工作目录内的路径 {test_path}: {sandbox.is_path_allowed(test_path)}")
    print(f"白名单内的路径 {white_list_path}: {sandbox.is_path_allowed(white_list_path)}")
    print(f"工作目录外的路径 {outside_path}: {sandbox.is_path_allowed(outside_path)}")
    
    # 清理测试文件
    import shutil
    shutil.rmtree(test_workspace, ignore_errors=True)
    shutil.rmtree(white_list_dir, ignore_errors=True)
    
    print("\n测试完成！")

if __name__ == "__main__":
    test_white_list()
