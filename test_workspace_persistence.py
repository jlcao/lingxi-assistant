#!/usr/bin/env python3
"""测试工作目录持久化功能"""

import os
import tempfile
from pathlib import Path
from lingxi.management.workspace_manager import get_workspace_manager
from lingxi.utils.config import get_config, get_workspace_path, reload_config

print("测试工作目录持久化功能")
print("=" * 50)

# 获取用户目录配置文件路径
user_home = Path.home()
user_config_path = user_home / ".lingxi" / "conf" / "config.yml"
print(f"用户目录配置文件: {user_config_path}")

# 读取当前用户配置
if user_config_path.exists():
    import yaml
    with open(user_config_path, 'r', encoding='utf-8') as f:
        user_config = yaml.safe_load(f)
    print(f"当前用户配置中的工作目录: {user_config.get('workspace', {}).get('last_workspace')}")
else:
    print("用户配置文件不存在")

# 获取当前配置
config = get_config()
print(f"当前全局配置中的工作目录: {config.get('workspace', {}).get('last_workspace')}")
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
    reload_config()
    
    # 检查配置是否更新
    new_config = get_config()
    print(f"\n全局配置文件中的工作目录: {new_config.get('workspace', {}).get('last_workspace')}")
    print(f"全局工作目录: {get_workspace_path()}")
    
    # 读取用户配置文件
    if user_config_path.exists():
        with open(user_config_path, 'r', encoding='utf-8') as f:
            updated_user_config = yaml.safe_load(f)
        user_workspace = updated_user_config.get('workspace', {}).get('last_workspace')
        print(f"用户配置文件中的工作目录: {user_workspace}")
        
        # 验证工作目录是否正确保存
        if user_workspace == str(temp_path):
            print("\n✅ 测试通过：工作目录已正确保存到用户配置文件")
        else:
            print("\n❌ 测试失败：工作目录未正确保存到用户配置文件")
    else:
        print("\n❌ 测试失败：用户配置文件不存在")

print("\n测试完成！")
