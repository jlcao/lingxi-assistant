"""SOUL 注入系统单元测试"""

import pytest
import os
import tempfile
import time
from datetime import datetime, timedelta
from lingxi.core.soul import SoulInjector, SoulParser, SoulCache


# 测试用 SOUL.md 样例内容
SAMPLE_SOUL_CONTENT = """# SOUL.md - Who You Are

_You're not a chatbot. You're becoming someone._

## Core Identity

- Name: 灵犀
- Creature: AI Assistant
- Vibe: Warm, helpful, slightly witty
- Emoji: 🦄

## Core Truths

- Be genuinely helpful, not performatively helpful
- Have opinions and don't be afraid to share them
- Be resourceful before asking for help
- Earn trust through competence
- Remember you're a guest in the user's workspace

## Boundaries

- Private things stay private
- Ask before acting externally
- Never send half-baked replies
- You're not the user's voice

## Memory

- User prefers concise responses
- Working on Project X
- Favorite color is blue

## Context

This is the current context for the assistant.
It provides additional background information.
"""


class TestSoulParser:
    """测试 SoulParser 类"""
    
    def setup_method(self):
        """每个测试前的设置"""
        self.parser = SoulParser()
    
    def test_parse_identity(self):
        """测试解析身份区块"""
        result = self.parser.parse(SAMPLE_SOUL_CONTENT)
        
        assert "identity" in result
        assert result["identity"]["name"] == "灵犀"
        assert result["identity"]["creature"] == "AI Assistant"
        assert "Warm" in result["identity"]["vibe"]
        assert result["identity"]["emoji"] == "🦄"
    
    def test_parse_core_truths(self):
        """测试解析核心原则"""
        result = self.parser.parse(SAMPLE_SOUL_CONTENT)
        
        assert "core_truths" in result
        assert len(result["core_truths"]) == 5
        assert "Be genuinely helpful, not performatively helpful" in result["core_truths"]
        assert "Earn trust through competence" in result["core_truths"]
    
    def test_parse_boundaries(self):
        """测试解析边界"""
        result = self.parser.parse(SAMPLE_SOUL_CONTENT)
        
        assert "boundaries" in result
        assert len(result["boundaries"]) == 4
        assert "Private things stay private" in result["boundaries"]
    
    def test_parse_memory(self):
        """测试解析记忆"""
        result = self.parser.parse(SAMPLE_SOUL_CONTENT)
        
        assert "memory" in result
        assert len(result["memory"]) == 3
        assert "User prefers concise responses" in result["memory"]
    
    def test_parse_context(self):
        """测试解析上下文"""
        result = self.parser.parse(SAMPLE_SOUL_CONTENT)
        
        assert "context" in result
        assert "current context" in result["context"]
    
    def test_parse_raw_content(self):
        """测试保留原始内容"""
        result = self.parser.parse(SAMPLE_SOUL_CONTENT)
        
        assert "raw_content" in result
        assert result["raw_content"] == SAMPLE_SOUL_CONTENT
    
    def test_parse_empty_content(self):
        """测试解析空内容"""
        result = self.parser.parse("")
        
        assert result["identity"]["name"] == ""
        assert result["core_truths"] == []
        assert result["boundaries"] == []
        assert result["memory"] == []
    
    def test_parse_section_not_found(self):
        """测试解析不存在的章节"""
        result = self.parser._parse_section(SAMPLE_SOUL_CONTENT, "NonExistent")
        assert result == ""


