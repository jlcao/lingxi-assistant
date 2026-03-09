#!/usr/bin/env python3
"""技能注册表（SQLite）"""

import os
import sqlite3
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any


class SkillRegistry:
    """本地技能注册表（SQLite）"""

    def __init__(self, config: Dict[str, Any]):
        """初始化技能注册表

        Args:
            config: 系统配置
        """
        self.logger = logging.getLogger(__name__)
        
        db_path = config.get("skills", {}).get("db_path", "data/skills.db")
        self.db_path = db_path
        self.skill_cache: Dict[str, Dict[str, Any]] = {}
        
        self._init_db()
        self._load_to_cache()
        
        self.logger.debug(f"初始化技能注册表: {db_path}")

    def _init_db(self):
        """初始化数据库"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                skill_id TEXT PRIMARY KEY,
                skill_name TEXT,
                version TEXT DEFAULT '1.0.0',
                api_url TEXT,
                api_key TEXT,
                input_schema TEXT,
                description TEXT,
                author TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def _load_to_cache(self):
        """加载技能到内存缓存"""
        self.skill_cache = {}
        
        if not os.path.exists(self.db_path):
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM skills WHERE enabled = 1")
        
        columns = [description[0] for description in cursor.description]
        
        for row in cursor.fetchall():
            row_dict = dict(zip(columns, row))
            
            skill = {
                "skill_id": row_dict.get("skill_id") or row_dict.get("id"),
                "skill_name": row_dict.get("skill_name") or row_dict.get("name"),
                "version": row_dict.get("version", "1.0.0"),
                "api_url": row_dict.get("api_url", ""),
                "api_key": row_dict.get("api_key", ""),
                "input_schema": self._parse_json_field(row_dict.get("input_schema")),
                "description": row_dict.get("description", ""),
                "author": row_dict.get("author", ""),
                "enabled": row_dict.get("enabled", 1)
            }
            self.skill_cache[skill["skill_id"]] = skill
        
        conn.close()
        self.logger.debug(f"加载了 {len(self.skill_cache)} 个技能到缓存")

    def _parse_json_field(self, field_value: Any) -> Optional[Dict[str, Any]]:
        """解析JSON字段

        Args:
            field_value: 字段值

        Returns:
            解析后的字典，失败返回None
        """
        if field_value is None:
            return None
        
        if isinstance(field_value, dict):
            return field_value
        
        if isinstance(field_value, (str, bytes)):
            try:
                return json.loads(field_value)
            except (json.JSONDecodeError, TypeError):
                return None
        
        return None

    def register_skill(self, name: str, description: str = "", author: str = "",
                      version: str = "1.0.0", parameters: List[Dict[str, Any]] = None) -> bool:
        """注册技能

        Args:
            name: 技能名称
            description: 技能描述
            author: 作者
            version: 版本
            parameters: 技能参数

        Returns:
            是否注册成功
        """
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("PRAGMA table_info(skills)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if "skill_id" in columns:
                cursor.execute("""
                    INSERT OR REPLACE INTO skills 
                    (skill_id, skill_name, version, api_url, api_key, input_schema, description, author)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    name,
                    name,
                    version,
                    "",  # api_url
                    "",  # api_key
                    json.dumps(parameters) if parameters else None,
                    description,
                    author
                ))
            else:
                cursor.execute("""
                    INSERT OR REPLACE INTO skills 
                    (name, description, author, version, enabled)
                    VALUES (?, ?, ?, ?, 1)
                """, (
                    name,
                    description,
                    author,
                    version
                ))
            
            conn.commit()
            self._load_to_cache()
            
            self.logger.debug(f"注册技能: {name}")
            return True
        
        except Exception as e:
            self.logger.error(f"注册技能失败 {name}: {e}")
            return False
        
        finally:
            conn.close()

    def unregister_skill(self, name: str) -> bool:
        """注销技能

        Args:
            name: 技能名称

        Returns:
            是否注销成功
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM skills WHERE skill_id = ?", (name,))
            conn.commit()
            self._load_to_cache()
            
            self.logger.debug(f"注销技能: {name}")
            return True
        
        except Exception as e:
            self.logger.error(f"注销技能失败 {name}: {e}")
            return False
        
        finally:
            conn.close()

    def enable_skill(self, name: str, enabled: bool = True) -> bool:
        """启用或禁用技能

        Args:
            name: 技能名称
            enabled: 是否启用

        Returns:
            是否操作成功
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("UPDATE skills SET enabled = ? WHERE skill_id = ?", (1 if enabled else 0, name))
            conn.commit()
            self._load_to_cache()
            
            self.logger.debug(f"{'启用' if enabled else '禁用'}技能: {name}")
            return True
        
        except Exception as e:
            self.logger.error(f"{'启用' if enabled else '禁用'}技能失败 {name}: {e}")
            return False
        
        finally:
            conn.close()

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
                {"skill_id": s["skill_id"], "skill_name": s["skill_name"], "name": s["skill_name"],
                 "description": s["description"], "version": s["version"],
                 "author": s["author"], "enabled": s["enabled"], "source": s.get("source", "global")}
                for s in self.skill_cache.values()
            ]
        else:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM skills")
            
            columns = [description[0] for description in cursor.description]
            
            skills = []
            for row in cursor.fetchall():
                row_dict = dict(zip(columns, row))
                
                skill_id = row_dict.get("skill_id") or row_dict.get("id")
                skill_name = row_dict.get("skill_name") or row_dict.get("name")
                
                skill = {
                    "skill_id": skill_id,
                    "skill_name": skill_name,
                    "name": skill_name,
                    "version": row_dict.get("version", "1.0.0"),
                    "api_url": row_dict.get("api_url", ""),
                    "api_key": row_dict.get("api_key", ""),
                    "input_schema": self._parse_json_field(row_dict.get("input_schema")),
                    "description": row_dict.get("description", ""),
                    "author": row_dict.get("author", ""),
                    "enabled": row_dict.get("enabled", 1),
                    "source": "global"
                }
                skills.append(skill)
            
            conn.close()
            return skills
    
    def register_skill_from_dir(self, skill_dir: Path, source: str = "global"):
        """从目录注册技能
        
        Args:
            skill_dir: 技能目录
            source: 技能来源（global/workspace）
        """
        import importlib.util
        
        if not (skill_dir / "main.py").exists():
            raise ValueError(f"技能目录缺少 main.py: {skill_dir}")
        
        # 加载技能模块
        spec = importlib.util.spec_from_file_location(
            f"skill_{skill_dir.name}",
            skill_dir / "main.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 获取技能信息
        if hasattr(module, 'get_skill_info'):
            skill_info = module.get_skill_info()
            skill_info['source'] = source
            skill_info['path'] = str(skill_dir)
            
            self.skill_cache[skill_info['name']] = skill_info
            self.logger.info(f"注册技能：{skill_info['name']} (source={source})")
        else:
            # 如果没有 get_skill_info，使用默认信息
            skill_info = {
                "name": skill_dir.name,
                "skill_id": skill_dir.name,
                "description": f"技能：{skill_dir.name}",
                "source": source,
                "path": str(skill_dir)
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
