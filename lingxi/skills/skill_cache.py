#!/usr/bin/env python3
"""技能缓存模块，提升技能加载和执行性能"""

import os
import hashlib
import logging
import types
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from pathlib import Path

ModuleType = types.ModuleType


class FileCacheEntry:
    """单个文件的缓存条目"""
    
    def __init__(self, content: str, file_hash: str, timestamp: datetime):
        self.content = content
        self.hash = file_hash
        self.timestamp = timestamp
        self.file_size = len(content)
    
    def is_expired(self, ttl: int) -> bool:
        return datetime.now() - self.timestamp > timedelta(seconds=ttl)


class SkillFileCache:
    """单个技能的所有文件缓存"""
    
    def __init__(self, skill_id: str, skill_dir: str):
        self.skill_id = skill_id
        self.skill_dir = skill_dir
        self.files: Dict[str, FileCacheEntry] = {}
        self.last_scan_time: Optional[datetime] = None
        self.total_files = 0
        self.total_size = 0
    
    def add_file(self, relative_path: str, content: str, file_hash: str) -> None:
        entry = FileCacheEntry(content, file_hash, datetime.now())
        self.files[relative_path] = entry
        self.total_files += 1
        self.total_size += entry.file_size
    
    def get_file(self, relative_path: str) -> Optional[FileCacheEntry]:
        return self.files.get(relative_path)
    
    def has_file(self, relative_path: str) -> bool:
        return relative_path in self.files
    
    def list_files(self) -> List[str]:
        return list(self.files.keys())
    
    def get_file_count(self) -> int:
        return self.total_files
    
    def get_total_size(self) -> int:
        return self.total_size
    
    def clear(self) -> None:
        self.files.clear()
        self.total_files = 0
        self.total_size = 0


