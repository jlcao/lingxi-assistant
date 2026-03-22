#!/usr/bin/env python3
"""记忆管理器使用示例"""

import os
import sys
# 添加正确的父目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

import logging
from lingxi.core.memory import (
    UserMemoryManager, WorkspaceMemoryManager, 
    search_combined_memory, save_memory_with_context, save_all_memories
)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 工作目录路径
workspace_path = "./workspace"

def example_user_memory():
    """用户记忆示例"""
    print("\n=== 用户记忆示例 ===")
    
    # 初始化用户记忆管理器
    user_manager = UserMemoryManager()
    
    # 保存用户偏好
    user_manager.save_memory(
        content="我喜欢用VS Code编辑器",
        category="preference",
        tags=["editor", "coding"],
        importance=4
    )
    
    user_manager.save_memory(
        content="我住在北京",
        category="fact",
        tags=["personal", "location"],
        importance=5
    )
    
    # 搜索用户记忆
    results = user_manager.search_memory(query="北京")
    print("搜索用户记忆结果：")
    for memory in results:
        print(f"- {memory.content} (分类: {memory.category}, 重要性: {memory.importance})")
    
    # 持久化用户记忆
    user_manager.save_to_file()
    
    # 获取统计信息
    stats = user_manager.get_stats()
    print(f"\n用户记忆统计：")
    print(f"总记忆数：{stats['total']}")
    print(f"按分类统计：{stats['by_category']}")

def example_workspace_memory():
    """工作记忆示例"""
    print("\n=== 工作记忆示例 ===")
    
    # 初始化工作记忆管理器
    workspace_manager = WorkspaceMemoryManager(workspace_path)
    
    # 保存项目相关记忆
    workspace_manager.save_memory(
        content="项目使用Python和Vue.js开发",
        category="fact",
        tags=["project", "tech"],
        importance=4
    )
    
    workspace_manager.save_memory(
        content="完成项目文档",
        category="todo",
        tags=["work", "priority"],
        importance=5
    )
    
    workspace_manager.save_memory(
        content="决定采用React作为前端框架",
        category="decision",
        tags=["project", "tech"],
        importance=4
    )
    
    # 搜索工作记忆
    results = workspace_manager.search_memory(query="项目")
    print("搜索工作记忆结果：")
    for memory in results:
        print(f"- {memory.content} (分类: {memory.category}, 重要性: {memory.importance})")
    
    # 持久化工作记忆
    workspace_manager.save_to_file()
    
    # 获取统计信息
    stats = workspace_manager.get_stats()
    print(f"\n工作记忆统计：")
    print(f"总记忆数：{stats['total']}")
    print(f"按分类统计：{stats['by_category']}")

def example_combined_search():
    """混合搜索示例"""
    print("\n=== 混合搜索示例 ===")
    
    # 搜索用户记忆和工作记忆
    results = search_combined_memory(
        query="开发",
        workspace_path=workspace_path
    )
    
    print("混合搜索结果（工作记忆优先）：")
    for memory in results:
        source = "工作记忆" if workspace_path in memory.workspace_path else "用户记忆"
        print(f"- {memory.content} (分类: {memory.category}, 来源: {source})")

def example_save_with_context():
    """根据上下文保存记忆示例"""
    print("\n=== 根据上下文保存记忆示例 ===")
    
    # 保存用户记忆（非项目特定）
    user_memory = save_memory_with_context(
        content="我喜欢喝咖啡",
        category="preference",
        tags=["food", "drink"]
    )
    print(f"保存用户记忆：{user_memory.content}")
    
    # 保存工作记忆（项目特定）
    workspace_memory = save_memory_with_context(
        content="项目截止日期是本周五",
        category="fact",
        tags=["project", "deadline"],
        workspace_path=workspace_path,
        is_project_specific=True
    )
    print(f"保存工作记忆：{workspace_memory.content}")

def example_save_all():
    """保存所有记忆示例"""
    print("\n=== 保存所有记忆示例 ===")
    
    # 保存所有记忆
    save_all_memories(workspace_path)
    print("所有记忆已成功保存")

if __name__ == "__main__":
    print("灵犀智能助手记忆管理器使用示例")
    print("=" * 50)
    
    # 运行各个示例
    example_user_memory()
    example_workspace_memory()
    example_combined_search()
    example_save_with_context()
    example_save_all()
    
    print("\n" + "=" * 50)
    print("示例运行完成！")
    print("\n查看生成的 MEMORY.md 文件：")
    print(f"- 用户记忆：~/.lingxi/memory/MEMORY.md")
    print(f"- 工作记忆：{workspace_path}/MEMORY.md")
