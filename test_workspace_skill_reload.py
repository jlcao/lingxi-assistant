#!/usr/bin/env python3
"""测试工作目录切换时技能重新加载"""

import os
import shutil
import tempfile
import asyncio
from pathlib import Path
from lingxi.management.workspace import get_workspace_manager
from lingxi.core.skill_caller import SkillCaller
from lingxi.utils.config import load_config

async def test_workspace_skill_reload():
    # 加载配置
    config = load_config()

    # 创建临时工作目录
    temp_dir1 = tempfile.mkdtemp()
    temp_dir2 = tempfile.mkdtemp()

    print(f"创建临时工作目录 1: {temp_dir1}")
    print(f"创建临时工作目录 2: {temp_dir2}")

    # 在第一个工作目录创建技能
    skill_dir1 = Path(temp_dir1) / ".lingxi" / "skills" / "test_skill1"
    skill_dir1.mkdir(parents=True, exist_ok=True)

    # 创建技能文件
    with open(skill_dir1 / "main.py", "w", encoding="utf-8") as f:
        f.write("""
def execute(parameters):
    return "Hello from test_skill1"
""")

    with open(skill_dir1 / "SKILL.md", "w", encoding="utf-8") as f:
        f.write("""# Test Skill 1

## Description
Test skill for workspace 1

## Parameters
- None

## Returns
- String: Greeting message
""")

    # 在第二个工作目录创建技能
    skill_dir2 = Path(temp_dir2) / ".lingxi" / "skills" / "test_skill2"
    skill_dir2.mkdir(parents=True, exist_ok=True)

    # 创建技能文件
    with open(skill_dir2 / "main.py", "w", encoding="utf-8") as f:
        f.write("""
def execute(parameters):
    return "Hello from test_skill2"
""")

    with open(skill_dir2 / "SKILL.md", "w", encoding="utf-8") as f:
        f.write("""# Test Skill 2

## Description
Test skill for workspace 2

## Parameters
- None

## Returns
- String: Greeting message
""")

    # 初始化技能调用器和工作空间管理器
    skill_caller = SkillCaller(config)
    workspace_manager = get_workspace_manager(config)

    # 设置资源引用
    workspace_manager.set_resources(
        sandbox=skill_caller.sandbox,
        skill_caller=skill_caller,
        skill_system=skill_caller.skill_system,
        session_store=None
    )

    print("\n=== 测试开始 ===")

    # 切换到第一个工作目录
    print("\n1. 切换到工作目录 1...")
    result = await workspace_manager.switch_workspace(temp_dir1, force=True)
    print(f"切换结果: {result['success']}")

    # 列出技能
    print("\n2. 技能列表（工作目录 1）:")
    skills = skill_caller.list_available_skills()
    for skill in skills:
        if skill['name'] in ['test_skill1', 'test_skill2']:
            print(f"  - {skill['name']}: {skill['description']}")

    # 执行技能
    print("\n3. 执行 test_skill1:")
    try:
        result = skill_caller.call("test_skill1")
        print(f"  结果: {result}")
    except Exception as e:
        print(f"  错误: {e}")

    # 切换到第二个工作目录
    print("\n4. 切换到工作目录 2...")
    result = await workspace_manager.switch_workspace(temp_dir2, force=True)
    print(f"切换结果: {result['success']}")

    # 列出技能
    print("\n5. 技能列表（工作目录 2）:")
    skills = skill_caller.list_available_skills()
    for skill in skills:
        if skill['name'] in ['test_skill1', 'test_skill2']:
            print(f"  - {skill['name']}: {skill['description']}")

    # 执行技能
    print("\n6. 执行 test_skill2:")
    try:
        result = skill_caller.call("test_skill2")
        print(f"  结果: {result}")
    except Exception as e:
        print(f"  错误: {e}")

    # 清理临时目录
    print("\n7. 清理临时目录...")
    shutil.rmtree(temp_dir1)
    shutil.rmtree(temp_dir2)

    print("\n=== 测试完成 ===")
    print("如果测试成功，应该看到:")
    print("- 切换到工作目录 1 后能看到并执行 test_skill1")
    print("- 切换到工作目录 2 后能看到并执行 test_skill2")

if __name__ == "__main__":
    asyncio.run(test_workspace_skill_reload())