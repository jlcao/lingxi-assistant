"""SOUL 缓存管理器 - 管理 SOUL 数据的缓存"""

import hashlib
from typing import Optional, Dict
from datetime import datetime, timedelta


class SoulCache:
    """SOUL 缓存管理器"""
    
    def __init__(self):
        self._cache: Dict[str, dict] = {}  # workspace_path -> {hash, data, timestamp}
        self._ttl = 300  # 5 分钟 TTL (秒)
    
    def get(self, workspace_path: str) -> Optional[dict]:
        """从缓存获取 SOUL 数据"""
        if workspace_path not in self._cache:
            return None
        
        cache_entry = self._cache[workspace_path]
        
        # 检查是否过期
        if self._is_expired(cache_entry["timestamp"]):
            # 过期则删除
            del self._cache[workspace_path]
            return None
        
        return cache_entry["data"]
    
    def set(self, workspace_path: str, content: str, data: dict) -> None:
        """缓存 SOUL 数据"""
        content_hash = self._compute_hash(content)
        self._cache[workspace_path] = {
            "hash": content_hash,
            "data": data,
            "timestamp": datetime.now()
        }
    
    def invalidate(self, workspace_path: str) -> None:
        """使缓存失效"""
        if workspace_path in self._cache:
            del self._cache[workspace_path]
    
    def _compute_hash(self, content: str) -> str:
        """计算内容哈希"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _is_expired(self, timestamp: datetime) -> bool:
        """检查是否过期"""
        now = datetime.now()
        expiry_time = timestamp + timedelta(seconds=self._ttl)
        return now > expiry_time
    
    def is_valid(self, workspace_path: str, content: str) -> bool:
        """检查缓存是否仍然有效（内容未变化且未过期）"""
        if workspace_path not in self._cache:
            return False
        
        cache_entry = self._cache[workspace_path]
        
        # 检查是否过期
        if self._is_expired(cache_entry["timestamp"]):
            return False
        
        # 检查内容是否变化
        current_hash = self._compute_hash(content)
        return cache_entry["hash"] == current_hash
    
    def clear(self) -> None:
        """清空所有缓存"""
        self._cache.clear()
    
    def get_cache_info(self, workspace_path: str) -> Optional[dict]:
        """获取缓存信息（用于调试）"""
        if workspace_path not in self._cache:
            return None
        
        cache_entry = self._cache[workspace_path]
        now = datetime.now()
        age = (now - cache_entry["timestamp"]).total_seconds()
        remaining = self._ttl - age
        
        return {
            "cached": True,
            "age_seconds": age,
            "remaining_seconds": max(0, remaining),
            "hash": cache_entry["hash"]
        }
