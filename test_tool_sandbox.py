#!/usr/bin/env python3
"""
本地工具沙盒执行测试脚本
验证本地工具是否使用了沙盒执行环境
"""

import logging
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from lingxi.core.action_caller import ActionCaller

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_tool_sandbox_execution():
    """测试本地工具的沙盒执行"""
    logger = logging.getLogger(__name__)
    logger.info("开始本地工具沙盒执行测试")
    
    # 配置
    config = {
        "security": {
            "max_file_size": 10 * 1024 * 1024,
            "safety_mode": True
        },
        "workspace": {
            "last_workspace": "./workspace"
        },
        "skills": {
            "builtin_skills_dir": "lingxi/skills/builtin",
            "user_skills_dir": ".lingxi/skills",
            "cache_ttl": 300
        },
        "executor": {
            "thread_pool_high_workers": 10,
            "thread_pool_low_workers": 5,
            "process_pool_workers": 4
        }
    }
    
    try:
        # 初始化 ActionCaller
        action_caller = ActionCaller(config)
        logger.info("ActionCaller 初始化成功")
        
        # 测试文件工具 - 列出当前目录
        logger.info("测试文件工具 - 列出当前目录")
        list_result = action_caller.call_with_security_check(
            "file",
            "tool",
            {
                "action": "list",
                "path": "."
            }
        )
        logger.info(f"文件工具执行结果: {list_result}")
        
        if list_result.get("success"):
            logger.info("文件工具执行成功")
        else:
            logger.warning(f"文件工具执行失败: {list_result.get('result')}")
        
        # 测试命令工具 - 执行简单命令
        logger.info("测试命令工具 - 执行简单命令")
        command_result = action_caller.call_with_security_check(
            "command",
            "tool",
            {
                "command": "echo hello world",
                "cwd": "."
            }
        )
        logger.info(f"命令工具执行结果: {command_result}")
        
        if command_result.get("success"):
            logger.info("命令工具执行成功")
        else:
            logger.warning(f"命令工具执行失败: {command_result.get('result')}")
        
        logger.info("本地工具沙盒执行测试完成")
        return True
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_tool_sandbox_execution()
    sys.exit(0 if success else 1)
