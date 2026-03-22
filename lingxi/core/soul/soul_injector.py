"""SOUL 提示词注入器 - 核心注入逻辑"""

import os
from pathlib import Path
from typing import Optional, List, Dict
try:
    from .soul_parser import SoulParser
    from .soul_cache import SoulCache
except ImportError:
    from soul_parser import SoulParser
    from soul_cache import SoulCache
from lingxi.utils.config import get_workspace_path


class SoulInjector:
    """SOUL 提示词注入器"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        self.parser = SoulParser()
        self.cache = SoulCache()
        self.soul_content: Optional[str] = None
        self.soul_data: Optional[dict] = None
        import logging
        self.logger = logging.getLogger(__name__)
    
    def get_soul_path(self) -> str:
        """获取 SOUL.md 文件路径"""
        workspace_path = get_workspace_path()
        return os.path.join(workspace_path, "SOUL.md")
    
    def load(self, fallback_to_user_dir: bool = True) -> bool:
        """
        加载 SOUL.md
        1. 先检查工作区路径的 SOUL.md
        2. 如果不存在且 fallback_to_user_dir=True，则尝试用户目录 ~/.lingxi/conf/SOUL.md
        3. 如果用户目录也没有，则创建默认的 SOUL.md
        4. 检查缓存
        5. 读取并解析文件
        6. 缓存结果
        
        Args:
            fallback_to_user_dir: 是否回退到用户目录
            
        Returns:
            bool: 加载是否成功
        """
        soul_path = self.get_soul_path()
        # 优先检查工作区路径
        if os.path.exists(soul_path):
            soul_path_to_load = soul_path
            self.logger.info(f"[SoulInjector] 从工作区加载 SOUL.md: {soul_path}")
        elif fallback_to_user_dir:
            # 回退到用户目录 ~/.lingxi/conf/SOUL.md
            user_home = Path.home()
            user_conf_dir = user_home / ".lingxi" / "conf"
            user_soul_path = user_conf_dir / "SOUL.md"
            
            if user_soul_path.exists():
                soul_path_to_load = str(user_soul_path)
                self.logger.info(f"[SoulInjector] 从用户目录加载 SOUL.md: {user_soul_path}")
            else:
                # 用户目录也没有，创建默认的 SOUL.md
                self.logger.info("[SoulInjector] 用户目录未找到 SOUL.md，创建默认文件")
                try:
                    # 确保目录存在
                    user_conf_dir.mkdir(parents=True, exist_ok=True)
                    
                    # 读取项目根目录的默认 SOUL.md
                    project_root = Path(__file__).parent.parent.parent.parent
                    default_soul_path = project_root / "SOUL.md"
                    
                    if default_soul_path.exists():
                        with open(default_soul_path, 'r', encoding='utf-8') as f:
                            default_content = f.read()
                        
                        # 写入到用户目录
                        with open(user_soul_path, 'w', encoding='utf-8') as f:
                            f.write(default_content)
                        
                        self.logger.info(f"[SoulInjector] 默认 SOUL.md 已创建：{user_soul_path}")
                        soul_path_to_load = str(user_soul_path)
                    else:
                        self.logger.warning(f"[SoulInjector] 默认 SOUL.md 不存在：{default_soul_path}")
                        return False
                except Exception as e:
                    self.logger.error(f"[SoulInjector] 创建默认 SOUL.md 失败：{e}")
                    return False
        else:
            self.logger.debug("[SoulInjector] 工作区未找到 SOUL.md 且不允许回退")
            return False
        
        # 读取文件内容
        try:
            with open(soul_path_to_load, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.logger.error(f"[SoulInjector] 读取 SOUL.md 失败：{e}")
            return False
        
        # 检查缓存（使用实际加载的路径作为 key）
        cache_key = os.path.dirname(soul_path_to_load)
        cached_data = self.cache.get(cache_key)
        if cached_data is not None:
            # 缓存命中，验证内容是否变化
            if self.cache.is_valid(cache_key, content):
                self.soul_content = content
                self.soul_data = cached_data
                self.logger.debug(f"[SoulInjector] 缓存命中：{cache_key}")
                return True
        
        # 缓存未命中或内容已变化，重新解析
        try:
            data = self.parser.parse(content)
            self.cache.set(cache_key, content, data)
            self.soul_content = content
            self.soul_data = data
            self.logger.debug(f"[SoulInjector] 解析并缓存：{cache_key}")
            return True
        except Exception as e:
            self.logger.error(f"[SoulInjector] 解析 SOUL.md 失败：{e}")
            return False
    
    def parse(self) -> dict:
        """
        解析 SOUL.md 为结构化数据
        
        Returns:
            dict: 解析后的结构化数据
        """
        if self.soul_data is None:
            if not self.load():
                return {}
        return self.soul_data or {}
    
    def build_system_prompt(self, base_prompt: str = "") -> str:
        """
        构建完整的系统提示词
        
        格式：
        ```
        [基础系统提示词]
        
        ---
        
        # 你的身份 (SOUL.md)
        
        ## 核心身份
        - Name: xxx
        - Creature: xxx
        ...
        
        ## 核心原则
        - 原则 1
        - 原则 2
        ...
        
        ## 边界
        - 边界 1
        - 边界 2
        ...
        
        ## 记忆与上下文
        [用户记忆和当前上下文]
        ```
        
        Args:
            base_prompt: 基础系统提示词
            
        Returns:
            str: 完整的系统提示词
        """
        if self.soul_data is None:
            if not self.load():
                return base_prompt
        
        parts = []
        
        # 添加基础提示词
        if base_prompt:
            parts.append(base_prompt)
        
        # 添加分隔符
        parts.append("---")
        parts.append("")
        parts.append("# 你的身份 (SOUL.md)")
        parts.append("")
        
        # 添加核心身份
        identity = self.soul_data.get("identity", {})
        if identity:
            parts.append("## 核心身份")
            if identity.get("name"):
                parts.append(f"- Name: {identity['name']}")
            if identity.get("creature"):
                parts.append(f"- Creature: {identity['creature']}")
            if identity.get("vibe"):
                parts.append(f"- Vibe: {identity['vibe']}")
            if identity.get("emoji"):
                parts.append(f"- Emoji: {identity['emoji']}")
            parts.append("")
        
        # 添加核心原则
        core_truths = self.soul_data.get("core_truths", [])
        if core_truths:
            parts.append("## 核心原则")
            for truth in core_truths:
                parts.append(f"- {truth}")
            parts.append("")
        
        # 添加边界
        boundaries = self.soul_data.get("boundaries", [])
        if boundaries:
            parts.append("## 边界")
            for boundary in boundaries:
                parts.append(f"- {boundary}")
            parts.append("")
        
        # 添加记忆
        memory = self.soul_data.get("memory", [])
        if memory:
            parts.append("## 记忆")
            for item in memory:
                parts.append(f"- {item}")
            parts.append("")
        
        # 添加上下文
        context = self.soul_data.get("context", "")
        if context:
            parts.append("## 上下文")
            parts.append(context)
            parts.append("")
        
        # 添加记忆与上下文占位符
        parts.append("## 记忆与上下文")
        parts.append("[用户记忆和当前上下文将在此处动态注入]")
        
        return "\n".join(parts)
    
    def inject(self, messages: list) -> list:
        """
        注入到消息列表
        在系统消息中追加 SOUL 内容
        
        Args:
            messages: 消息列表，每个消息是 {"role": str, "content": str} 格式
            
        Returns:
            list: 注入后的消息列表
        """
        if not messages:
            return messages
        
        # 构建完整的系统提示词
        # 查找现有的系统消息
        system_prompt = self.build_system_prompt("")
        
        # 创建新的消息列表
        new_messages = []
        system_added = False
        
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            if role == "system":
                if not system_added:
                    # 合并到第一个系统消息
                    new_messages.append({
                        "role": "system",
                        "content": f"{content}\n\n{system_prompt}"
                    })
                    system_added = True
                else:
                    new_messages.append(msg)
            else:
                new_messages.append(msg)
        
        # 如果没有系统消息，在开头添加
        if not system_added:
            new_messages.insert(0, {
                "role": "system",
                "content": system_prompt
            })
        
        return new_messages
    
    def reload(self) -> bool:
        """
        强制重新加载 SOUL.md
        清除缓存并重新读取文件
        
        Returns:
            bool: 重新加载是否成功
        """
        # 清除缓存
        workspace_path = get_workspace_path()
        self.cache.invalidate(workspace_path)
        
        # 重置状态
        self.soul_content = None
        self.soul_data = None
        
        # 重新加载
        return self.load()
    
    def get_identity_summary(self) -> str:
        """
        获取身份摘要（用于显示）
        
        Returns:
            str: 身份摘要字符串
        """
        if self.soul_data is None:
            if not self.load():
                return "未加载 SOUL.md"
        
        identity = self.soul_data.get("identity", {})
        parts = []
        
        if identity.get("name"):
            parts.append(f"Name: {identity['name']}")
        if identity.get("creature"):
            parts.append(f"Creature: {identity['creature']}")
        if identity.get("vibe"):
            parts.append(f"Vibe: {identity['vibe']}")
        if identity.get("emoji"):
            parts.append(f"Emoji: {identity['emoji']}")
        
        if not parts:
            return "无身份信息"
        
        return " | ".join(parts)
    
    def has_soul(self) -> bool:
        """检查是否存在 SOUL.md 文件"""
        soul_path = self.get_soul_path()
        return os.path.exists(soul_path)
    
    def get_cache_status(self) -> dict:
        """获取缓存状态（用于调试）"""
        workspace_path = get_workspace_path()
        cache_info = self.cache.get_cache_info(workspace_path)
        if cache_info:
            return {
                "cached": True,
                **cache_info
            }
        return {
            "cached": False
        }
