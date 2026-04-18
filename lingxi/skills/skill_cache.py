#!/usr/bin/env python3
"""技能缓存模块，提升技能加载和执行性能"""

import os
import hashlib
import logging
import types
import sys
import gc
import weakref
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from pathlib import Path
from collections import OrderedDict

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
    """技能缓存管理器（支持 LRU + TTL 自动回收）"""
    
    def __init__(self, ttl: int = 300, max_size: int = 100):
        """
        初始化缓存
        
        Args:
            ttl: 缓存过期时间（秒），默认 5 分钟
            max_size: 最大缓存数量（LRU 限制），默认 100
        """
        self._module_cache: OrderedDict[str, dict] = OrderedDict()
        self._config_cache: OrderedDict[str, dict] = OrderedDict()
        self._md_content_cache: OrderedDict[str, dict] = OrderedDict()
        self._file_cache: OrderedDict[str, SkillFileCache] = OrderedDict()
        self._mcp_skills_cache: OrderedDict[str, dict] = OrderedDict()
        self._module_names: Dict[str, List[str]] = {}
        self._ttl = ttl
        self._max_size = max_size
        self.logger = logging.getLogger(__name__)
    
    def get_module(self, skill_id: str) -> Optional[ModuleType]:
        """获取缓存的技能模块（支持 LRU 更新访问时间）"""
        if skill_id not in self._module_cache:
            return None
        
        cache_entry = self._module_cache[skill_id]
        if self._is_expired(cache_entry['timestamp']):
            self.logger.debug(f"技能模块缓存过期：{skill_id}")
            self._remove_module(skill_id)
            return None
        
        self._module_cache.move_to_end(skill_id)
        return cache_entry.get('module')
    
    def set_module(self, skill_id: str, module: Any, file_path: str) -> None:
        """缓存技能模块（支持 LRU 淘汰）
        
        Args:
            skill_id: 技能ID
            module: 模块对象或外部执行模式字典
            file_path: 文件路径
        """
        if skill_id in self._module_cache:
            self._remove_module(skill_id)
        
        if len(self._module_cache) >= self._max_size:
            oldest_skill_id = next(iter(self._module_cache))
            self.logger.debug(f"LRU 淘汰最旧的缓存：{oldest_skill_id}")
            self._remove_module(oldest_skill_id)
        
        cache_entry = {
            'module': module,
            'timestamp': datetime.now()
        }
        
        if isinstance(module, ModuleType):
            cache_entry['hash'] = self._compute_file_hash(file_path)
            cache_entry['type'] = 'module'
            module_names = self._extract_module_names(module)
            self._module_names[skill_id] = module_names
        else:
            cache_entry['type'] = 'external'
        
        self._module_cache[skill_id] = cache_entry
        self.logger.debug(f"技能模块已缓存：{skill_id}")
    
    def get_config(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """获取缓存的技能配置（支持 LRU 更新访问时间）"""
        if skill_id not in self._config_cache:
            return None
        
        cache_entry = self._config_cache[skill_id]
        if self._is_expired(cache_entry['timestamp']):
            self.logger.debug(f"技能配置缓存过期：{skill_id}")
            del self._config_cache[skill_id]
            return None
        
        self._config_cache.move_to_end(skill_id)
        return cache_entry.get('config')
    
    def set_config(self, skill_id: str, config: Dict[str, Any], file_path: str) -> None:
        """缓存技能配置（支持 LRU 淘汰）"""
        if skill_id in self._config_cache:
            del self._config_cache[skill_id]
        
        if len(self._config_cache) >= self._max_size:
            oldest_skill_id = next(iter(self._config_cache))
            self.logger.debug(f"LRU 淘汰最旧的配置缓存：{oldest_skill_id}")
            del self._config_cache[oldest_skill_id]
        
        file_hash = self._compute_file_hash(file_path)
        self._config_cache[skill_id] = {
            'config': config,
            'hash': file_hash,
            'timestamp': datetime.now()
        }
        self.logger.debug(f"技能配置已缓存：{skill_id}")
    

    
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
    
    def get_mcp_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """获取 MCP 技能配置
        
        Args:
            skill_id: 技能ID
            
        Returns:
            MCP 技能配置，如果缓存不存在或过期返回 None
        """
        if skill_id not in self._mcp_skills_cache:
            return None
        
        cache_entry = self._mcp_skills_cache[skill_id]
        if self._is_expired(cache_entry['timestamp']):
            self.logger.debug(f"MCP 技能缓存过期：{skill_id}")
            del self._mcp_skills_cache[skill_id]
            return None
        
        self._mcp_skills_cache.move_to_end(skill_id)
        return cache_entry.get('config')
    
    def set_mcp_skill(self, skill_id: str, config: Dict[str, Any]) -> None:
        """缓存 MCP 技能配置
        
        Args:
            skill_id: 技能ID
            config: MCP 技能配置
        """
        if skill_id in self._mcp_skills_cache:
            del self._mcp_skills_cache[skill_id]
        
        if len(self._mcp_skills_cache) >= self._max_size:
            oldest_skill_id = next(iter(self._mcp_skills_cache))
            self.logger.debug(f"LRU 淘汰最旧的 MCP 技能缓存：{oldest_skill_id}")
            del self._mcp_skills_cache[oldest_skill_id]
        
        self._mcp_skills_cache[skill_id] = {
            'config': config,
            'timestamp': datetime.now()
        }
        self.logger.debug(f"MCP 技能已缓存：{skill_id}")
    
    def has_module(self, skill_id: str) -> bool:
        """检查技能模块是否已缓存
        
        Args:
            skill_id: 技能ID
            
        Returns:
            是否已缓存
        """
        return skill_id in self._module_cache
    
    def list_loaded_modules(self) -> List[str]:
        """列出所有已加载的技能ID
        
        Returns:
            技能ID列表
        """
        return list(self._module_cache.keys())
    
    def clear_modules(self) -> None:
        """清空所有已加载的模块"""
        skill_ids = list(self._module_cache.keys())
        for skill_id in skill_ids:
            self._remove_module(skill_id)
        self.logger.debug(f"已清空所有模块缓存，共 {len(skill_ids)} 个")
    
    def invalidate(self, skill_id):
        """使缓存失效（同时清理 sys.modules 和引用）"""
        if skill_id in self._module_cache:
            self._remove_module(skill_id)
        
        if skill_id in self._config_cache:
            del self._config_cache[skill_id]
            self.logger.debug(f"技能配置缓存已失效：{skill_id}")
        
        if skill_id in self._md_content_cache:
            del self._md_content_cache[skill_id]
            self.logger.debug(f"SKILL.md 内容缓存已失效：{skill_id}")
        
        if skill_id in self._mcp_skills_cache:
            del self._mcp_skills_cache[skill_id]
            self.logger.debug(f"MCP 技能缓存已失效：{skill_id}")
        
        if skill_id in self._file_cache:
            del self._file_cache[skill_id]
            self.logger.debug(f"技能文件缓存已失效：{skill_id}")
    
    def invalidate_all(self) -> None:
        """清空所有缓存"""
        count = (len(self._module_cache) + len(self._config_cache) + 
                 len(self._md_content_cache) + len(self._file_cache) +
                 len(self._mcp_skills_cache))
        self._module_cache.clear()
        self._config_cache.clear()
        self._md_content_cache.clear()
        self._file_cache.clear()
        self._mcp_skills_cache.clear()
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
                # 统一使用正斜杠作为路径分隔符
                relative_path = relative_path.replace('\\', '/')
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
        
        # 统一使用正斜杠作为路径分隔符
        relative_path = relative_path.replace('\\', '/')
        
        skill_cache = self._file_cache[skill_id]
        entry = skill_cache.get_file(relative_path)
        
        if entry is None:
            return None
        
        if entry.is_expired(self._ttl):
            self.logger.debug(f"文件缓存过期: {skill_id}/{relative_path},重新加载")
            self.cache_skill_files(skill_id, skill_cache.skill_dir)
            # 重新获取缓存条目
            entry = skill_cache.get_file(relative_path)
            if entry is None:
                return None

        result_str = entry.content.replace('skill_dir', skill_cache.skill_dir)
        
        return result_str
    
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
            'max_size': self._max_size,
            'modules': list(self._module_cache.keys()),
            'configs': list(self._config_cache.keys()),
            'md_contents': list(self._md_content_cache.keys()),
            'file_cached_skills': list(self._file_cache.keys())
        }
    
    def _remove_module(self, skill_id: str) -> None:
        """移除模块缓存并清理 sys.modules
        
        Args:
            skill_id: 技能ID
        """
        if skill_id in self._module_cache:
            module = self._module_cache[skill_id]['module']
            if module:
                self._cleanup_module_references(module)
            del self._module_cache[skill_id]
            self.logger.debug(f"技能模块缓存已移除：{skill_id}")
        
        if skill_id in self._module_names:
            module_names = self._module_names[skill_id]
            for name in module_names:
                if name in sys.modules:
                    del sys.modules[name]
                    self.logger.debug(f"已从 sys.modules 移除：{name}")
            del self._module_names[skill_id]
        
        gc.collect()
        self.logger.debug(f"已调用 gc.collect() 清理内存")
    
    def _extract_module_names(self, module: ModuleType) -> List[str]:
        """提取模块及其子模块的名称
        
        Args:
            module: Python 模块对象
            
        Returns:
            模块名称列表
        """
        module_names = []
        if hasattr(module, '__name__'):
            module_names.append(module.__name__)
        
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, types.ModuleType):
                if hasattr(attr, '__name__'):
                    module_names.append(attr.__name__)
        
        return module_names
    
    def _cleanup_module_references(self, module: ModuleType) -> None:
        """清理模块内部引用，帮助 GC 回收
        
        Args:
            module: Python 模块对象
        """
        try:
            for attr_name in dir(module):
                if attr_name.startswith('__'):
                    continue
                try:
                    attr = getattr(module, attr_name)
                    if isinstance(attr, (list, dict, set)):
                        attr.clear()
                    elif hasattr(attr, '__dict__'):
                        attr.__dict__.clear()
                    delattr(module, attr_name)
                except Exception:
                    pass
        except Exception as e:
            self.logger.debug(f"清理模块引用时出错：{e}")
    
    def hot_reload(self, skill_id: str) -> None:
        """热重载技能（强制清理并重新加载）
        
        Args:
            skill_id: 技能ID
        """
        self.logger.info(f"热重载技能：{skill_id}")
        self.invalidate(skill_id)
        gc.collect()
        self.logger.info(f"技能热重载完成：{skill_id}")
    
    def force_gc(self) -> int:
        """强制执行垃圾回收
        
        Returns:
            回收的对象数量
        """
        gc.collect()
        count = gc.collect()
        self.logger.info(f"强制 GC 完成，回收了 {count} 个对象")
        return count
    
    def cleanup_expired(self) -> int:
        """清理所有过期的缓存
        
        Returns:
            清理的缓存条目数量
        """
        cleaned_count = 0
        
        expired_modules = []
        for skill_id, entry in list(self._module_cache.items()):
            if self._is_expired(entry['timestamp']):
                expired_modules.append(skill_id)
        
        for skill_id in expired_modules:
            self._remove_module(skill_id)
            cleaned_count += 1
        
        expired_configs = []
        for skill_id, entry in list(self._config_cache.items()):
            if self._is_expired(entry['timestamp']):
                expired_configs.append(skill_id)
        
        for skill_id in expired_configs:
            del self._config_cache[skill_id]
            cleaned_count += 1
        
        expired_md = []
        for skill_id, entry in list(self._md_content_cache.items()):
            if self._is_expired(entry['timestamp']):
                expired_md.append(skill_id)
        
        for skill_id in expired_md:
            del self._md_content_cache[skill_id]
            cleaned_count += 1
        
        if cleaned_count > 0:
            self.logger.info(f"清理了 {cleaned_count} 个过期缓存条目")
        
        return cleaned_count
