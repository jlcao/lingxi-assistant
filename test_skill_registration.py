#!/usr/bin/env python3
"""测试技能注册"""

import logging
from lingxi.utils.config import get_config
from lingxi.skills.skill_loader import SkillLoader

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 获取配置
config = get_config()

# 模拟技能注册表
class MockRegistry:
    def __init__(self):
        self.registered_skills = []
    
    def register_skill_from_dir(self, skill_dir):
        skill_id = skill_dir.split('\\')[-1] if '\\' in skill_dir else skill_dir.split('/')[-1]
        self.registered_skills.append(skill_id)
        print(f"注册技能：{skill_id}")
    
    def register_skill(self, skill_config):
        skill_id = skill_config.get('name')
        self.registered_skills.append(skill_id)
        print(f"注册技能：{skill_id}")

# 测试技能注册
def test_skill_registration():
    print("开始测试技能注册...")
    
    # 创建技能加载器
    loader = SkillLoader(config)
    
    # 创建模拟注册表
    registry = MockRegistry()
    
    # 扫描并注册技能
    registered_count = loader.scan_and_register(registry)
    
    print(f"\n技能注册完成，成功注册 {registered_count} 个技能")
    print(f"已注册技能：{registry.registered_skills}")
    
    # 检查目标技能是否注册成功
    target_skills = ['memory', 'spawn_subagent']
    for skill in target_skills:
        if skill in registry.registered_skills:
            print(f"✅ {skill} 技能注册成功")
        else:
            print(f"❌ {skill} 技能注册失败")

if __name__ == "__main__":
    test_skill_registration()