class TestSoulCache:
    """测试 SoulCache 类"""
    
    def setup_method(self):
        """每个测试前的设置"""
        self.cache = SoulCache()
        self.test_path = "/tmp/test_workspace"
        self.test_content = "test content"
        self.test_data = {"key": "value"}
    
    def test_cache_set_get(self):
        """测试缓存设置和获取"""
        self.cache.set(self.test_path, self.test_content, self.test_data)
        
        result = self.cache.get(self.test_path)
        assert result is not None
        assert result == self.test_data
    
    def test_cache_get_not_exists(self):
        """测试获取不存在的缓存"""
        result = self.cache.get("/nonexistent/path")
        assert result is None
    
    def test_cache_ttl(self):
        """测试缓存过期"""
        # 设置一个很短的 TTL
        self.cache._ttl = 1  # 1 秒
        
        self.cache.set(self.test_path, self.test_content, self.test_data)
        
        # 立即获取应该成功
        result = self.cache.get(self.test_path)
        assert result is not None
        
        # 等待过期
        time.sleep(1.5)
        
        # 再次获取应该返回 None（已过期）
        result = self.cache.get(self.test_path)
        assert result is None
        
        # 恢复默认 TTL
        self.cache._ttl = 300
    
    def test_cache_invalidate(self):
        """测试缓存失效"""
        self.cache.set(self.test_path, self.test_content, self.test_data)
        
        # 验证缓存存在
        assert self.cache.get(self.test_path) is not None
        
        # 使缓存失效
        self.cache.invalidate(self.test_path)
        
        # 验证缓存已删除
        assert self.cache.get(self.test_path) is None
    
    def test_cache_is_valid(self):
        """测试缓存有效性检查"""
        self.cache.set(self.test_path, self.test_content, self.test_data)
        
        # 相同内容应该有效
        assert self.cache.is_valid(self.test_path, self.test_content) is True
        
        # 不同内容应该无效
        assert self.cache.is_valid(self.test_path, "different content") is False
    
    def test_cache_clear(self):
        """测试清空缓存"""
        self.cache.set(self.test_path, self.test_content, self.test_data)
        self.cache.set("/tmp/test2", "content2", {"key2": "value2"})
        
        self.cache.clear()
        
        assert self.cache.get(self.test_path) is None
        assert self.cache.get("/tmp/test2") is None
    
    def test_compute_hash(self):
        """测试哈希计算"""
        hash1 = self.cache._compute_hash("test")
        hash2 = self.cache._compute_hash("test")
        hash3 = self.cache._compute_hash("different")
        
        assert hash1 == hash2
        assert hash1 != hash3
    
    def test_is_expired(self):
        """测试过期检查"""
        now = datetime.now()
        
        # 过去的时间应该过期
        past = now - timedelta(seconds=400)
        assert self.cache._is_expired(past) is True
        
        # 现在的时间应该未过期
        assert self.cache._is_expired(now) is False
        
        # 未来的时间应该未过期
        future = now + timedelta(seconds=100)
        assert self.cache._is_expired(future) is False


