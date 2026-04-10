#!/usr/bin/env python3
"""技能注册表（纯内存版本）"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path


class SkillRegistry:
    """技能注册表（纯内存版本）"""
    
    _instance = None  # 单例实例
    
    def __new__(cls, config: Dict[str, Any]):
        """单例模式：确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config: Dict[str, Any]):
        """初始化技能注册表

        Args:
            config: 系统配置
        """
        self.logger = logging.getLogger(__name__)

        # 技能缓存
        self.skill_cache: Dict[str, Dict[str, Any]] = {}

        self.logger.debug("初始化技能注册表（纯内存版本）")
        
        self._initialized = True

    def register_skill(self, skill_config: Dict[str, Any]) -> bool:
        """注册技能

        Args:
            skill_config: 技能配置字典

        Returns:
            是否注册成功
        """
        skill_id = skill_config.get("skill_id")

        if not skill_id:
            self.logger.error("技能配置缺少 skill_id")
            return False

        try:
            # 如果技能已存在，保留 enabled 状态
            enabled = self.skill_cache.get(skill_id, {}).get("enabled", True)

            # 更新技能配置
            self.skill_cache[skill_id] = {
                "skill_id": skill_id,
                "skill_name": skill_config.get("skill_name", skill_id),
                "version": skill_config.get("version", "1.0.0"),
                "type": skill_config.get("type", "local"),
                "description": skill_config.get("description", ""),
                "author": skill_config.get("author", ""),
                "enabled": enabled,
                "config": skill_config  # 保存完整配置
            }

            self.logger.debug(f"注册技能: {skill_id}")
            return True

        except Exception as e:
            self.logger.error(f"注册技能失败 {skill_id}: {e}")
            return False

    def unregister_skill(self, name: str) -> bool:
        """注销技能

        Args:
            name: 技能名称

        Returns:
            是否注销成功
        """
        try:
            if name in self.skill_cache:
                del self.skill_cache[name]
                self.logger.debug(f"注销技能: {name}")
                return True
            else:
                self.logger.warning(f"技能不存在: {name}")
                return False
        except Exception as e:
            self.logger.error(f"注销技能失败 {name}: {e}")
            return False

    def enable_skill(self, name: str, enabled: bool = True) -> bool:
        """启用或禁用技能

        Args:
            name: 技能名称
            enabled: 是否启用

        Returns:
            是否操作成功
        """
        try:
            if name in self.skill_cache:
                self.skill_cache[name]["enabled"] = enabled
                self.logger.debug(f"{'启用' if enabled else '禁用'}技能: {name}")
                return True
            else:
                self.logger.warning(f"技能不存在: {name}")
                return False
        except Exception as e:
            self.logger.error(f"{'启用' if enabled else '禁用'}技能失败 {name}: {e}")
            return False

    def get_skill(self, name: str) -> Optional[Dict[str, Any]]:
        """获取技能信息

        Args:
            name: 技能名称

        Returns:
            技能信息字典
        """
        return self.skill_cache.get(name)

    def list_skills(self, enabled_only: bool = True) -> List[Dict[str, Any]]:
        """列出所有技能

        Args:
            enabled_only: 是否只列出启用的技能

        Returns:
            技能列表
        """
        if enabled_only:
            return [
                {
                    "skill_id": s.get("skill_id", s.get("name", "")),
                    "skill_name": s.get("skill_name", s.get("name", "")),
                    "name": s.get("skill_name", s.get("name", "")),
                    "description": s.get("description", ""),
                    "version": s.get("version", "1.0.0"),
                    "author": s.get("author", ""),
                    "enabled": s.get("enabled", True),
                    "source": s.get("source", "global")
                }
                for s in self.skill_cache.values()
                if s.get("enabled", True)
            ]
        else:
            return [
                {
                    "skill_id": s.get("skill_id", s.get("name", "")),
                    "skill_name": s.get("skill_name", s.get("name", "")),
                    "name": s.get("skill_name", s.get("name", "")),
                    "description": s.get("description", ""),
                    "version": s.get("version", "1.0.0"),
                    "author": s.get("author", ""),
                    "enabled": s.get("enabled", True),
                    "source": s.get("source", "global")
                }
                for s in self.skill_cache.values()
            ]
    
    def register_skill_from_dir(self, skill_dir: Path, source: str = "global"):
        """从目录注册技能（纯存储，不加载模块）
        
        Args:
            skill_dir: 技能目录
            source: 技能来源（global/workspace）
        """
        skill_info = {
            "name": skill_dir.name,
            "skill_id": skill_dir.name,
            "description": f"技能：{skill_dir.name}",
            "source": source,
            "path": str(skill_dir),
            "enabled": True,
            "version": "1.0.0",
            "author": ""
        }
        self.skill_cache[skill_dir.name] = skill_info
        self.logger.info(f"注册技能：{skill_dir.name} (source={source})")
    
    def unregister_workspace_skills(self):
        """注销工作目录级别的技能"""
        workspace_skills = [
            name for name, info in self.skill_cache.items()
            if info.get("source") == "workspace"
        ]
        
        for skill_name in workspace_skills:
            del self.skill_cache[skill_name]
            self.logger.debug(f"已注销工作目录技能：{skill_name}")
