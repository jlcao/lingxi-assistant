#!/usr/bin/env python3
"""技能注册表（纯内存版本）"""

import os
import json
import logging
import yaml
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

        # 技能配置文件路径（存储启用/禁用状态）
        self.config_path = config.get("skills", {}).get("config_path", "data/skills_config.json")

        # 技能缓存
        self.skill_cache: Dict[str, Dict[str, Any]] = {}

        # 加载技能配置
        #self._load_config()

        self.logger.debug(f"初始化技能注册表（纯内存版本）: {self.config_path}")
        
        self._initialized = True 

    def _load_config(self):
        """加载技能配置文件"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.skill_cache = config.get("skills", {})
                self.logger.debug(f"加载技能配置: {len(self.skill_cache)} 个技能")
            except Exception as e:
                self.logger.error(f"加载技能配置失败: {e}")
                self.skill_cache = {}
        else:
            self.skill_cache = {}

    def _save_config(self):
        """保存技能配置文件"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump({"skills": self.skill_cache}, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"保存技能配置失败: {e}")

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

            self._save_config()
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
                self._save_config()
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
                self._save_config()
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
                    "skill_id": s["skill_id"],
                    "skill_name": s["skill_name"],
                    "name": s["skill_name"],
                    "description": s["description"],
                    "version": s["version"],
                    "author": s["author"],
                    "enabled": s["enabled"]
                }
                for s in self.skill_cache.values()
                if s.get("enabled", True)
            ]
        else:
            return [
                {
                    "skill_id": s["skill_id"],
                    "skill_name": s["skill_name"],
                    "name": s["skill_name"],
                    "description": s["description"],
                    "version": s["version"],
                    "author": s["author"],
                    "enabled": s["enabled"]
                }
                for s in self.skill_cache.values()
            ]
