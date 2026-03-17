#!/usr/bin/env python3
"""子代理自动检测示例"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lingxi.core.engine import DirectEngine
from lingxi.core.skill_caller import SkillCaller


class MockSessionManager:
    """模拟会话管理器用于测试"""
    def create_session(self, session_id=None, workspace_path=None):
        class Session:
            def __init__(self, sid):
                self.id = sid
            def get_history(self):
                return []
            def save_checkpoint(self, session_id, checkpoint):
                pass
            def restore_checkpoint(self, session_id):
                return None
        return Session(session_id or "test_session")


async def main():
    """主函数"""
    print("=" * 60)
    print("灵犀助手 - 子代理自动检测功能测试")
    print("=" * 60)
    
    config = {
        "workspace": {"default_path": "./workspace"},
        "max_concurrent": 5,
        "default_timeout": 300
    }
    
    # 初始化 SkillCaller
    skill_caller = SkillCaller(config)
    
    # 初始化 SessionManager
    session_manager = MockSessionManager()
    skill_caller.session_manager = session_manager
    
    # 初始化引擎
    from lingxi.core.engine import PlanReActEngine
    engine = PlanReActEngine(config, skill_caller, session_manager)
    
    print("\n【测试 1】检测并行关键词")
    print("-" * 40)
    test_task1 = "同时分析前端代码和后端代码"
    should_use = engine._should_use_subagent(test_task1)
    print(f"任务：{test_task1}")
    print(f"是否使用子代理：{should_use}")
    
    print("\n【测试 2】检测多行任务")
    print("-" * 40)
    test_task2 = """1. 分析项目目录结构
2. 读取 package.json
3. 检查依赖配置
4. 生成分析报告"""
    should_use = engine._should_use_subagent(test_task2)
    print(f"任务：{test_task2[:50]}...")
    print(f"是否使用子代理：{should_use}")
    
    print("\n【测试 3】任务分解功能")
    print("-" * 40)
    test_task3 = "分析代码结构，检查代码规范，运行单元测试"
    subtasks = engine._decompose_task(test_task3)
    print(f"原始任务：{test_task3}")
    print(f"分解为 {len(subtasks)} 个子任务:")
    for i, task in enumerate(subtasks, 1):
        print(f"  {i}. {task}")
    
    print("\n【测试 4】复杂任务自动分解")
    print("-" * 40)
    test_task4 = "请帮我全面分析这个项目的代码质量，包括代码规范检查、单元测试覆盖率分析、依赖安全性检查、性能瓶颈分析、代码复杂度评估等多个方面"
    should_use = engine._should_use_subagent(test_task4)
    subtasks = engine._decompose_task(test_task4)
    print(f"任务长度：{len(test_task4)} 字符")
    print(f"是否使用子代理：{should_use}")
    print(f"分解为 {len(subtasks)} 个子任务:")
    for i, task in enumerate(subtasks, 1):
        print(f"  {i}. {task[:60]}...")
    
    print("\n【测试 5】结果聚合功能")
    print("-" * 40)
    
    # 模拟子代理结果
    class MockResult:
        def __init__(self, result):
            self.result = result
        def to_dict(self):
            return {"result": self.result}
    
    mock_results = [
        MockResult("前端代码结构分析完成"),
        MockResult("后端代码结构分析完成"),
        MockResult("测试代码结构分析完成")
    ]
    
    aggregated = engine._aggregate_subagent_results(mock_results)
    print("聚合结果:")
    print(aggregated)
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    
    # 清理
    skill_caller.subagent_scheduler.cleanup_completed()


if __name__ == "__main__":
    asyncio.run(main())