class SkillCache:
    """技能缓存管理器"""
    
    def __init__(self, ttl: int = 300):
        """
        初始化缓存
        
        Args:
            ttl: 缓存过期时间（秒），默认 5 分钟
        """
        self._module_cache: Dict[str, dict] = {}
        self._config_cache: Dict[str, dict] = {}
        self._md_content_cache: Dict[str, dict] = {}
        self._file_cache: Dict[str, SkillFileCache] = {}
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
    
    def get_md_content(self, skill_id: str) -> Optional[str]:
        """获取缓存的 SKILL.md 内容
        
        Args:
            skill_id: 技能ID
            
        Returns:
            SKILL.md 文件内容，如果缓存不存在或过期返回 None
        """
        if skill_id not in self._md_content_cache:
            return None
        
        cache_entry = self._md_content_cache[skill_id]
        if self._is_expired(cache_entry['timestamp']):
            self.logger.debug(f"SKILL.md 内容缓存过期：{skill_id}")
            del self._md_content_cache[skill_id]
            return None
        
        return cache_entry.get('content')
    
    def set_md_content(self, skill_id: str, md_content: str, file_path: str) -> None:
        """缓存 SKILL.md 内容
        
        Args:
            skill_id: 技能ID
            md_content: SKILL.md 文件内容
            file_path: SKILL.md 文件路径（用于计算哈希）
        """
        file_hash = self._compute_file_hash(file_path)
        self._md_content_cache[skill_id] = {
            'content': md_content,
            'hash': file_hash,
            'timestamp': datetime.now()
        }
        self.logger.debug(f"SKILL.md 内容已缓存：{skill_id}")
    
    def invalidate(self, skill_id: str) -> None:
        """使缓存失效"""
        if skill_id in self._module_cache:
            del self._module_cache[skill_id]
            self.logger.debug(f"技能模块缓存已失效：{skill_id}")
        
        if skill_id in self._config_cache:
            del self._config_cache[skill_id]
            self.logger.debug(f"技能配置缓存已失效：{skill_id}")
        
        if skill_id in self._md_content_cache:
            del self._md_content_cache[skill_id]
            self.logger.debug(f"SKILL.md 内容缓存已失效：{skill_id}")
        
        if skill_id in self._file_cache:
            del self._file_cache[skill_id]
            self.logger.debug(f"技能文件缓存已失效：{skill_id}")
    
    def invalidate_all(self) -> None:
        """清空所有缓存"""
        count = len(self._module_cache) + len(self._config_cache) + len(self._md_content_cache) + len(self._file_cache)
        self._module_cache.clear()
        self._config_cache.clear()
        self._md_content_cache.clear()
        self._file_cache.clear()
        self.logger.info(f"所有技能缓存已清空，共 {count} 个条目")
    
    def cache_skill_files(self, skill_id: str, skill_dir: str) -> int:
        """递归缓存技能目录下所有文件
        
        Args:
            skill_id: 技能ID
            skill_dir: 技能目录路径
            
        Returns:
            成功缓存的文件数量
        """
        if skill_id not in self._file_cache:
            self._file_cache[skill_id] = SkillFileCache(skill_id, skill_dir)
        
        skill_cache = self._file_cache[skill_id]
        skill_dir_path = Path(skill_dir)
        
        cached_count = 0
        for file_path in skill_dir_path.rglob('*'):
            if file_path.is_file() and self._should_cache_file(file_path):
                relative_path = str(file_path.relative_to(skill_dir_path))
                try:
                    content = file_path.read_text(encoding='utf-8')
                    file_hash = self._compute_content_hash(content)
                    skill_cache.add_file(relative_path, content, file_hash)
                    cached_count += 1
                    self.logger.debug(f"缓存文件: {skill_id}/{relative_path}")
                except Exception as e:
                    self.logger.warning(f"缓存文件失败 {relative_path}: {e}")
        
        skill_cache.last_scan_time = datetime.now()
        self.logger.info(f"技能 {skill_id} 已缓存 {cached_count} 个文件")
        return cached_count
    
    def get_file_content(self, skill_id: str, relative_path: str) -> Optional[str]:
        """获取缓存的文件内容
        
        Args:
            skill_id: 技能ID
            relative_path: 文件相对路径
            
        Returns:
            文件内容，如果缓存不存在或过期返回 None
        """
        if skill_id not in self._file_cache:
            return None
        
        skill_cache = self._file_cache[skill_id]
        entry = skill_cache.get_file(relative_path)
        
        if entry is None:
            return None
        
        if entry.is_expired(self._ttl):
            self.logger.debug(f"文件缓存过期: {skill_id}/{relative_path}")
            del skill_cache.files[relative_path]
            return None
        
        return entry.content
    
    def list_cached_files(self, skill_id: str) -> List[str]:
        """列出技能已缓存的所有文件
        
        Args:
            skill_id: 技能ID
            
        Returns:
            文件相对路径列表
        """
        if skill_id not in self._file_cache:
            return []
        
        return self._file_cache[skill_id].list_files()
    
    def invalidate_skill_files(self, skill_id: str) -> None:
        """使技能文件缓存失效
        
        Args:
            skill_id: 技能ID
        """
        if skill_id in self._file_cache:
            del self._file_cache[skill_id]
            self.logger.debug(f"技能文件缓存已失效: {skill_id}")
    
    def _should_cache_file(self, file_path: Path) -> bool:
        """判断文件是否应该被缓存
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否应该缓存
        """
        excluded_extensions = {'.pyc', '.so', '.dll', '.exe', '.bin'}
        if file_path.suffix in excluded_extensions:
            return False
        
        excluded_dirs = {'__pycache__', '.git', '.idea', 'node_modules'}
        for part in file_path.parts:
            if part in excluded_dirs:
                return False
        
        if file_path.name.startswith('.'):
            return False
        
        text_extensions = {
            '.md', '.txt', '.py', '.js', '.ts', '.json', 
            '.yaml', '.yml', '.xml', '.xsd', '.html', '.css'
        }
        return file_path.suffix in text_extensions or file_path.suffix == ''
    
    def _compute_content_hash(self, content: str) -> str:
        """计算内容哈希
        
        Args:
            content: 文件内容
            
        Returns:
            MD5 哈希值
        """
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        file_cache_stats = {}
        for skill_id, skill_cache in self._file_cache.items():
            file_cache_stats[skill_id] = {
                'file_count': skill_cache.get_file_count(),
                'total_size': skill_cache.get_total_size(),
                'files': skill_cache.list_files()
            }
        
        return {
            'module_cache_size': len(self._module_cache),
            'config_cache_size': len(self._config_cache),
            'md_content_cache_size': len(self._md_content_cache),
            'file_cache_size': len(self._file_cache),
            'file_cache_details': file_cache_stats,
            'ttl_seconds': self._ttl,
            'modules': list(self._module_cache.keys()),
            'configs': list(self._config_cache.keys()),
            'md_contents': list(self._md_content_cache.keys()),
            'file_cached_skills': list(self._file_cache.keys())
        }
