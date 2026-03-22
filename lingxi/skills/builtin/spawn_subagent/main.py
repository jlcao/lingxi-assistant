#!/usr/bin/env python3
"""Spawn 子代理技能 - 手动创建子代理执行任务"""

import logging
from typing import Dict, Any
import asyncio


def execute(parameters: Dict[str, Any]) -> str:
    """
    执行 spawn 子代理
    
    参数：
    - task: 任务描述（必填）
    - workspace_path: 工作目录（可选）
    - timeout: 超时时间（可选，默认 300 秒）
    - wait: 是否等待完成（可选，默认 True）
    
    返回：
    - 任务 ID 和执行状态
    """
    logger = logging.getLogger(__name__)
    
    task = parameters.get("task") or parameters.get("task_description")
    if not task:
        return "错误：缺少 task 参数"
    
    workspace_path = parameters.get("workspace_path")
    timeout = parameters.get("timeout", 300)
    wait = parameters.get("wait", True)
    
    logger.info(f"Spawn 子代理任务：{task[:50]}...")
    
    try:
        # 获取 SkillCaller 单例实例
        from lingxi.core.skill_caller import SkillCaller
        
        # 注意：SkillCaller 是单例，但需要 config 初始化
        # 这里我们通过全局方式获取已初始化的实例
        # 在实际使用中，skill_caller 应该通过依赖注入传递
        
        # 尝试从全局获取 skill_caller
        skill_caller = None
        
        # 方法 1：尝试从模块全局变量获取
        import lingxi.core.skill_caller as sc_module
        if hasattr(sc_module.SkillCaller, '_instance') and sc_module.SkillCaller._instance:
            skill_caller = sc_module.SkillCaller._instance
            logger.debug("从单例获取 SkillCaller 实例")
        
        if not skill_caller:
            return "错误：SkillCaller 未初始化，无法创建子代理"
        
        if not hasattr(skill_caller, 'subagent_scheduler'):
            return "错误：子代理调度器未初始化"
        
        # 异步执行 spawn
        async def spawn_task():
            # 传递 context 参数，即使为空
            task_id = await skill_caller.subagent_scheduler.spawn(
                task=task,
                workspace_path=workspace_path,
                timeout=timeout,
                context={}
            )
            return task_id
        
        # 运行异步代码
        # 使用在单独线程中执行异步代码的方式，避免与当前事件循环冲突
        def run_async(coro):
            # 在单独的线程中执行异步代码
            import threading
            result = None
            error = None
            
            def run_in_thread():
                nonlocal result, error
                try:
                    result = asyncio.run(coro)
                except Exception as e:
                    error = e
            
            # 创建并启动线程
            thread = threading.Thread(target=run_in_thread)
            thread.start()
            thread.join()
            
            # 检查是否有错误
            if error:
                raise error
            
            return result
        
        # 执行spawn任务
        task_id = run_async(spawn_task())
        
        if wait:
            # 等待任务完成
            async def wait_task():
                result = await skill_caller.subagent_scheduler.wait_for_task(task_id, timeout)
                return result
            
            # 执行wait任务
            result = run_async(wait_task())
            
            if result:
                return f"子代理任务完成\n任务 ID: {task_id}\n状态：{result.status}\n结果：{result.result}"
            else:
                return f"子代理任务超时\n任务 ID: {task_id}"
        else:
            return f"子代理已创建，任务 ID: {task_id}\n状态：pending\n使用 wait=False，任务在后台执行"
    
    except Exception as e:
        logger.error(f"Spawn 子代理失败：{e}")
        import traceback
        return f"Spawn 子代理失败：{str(e)}\n{traceback.format_exc()}"
