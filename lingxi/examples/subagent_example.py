#!/usr/bin/env python3
"""子代理使用示例（带进度监控）"""

import asyncio
from lingxi.core.skill_caller import SkillCaller

async def main():
    config = {
        "max_concurrent": 5,
        "default_timeout": 300
    }
    
    skill_caller = SkillCaller(config)
    
    # Spawn 单个子代理
    print("🚀 Spawn 子代理...")
    task_id = await skill_caller.subagent_scheduler.spawn(
        task="分析这个项目的代码结构",
        workspace_path="/home/admin/lingxi-assistant"
    )
    print(f"子代理已启动：{task_id}")
    
    # 轮询进度
    print("\n📊 监控进度...")
    while True:
        progress = skill_caller.subagent_scheduler.get_task_progress(task_id)
        
        if progress:
            print(f"  进度：{progress['progress']}% - {progress['current_step']}")
            print(f"  步骤：{progress['completed_steps']}/{progress['total_steps']}")
            
            if progress.get('logs'):
                print(f"  日志:")
                for log in progress['logs']:
                    print(f"    - {log}")
        
        if progress and progress['status'] in ['completed', 'failed', 'timeout']:
            break
        
        await asyncio.sleep(1)
    
    # 最终结果
    print(f"\n✅ 任务完成！")
    task = skill_caller.subagent_scheduler.get_task(task_id)
    print(f"  状态：{task.status}")
    print(f"  耗时：{task.duration:.2f}s")
    print(f"  结果：{str(task.result)[:200]}...")
    
    # 列出所有任务
    tasks = skill_caller.subagent_scheduler.list_tasks()
    print(f"\n所有任务：{len(tasks)} 个")
    for t in tasks:
        print(f"  - {t.id}: {t.status}")

if __name__ == "__main__":
    asyncio.run(main())
