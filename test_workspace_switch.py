#!/usr/bin/env python3
"""测试工作目录切换功能"""

import os
import tempfile
from pathlib import Path
from lingxi.management.workspace_manager import get_workspace_manager
from lingxi.utils.config import get_config, get_workspace_path

print("测试工作目录切换功能")
print("=" * 50)

# 获取当前配置
config = get_config()
print(f"当前配置中的工作目录: {config.get('workspace', {}).get('last_workspace')}")
print(f"当前全局工作目录: {get_workspace_path()}")

# 创建临时目录作为测试工作目录
with tempfile.TemporaryDirectory() as temp_dir:
    temp_path = Path(temp_dir)
    print(f"\n创建测试工作目录: {temp_path}")
    
    # 获取工作目录管理器
    workspace_manager = get_workspace_manager()
    
    # 切换工作目录
    print("\n切换工作目录...")
    result = workspace_manager.switch_workspace(str(temp_path))
    print(f"切换结果: {result['success']}")
    print(f"新工作目录: {result['data']['current_workspace']}")
    
    # 重新加载配置
    from lingxi.utils.config import reload_config
    reload_config()
    
    # 检查配置是否更新
    new_config = get_config()
    print(f"\n配置文件中的工作目录: {new_config.get('workspace', {}).get('last_workspace')}")
    print(f"全局工作目录: {get_workspace_path()}")
    
    # 验证工作目录是否正确保存
    if new_config.get('workspace', {}).get('last_workspace') == str(temp_path):
        print("\n✅ 测试通过：工作目录已正确保存到配置文件")
    else:
        print("\n❌ 测试失败：工作目录未正确保存到配置文件")

print("\n测试完成！")
