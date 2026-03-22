#!/usr/bin/env python3
"""
Test script for financial_news skill
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from lingxi.skills.skill_system import SkillSystem
from lingxi.utils.config import get_config

# Get configuration
config = get_config()

# Initialize skill system
skill_system = SkillSystem(config)

# Test financial_news skill
print("Testing financial_news skill...")
try:
    # Call the skill
    result = skill_system.execute_skill("financial_news", {"hours": 24, "num_results": 5})
    print("\nSkill execution result:")
    print(result)
    print("\nTest completed successfully!")
except Exception as e:
    print(f"\nError testing financial_news skill: {e}")
    import traceback
    traceback.print_exc()