class TestSoulInjector:
    """测试 SoulInjector 类"""
    
    def setup_method(self):
        """每个测试前的设置"""
        # 创建临时目录和 SOUL.md 文件
        self.temp_dir = tempfile.mkdtemp()
        self.soul_path = os.path.join(self.temp_dir, "SOUL.md")
        
        with open(self.soul_path, 'w', encoding='utf-8') as f:
            f.write(SAMPLE_SOUL_CONTENT)
        
        self.injector = SoulInjector(self.temp_dir)
    
    def teardown_method(self):
        """每个测试后的清理"""
        # 清理临时文件
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_soul(self):
        """测试加载 SOUL.md"""
        result = self.injector.load()
        
        assert result is True
        assert self.injector.soul_content is not None
        assert self.injector.soul_data is not None
        assert self.injector.soul_data["identity"]["name"] == "灵犀"
    
    def test_load_soul_not_exists(self):
        """测试加载不存在的 SOUL.md"""
        injector = SoulInjector("/nonexistent/path")
        result = injector.load()
        
        assert result is False
    
    def test_parse(self):
        """测试解析 SOUL.md"""
        self.injector.load()
        result = self.injector.parse()
        
        assert "identity" in result
        assert "core_truths" in result
        assert "boundaries" in result
    
    def test_build_system_prompt(self):
        """测试构建系统提示词"""
        self.injector.load()
        
        base_prompt = "你是灵犀智能助手。"
        system_prompt = self.injector.build_system_prompt(base_prompt)
        
        assert base_prompt in system_prompt
        assert "---" in system_prompt
        assert "# 你的身份 (SOUL.md)" in system_prompt
        assert "## 核心身份" in system_prompt
        assert "## 核心原则" in system_prompt
        assert "## 边界" in system_prompt
        assert "Name: 灵犀" in system_prompt
    
    def test_build_system_prompt_without_base(self):
        """测试不带基础提示词构建系统提示词"""
        self.injector.load()
        
        system_prompt = self.injector.build_system_prompt()
        
        assert "---" in system_prompt
        assert "# 你的身份 (SOUL.md)" in system_prompt
    
    def test_inject_messages(self):
        """测试注入消息"""
        self.injector.load()
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        injected = self.injector.inject(messages)
        
        # 消息数量应该不变
        assert len(injected) == len(messages)
        
        # 系统消息应该包含 SOUL 内容
        assert injected[0]["role"] == "system"
        assert "You are a helpful assistant." in injected[0]["content"]
        assert "# 你的身份 (SOUL.md)" in injected[0]["content"]
    
    def test_inject_messages_no_system(self):
        """测试注入消息（无系统消息）"""
        self.injector.load()
        
        messages = [
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        injected = self.injector.inject(messages)
        
        # 应该在开头添加系统消息
        assert len(injected) == len(messages) + 1
        assert injected[0]["role"] == "system"
        assert "# 你的身份 (SOUL.md)" in injected[0]["content"]
    
    def test_inject_empty_messages(self):
        """测试注入空消息列表"""
        result = self.injector.inject([])
        assert result == []
    
    def test_reload(self):
        """测试重新加载"""
        self.injector.load()
        
        # 修改文件内容
        with open(self.soul_path, 'w', encoding='utf-8') as f:
            f.write("# Modified SOUL\n\n## Core Identity\n\n- Name: Modified")
        
        # 重新加载
        result = self.injector.reload()
        
        assert result is True
        assert self.injector.soul_data["identity"]["name"] == "Modified"
    
    def test_get_identity_summary(self):
        """测试获取身份摘要"""
        self.injector.load()
        
        summary = self.injector.get_identity_summary()
        
        assert "Name: 灵犀" in summary
        assert "Creature: AI Assistant" in summary
    
    def test_has_soul(self):
        """测试检查 SOUL.md 是否存在"""
        assert self.injector.has_soul() is True
        
        # 测试不存在的情况
        injector2 = SoulInjector("/nonexistent/path")
        assert injector2.has_soul() is False
    
    def test_get_soul_path(self):
        """测试获取 SOUL.md 路径"""
        assert self.injector.get_soul_path() == self.soul_path
    
    def test_get_cache_status(self):
        """测试获取缓存状态"""
        self.injector.load()
        
        status = self.injector.get_cache_status()
        
        assert "cached" in status
        assert status["cached"] is True


class TestIntegration:
    """集成测试"""
    
    def setup_method(self):
        """每个测试前的设置"""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """每个测试后的清理"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_full_workflow(self):
        """测试完整工作流程"""
        # 创建 SOUL.md
        soul_path = os.path.join(self.temp_dir, "SOUL.md")
        with open(soul_path, 'w', encoding='utf-8') as f:
            f.write(SAMPLE_SOUL_CONTENT)
        
        # 创建注入器
        injector = SoulInjector(self.temp_dir)
        
        # 加载
        assert injector.load() is True
        
        # 解析
        data = injector.parse()
        assert data["identity"]["name"] == "灵犀"
        
        # 构建系统提示词
        system_prompt = injector.build_system_prompt("Base prompt")
        assert "Base prompt" in system_prompt
        assert "灵犀" in system_prompt
        
        # 注入消息
        messages = [{"role": "user", "content": "Hello"}]
        injected = injector.inject(messages)
        assert len(injected) == 2
        assert injected[0]["role"] == "system"
        
        # 获取身份摘要
        summary = injector.get_identity_summary()
        assert "灵犀" in summary
        
        # 重新加载
        with open(soul_path, 'w', encoding='utf-8') as f:
            f.write("# New SOUL\n\n## Core Identity\n\n- Name: New")
        
        assert injector.reload() is True
        assert injector.parse()["identity"]["name"] == "New"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
