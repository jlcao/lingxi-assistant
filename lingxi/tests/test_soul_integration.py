#!/usr/bin/env python3
"""SOUL 注入集成测试"""

import pytest
import sys
import os
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from lingxi.core.soul import SoulInjector, SoulParser


class TestSoulIntegration:
    """SOUL 注入集成测试"""
    
    @pytest.fixture
    def test_soul_content(self):
        return """# SOUL.md - Who You Are

## Core Identity
- **Name:** 灵犀
- **Creature:** AI 助手
- **Vibe:** 温暖、专业、幽默
- **Emoji:** 🦋

## Core Truths
- Be genuinely helpful
- Have opinions
- Be resourceful

## Boundaries
- Private things stay private
- Ask before acting externally

## Memory
- 用户偏好：喜欢简洁的回复
- 当前项目：灵犀助手开发
"""
    
    @pytest.fixture
    def temp_workspace(self, test_soul_content):
        """创建临时工作目录"""
        temp_dir = tempfile.mkdtemp()
        soul_path = os.path.join(temp_dir, "SOUL.md")
        
        with open(soul_path, 'w', encoding='utf-8') as f:
            f.write(test_soul_content)
        
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_soul_injector_load(self, temp_workspace):
        """测试 SOUL 加载"""
        injector = SoulInjector(temp_workspace)
        success = injector.load()
        
        assert success is True
        assert injector.soul_content is not None
        assert injector.soul_data is not None
    
    def test_soul_parser(self, test_soul_content):
        """测试 SOUL 解析"""
        parser = SoulParser()
        data = parser.parse(test_soul_content)
        
        assert data["identity"]["name"] == "灵犀"
        assert data["identity"]["creature"] == "AI 助手"
        assert len(data["core_truths"]) > 0
        assert len(data["boundaries"]) > 0
    
    def test_build_system_prompt(self, temp_workspace):
        """测试构建系统提示词"""
        injector = SoulInjector(temp_workspace)
        injector.load()
        
        base_prompt = "你是灵犀智能助手。"
        system_prompt = injector.build_system_prompt(base_prompt)
        
        assert "灵犀" in system_prompt
        assert "AI 助手" in system_prompt
        assert "温暖、专业、幽默" in system_prompt
    
    def test_inject_messages(self, temp_workspace):
        """测试注入消息"""
        injector = SoulInjector(temp_workspace)
        injector.load()
        
        messages = [
            {"role": "user", "content": "你好"}
        ]
        
        injected = injector.inject(messages)
        
        # 应该包含系统消息
        assert len(injected) > len(messages)
        assert injected[0]["role"] == "system"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
