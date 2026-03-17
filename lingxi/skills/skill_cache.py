#!/usr/bin/env python3
"""技能缓存模块，提升技能加载和执行性能"""

import os
import hashlib
import logging
import types
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

ModuleType = types.ModuleType


class SkillCache:
    """技能缓存管理器"""
    
    def __init__(self, ttl: int = 300):
        """
        初始化缓存
        
        Args:
            ttl: 缓存过期时间（秒），默认 5 分钟
        """
        self._module_cache: Dict[str, dict] = {}  # skill_id -> {module, hash, timestamp}
        self._config_cache: Dict[str, dict] = {}  # skill_id -> {config, hash, timestamp}
        self._ttl = ttl
        self.logger = logging.getLogger(__name__)
    
    def get_module(self, skill_id: str) -> Optional[ModuleType]:
        """获取缓存的技能模块"""
        if skill_id not in self._module_cache:
            return None
        
        cache_entry = self._module_cache[skill_id]
        if self._is_expired(cache_entry['timestamp']):
            self.logger.debug(f"技能模块缓存过期：{skill_id}")
            del self._module_cache[skill_id]
            return None
        
        return cache_entry.get('module')
    
    def set_module(self, skill_id: str, module: ModuleType, file_path: str) -> None:
        """缓存技能模块"""
        file_hash = self._compute_file_hash(file_path)
        self._module_cache[skill_id] = {
            'module': module,
            'hash': file_hash,
            'timestamp': datetime.now()
        }
        self.logger.debug(f"技能模块已缓存：{skill_id}")
    
    def get_config(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """获取缓存的技能配置"""
        if skill_id not in self._config_cache:
            return None
        
        cache_entry = self._config_cache[skill_id]
        if self._is_expired(cache_entry['timestamp']):
            self.logger.debug(f"技能配置缓存过期：{skill_id}")
            del self._config_cache[skill_id]
            return None
        
        return cache_entry.get('config')
    
    def set_config(self, skill_id: str, config: Dict[str, Any], file_path: str) -> None:
        """缓存技能配置"""
        file_hash = self._compute_file_hash(file_path)
        self._config_cache[skill_id] = {
            'config': config,
            'hash': file_hash,
            'timestamp': datetime.now()
        }
        self.logger.debug(f"技能配置已缓存：{skill_id}")
    
    def invalidate(self, skill_id: str) -> None:
        """使缓存失效"""
        if skill_id in self._module_cache:
            del self._module_cache[skill_id]
            self.logger.debug(f"技能模块缓存已失效：{skill_id}")
        
        if skill_id in self._config_cache:
            del self._config_cache[skill_id]
            self.logger.debug(f"技能配置缓存已失效：{skill_id}")
    
    def invalidate_all(self) -> None:
        """清空所有缓存"""
        count = len(self._module_cache) + len(self._config_cache)
        self._module_cache.clear()
        self._config_cache.clear()
        self.logger.info(f"所有技能缓存已清空，共 {count} 个条目")
    
    def _is_expired(self, timestamp: datetime) -> bool:
        """检查是否过期"""
        return datetime.now() - timestamp > timedelta(seconds=self._ttl)
    
    def _compute_file_hash(self, file_path: str) -> str:
        """计算文件哈希"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return hashlib.md5(content).hexdigest()
        except Exception:
            return ""
    
    def check_file_changed(self, skill_id: str, file_path: str) -> bool:
        """检查文件是否发生变化"""
        current_hash = self._compute_file_hash(file_path)
        
        # 检查模块缓存
        if skill_id in self._module_cache:
            cached_hash = self._module_cache[skill_id]['hash']
            if cached_hash != current_hash:
                return True
        
        # 检查配置缓存
        if skill_id in self._config_cache:
            cached_hash = self._config_cache[skill_id]['hash']
            if cached_hash != current_hash:
                return True
        
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            'module_cache_size': len(self._module_cache),
            'config_cache_size': len(self._config_cache),
            'ttl_seconds': self._ttl,
            'modules': list(self._module_cache.keys()),
            'configs': list(self._config_cache.keys())
        }
