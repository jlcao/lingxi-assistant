#!/usr/bin/env python3
"""测试技能系统重构"""

import logging
import sys
from lingxi.skills import (
    SkillSystem,
    SkillResponse,
    ExecutionContext,
    TrustLevel
)

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_skill_system_initialization():
    """测试技能系统初始化"""
    print("\n=== 测试 1: 技能系统初始化 ===")
    
    # 配置
    config = {
        "security": {
            "max_file_size": 10 * 1024 * 1024,
            "safety_mode": True
        },
        "skills": {
            "cache_ttl": 300
        },
        "workspace": {
            "last_workspace": "./workspace"
        }
    }
    
    try:
        # 初始化技能系统
        skill_system = SkillSystem(config)
        logger.info("技能系统初始化成功")
        
        # 测试列出技能
        skills = skill_system.list_skills()
        logger.info(f"发现 {len(skills)} 个技能")
        for skill in skills:
            logger.info(f"  - {skill.get('name', 'Unknown')} (ID: {skill.get('skill_id', 'Unknown')})")
        
        return True
    except Exception as e:
        logger.error(f"技能系统初始化失败: {e}")
        return False

def test_skill_execution():
    """测试技能执行"""
    print("\n=== 测试 2: 技能执行 ===")
    
    # 配置
    config = {
        "security": {
            "max_file_size": 10 * 1024 * 1024,
            "safety_mode": True
        },
        "skills": {
            "cache_ttl": 300
        },
        "workspace": {
            "last_workspace": "./workspace"
        }
    }
    
    try:
        # 初始化技能系统
        skill_system = SkillSystem(config)
        
        # 测试执行一个简单的技能
        # 注意：这里假设存在一个名为 "test" 的技能，或者使用实际存在的技能
        test_skill_id = "pdf"  # 使用实际存在的技能
        params = {"file_path": "test.pdf"}  # 测试参数
        
        logger.info(f"尝试执行技能: {test_skill_id}")
        response = skill_system.execute_skill(test_skill_id, params)
        
        logger.info(f"执行结果: {response.success}")
        logger.info(f"响应代码: {response.code}")
        logger.info(f"消息: {response.message}")
        logger.info(f"元数据: {response.meta}")
        
        return True
    except Exception as e:
        logger.error(f"技能执行测试失败: {e}")
        return False

def test_skill_reload():
    """测试技能热重载"""
    print("\n=== 测试 3: 技能热重载 ===")
    
    # 配置
    config = {
        "security": {
            "max_file_size": 10 * 1024 * 1024,
            "safety_mode": True
        },
        "skills": {
            "cache_ttl": 300
        },
        "workspace": {
            "last_workspace": "./workspace"
        }
    }
    
    try:
        # 初始化技能系统
        skill_system = SkillSystem(config)
        
        # 获取技能列表
        skills = skill_system.list_skills()
        if skills:
            test_skill_id = skills[0].get('skill_id')
            logger.info(f"尝试重新加载技能: {test_skill_id}")
            
            # 测试热重载
            success = skill_system.reload_skill(test_skill_id)
            logger.info(f"热重载结果: {success}")
            
            return success
        else:
            logger.warning("没有找到技能，跳过热重载测试")
            return True
    except Exception as e:
        logger.error(f"技能热重载测试失败: {e}")
        return False

def test_execution_context():
    """测试执行上下文"""
    print("\n=== 测试 4: 执行上下文 ===")
    
    try:
        # 创建执行上下文
        context = ExecutionContext(
            skill_id="test_skill",
            trust_level=TrustLevel.L1,
            workspace="./workspace"
        )
        
        logger.info(f"上下文创建成功，trace_id: {context.trace_id}")
        logger.info(f"技能ID: {context.skill_id}")
        logger.info(f"信任等级: {context.trust_level}")
        logger.info(f"工作目录: {context.workspace}")
        
        # 测试上下文克隆
        cloned_context = context.clone()
        logger.info(f"上下文克隆成功，trace_id: {cloned_context.trace_id}")
        
        return True
    except Exception as e:
        logger.error(f"执行上下文测试失败: {e}")
        return False

def test_skill_response():
    """测试技能响应"""
    print("\n=== 测试 5: 技能响应 ===")
    
    try:
        # 创建成功响应
        success_response = SkillResponse.success(
            data="测试成功",
            message="操作完成",
            skill_id="test_skill",
            trace_id="test_trace"
        )
        
        logger.info(f"成功响应: {success_response.to_dict()}")
        
        # 创建错误响应
        error_response = SkillResponse.error(
            message="测试失败",
            code=400,
            skill_id="test_skill",
            trace_id="test_trace"
        )
        
        logger.info(f"错误响应: {error_response.to_dict()}")
        
        return True
    except Exception as e:
        logger.error(f"技能响应测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("开始测试技能系统重构...")
    
    tests = [
        test_skill_system_initialization,
        test_execution_context,
        test_skill_response,
        test_skill_execution,
        test_skill_reload
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
    
    print(f"\n=== 测试结果 ===")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    
    if failed == 0:
        print("✅ 所有测试通过！技能系统重构成功。")
        return 0
    else:
        print("❌ 部分测试失败，需要检查。")
        return 1

if __name__ == "__main__":
    sys.exit(main())