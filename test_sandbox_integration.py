#!/usr/bin/env python3
"""
沙盒集成测试脚本
验证技能系统与沙盒机制的整合是否正常工作
"""

import logging
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from lingxi.skills.skill_system import SkillSystem
from lingxi.skills.execution_context import TrustLevel

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_sandbox_integration():
    """测试沙盒集成"""
    logger = logging.getLogger(__name__)
    logger.info("开始沙盒集成测试")
    
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
        # 初始化技能系统
        skill_system = SkillSystem(config)
        logger.info("技能系统初始化成功")
        
        # 列出所有技能
        skills = skill_system.list_skills()
        logger.info(f"发现 {len(skills)} 个技能")
        for skill in skills:
            logger.debug(f"技能: {skill['name']}, 信任等级: {skill.get('trust_level', 'L1')}")
        
        # 测试执行一个简单技能（使用 L1 沙盒）
        logger.info("测试执行 L1 信任等级技能")
        if skills:
            test_skill_id = skills[0]['name']
            logger.info(f"测试技能: {test_skill_id}")
            
            # 执行技能
            response = skill_system.execute_skill(test_skill_id, {})
            logger.info(f"执行结果: {response}")
            
            if response.success:
                logger.info("L1 沙盒执行成功")
            else:
                logger.warning(f"L1 沙盒执行失败: {response.message}")
        
        # 测试异步执行
        logger.info("测试异步执行技能")
        if skills:
            test_skill_id = skills[0]['name']
            future = skill_system.execute_skill_async(test_skill_id, {})
            response = future.result()
            logger.info(f"异步执行结果: {response}")
            
            if response.success:
                logger.info("异步执行成功")
            else:
                logger.warning(f"异步执行失败: {response.message}")
        
        logger.info("沙盒集成测试完成")
        return True
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_sandbox_integration()
    sys.exit(0 if success else 1)
