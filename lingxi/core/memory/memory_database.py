#!/usr/bin/env python3
"""记忆数据库访问层"""

import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class MemoryDatabase:
    """记忆数据库访问层"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接上下文管理器"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _init_db(self):
        """初始化数据库"""
        from .database_migration import migrate
        migrate(self.db_path)
        logger.info(f"记忆数据库已初始化：{self.db_path}")
    
    def save_memory(self, memory_data: Dict[str, Any]) -> bool:
        """
        保存记忆到数据库
        
        Args:
            memory_data: 记忆数据字典
        
        Returns:
            是否保存成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 检查是否存在
                cursor.execute("SELECT id FROM memories WHERE id = ?", (memory_data['id'],))
                exists = cursor.fetchone() is not None
                
                if exists:
                    # 更新
                    cursor.execute("""
                    UPDATE memories SET
                        content = ?,
                        category = ?,
                        tags = ?,
                        importance = ?,
                        updated_at = ?,
                        access_count = ?,
                        workspace_path = ?,
                        metadata = ?
                    WHERE id = ?
                    """, (
                        memory_data['content'],
                        memory_data['category'],
                        json.dumps(memory_data.get('tags', [])),
                        memory_data['importance'],
                        memory_data['updated_at'],
                        memory_data['access_count'],
                        memory_data['workspace_path'],
                        json.dumps(memory_data.get('metadata', {})),
                        memory_data['id']
                    ))
                else:
                    # 插入
                    cursor.execute("""
                    INSERT INTO memories (id, content, category, tags, importance, 
                                        created_at, updated_at, access_count, 
                                        workspace_path, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        memory_data['id'],
                        memory_data['content'],
                        memory_data['category'],
                        json.dumps(memory_data.get('tags', [])),
                        memory_data['importance'],
                        memory_data['created_at'],
                        memory_data['updated_at'],
                        memory_data['access_count'],
                        memory_data['workspace_path'],
                        json.dumps(memory_data.get('metadata', {}))
                    ))
                
                logger.debug(f"记忆已保存到数据库：{memory_data['id']}")
                return True
                
        except Exception as e:
            logger.error(f"保存记忆失败：{e}")
            return False
    
    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """获取记忆"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_dict(row)
            return None
    
    def search_memories(
        self,
        query: str,
        category: str = None,
        tags: List[str] = None,
        workspace_path: str = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """搜索记忆"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 构建查询
            conditions = []
            params = []
            
            if category:
                conditions.append("category = ?")
                params.append(category)
            
            if workspace_path:
                conditions.append("workspace_path = ?")
                params.append(workspace_path)
            
            # 内容搜索
            conditions.append("content LIKE ?")
            params.append(f"%{query}%")
            
            where_clause = " AND ".join(conditions)
            
            sql = f"""
            SELECT * FROM memories
            WHERE {where_clause}
            ORDER BY importance DESC, access_count DESC, created_at DESC
            LIMIT ?
            """
            params.append(limit)
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            # 过滤标签
            results = []
            for row in rows:
                memory = self._row_to_dict(row)
                
                if tags:
                    memory_tags = memory.get('tags', [])
                    if not any(t in memory_tags for t in tags):
                        continue
                
                results.append(memory)
            
            return results
    
    def get_all_memories(self, workspace_path: str = None) -> List[Dict[str, Any]]:
        """获取所有记忆"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if workspace_path:
                cursor.execute(
                    "SELECT * FROM memories WHERE workspace_path = ? ORDER BY importance DESC",
                    (workspace_path,)
                )
            else:
                cursor.execute("SELECT * FROM memories ORDER BY importance DESC")
            
            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]
    
    def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            deleted = cursor.rowcount > 0
            
            if deleted:
                logger.info(f"删除记忆：{memory_id}")
            return deleted
    
    def update_access_count(self, memory_id: str, query: str = None, context: str = None):
        """更新访问计数并记录日志"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 增加访问计数
            cursor.execute("""
            UPDATE memories SET access_count = access_count + 1 WHERE id = ?
            """, (memory_id,))
            
            # 记录访问日志
            cursor.execute("""
            INSERT INTO memory_access_log (memory_id, accessed_at, query, context)
            VALUES (?, ?, ?, ?)
            """, (memory_id, datetime.now().timestamp(), query, context))
    
    def get_stats(self, workspace_path: str = None) -> Dict[str, Any]:
        """获取统计信息"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            stats = {
                "total": 0,
                "by_category": {},
                "by_importance": {i: 0 for i in range(1, 6)},
                "workspace_path": workspace_path
            }
            
            # 总数
            if workspace_path:
                cursor.execute("SELECT COUNT(*) FROM memories WHERE workspace_path = ?", (workspace_path,))
            else:
                cursor.execute("SELECT COUNT(*) FROM memories")
            stats["total"] = cursor.fetchone()[0]
            
            # 按分类统计
            if workspace_path:
                cursor.execute("""
                SELECT category, COUNT(*) as count 
                FROM memories 
                WHERE workspace_path = ?
                GROUP BY category
                """, (workspace_path,))
            else:
                cursor.execute("""
                SELECT category, COUNT(*) as count 
                FROM memories 
                GROUP BY category
                """)
            
            for row in cursor.fetchall():
                stats["by_category"][row[0]] = row[1]
            
            # 按重要性统计
            if workspace_path:
                cursor.execute("""
                SELECT importance, COUNT(*) as count 
                FROM memories 
                WHERE workspace_path = ?
                GROUP BY importance
                """, (workspace_path,))
            else:
                cursor.execute("""
                SELECT importance, COUNT(*) as count 
                FROM memories 
                GROUP BY importance
                """)
            
            for row in cursor.fetchall():
                stats["by_importance"][row[0]] = row[1]
            
            return stats
    
    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """将数据库行转换为字典"""
        return {
            "id": row["id"],
            "content": row["content"],
            "category": row["category"],
            "tags": json.loads(row["tags"]) if row["tags"] else [],
            "importance": row["importance"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "access_count": row["access_count"],
            "workspace_path": row["workspace_path"],
            "metadata": json.loads(row["metadata"]) if row["metadata"] else {}
        }
