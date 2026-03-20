import logging
import sqlite3
import json
import re
from typing import List, Dict, Optional, Any
from datetime import datetime


class LongTermMemory:
    """长期记忆存储 - SQLite + 简单向量检索"""

    def __init__(self, db_path: str = "data/long_term_memory.db",
                 vector_dim: int = 384):
        """初始化长期记忆

        Args:
            db_path: 数据库路径
            vector_dim: 向量维度
        """
        self.db_path = db_path
        self.vector_dim = vector_dim
        self._init_db()
        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"初始化长期记忆，数据库: {db_path}")

    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_summaries (
                task_id TEXT PRIMARY KEY,
                session_id TEXT,
                summary TEXT,
                key_entities TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                accessed_at TIMESTAMP,
                access_count INTEGER DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS archived_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                message_id TEXT,
                role TEXT,
                content_summary TEXT,
                content_type TEXT,
                token_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS message_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                embedding BLOB,
                content_preview TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def store(self, task_id: str, summary: str, messages: List[Any],
              session_id: str = "default"):
        """存储任务到长期记忆

        Args:
            task_id: 任务ID
            summary: 任务摘要
            messages: 消息列表
            session_id: 会话ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        key_entities = self._extract_entities(summary)

        cursor.execute("""
            INSERT OR REPLACE INTO task_summaries
            (task_id, session_id, summary, key_entities)
            VALUES (?, ?, ?, ?)
        """, (task_id, session_id, summary, json.dumps(key_entities)))

        for msg in messages:
            cursor.execute("""
                INSERT INTO archived_messages
                (task_id, message_id, role, content_summary, content_type, token_count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                task_id,
                msg.id,
                msg.role,
                msg.summary or msg.content[:200],
                msg.content_type.value if hasattr(msg.content_type, 'value') else str(msg.content_type),
                msg.token_count
            ))

        conn.commit()
        conn.close()

        self.logger.debug(f"任务 {task_id} 已归档到长期记忆")

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """检索相关历史记忆

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            相关历史记录
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        keywords = query.split()
        results = []

        for keyword in keywords:
            cursor.execute("""
                SELECT task_id, summary, key_entities, access_count
                FROM task_summaries
                WHERE summary LIKE ? OR key_entities LIKE ?
                ORDER BY access_count DESC
                LIMIT ?
            """, (f"%{keyword}%", f"%{keyword}%", top_k))

            for row in cursor.fetchall():
                if row[0] not in [r["task_id"] for r in results]:
                    try:
                        results.append({
                            "task_id": row[0],
                            "summary": row[1],
                            "key_entities": json.loads(row[2]) if row[2] else [],
                            "access_count": row[3]
                        })
                    except json.JSONDecodeError:
                        results.append({
                            "task_id": row[0],
                            "summary": row[1],
                            "key_entities": [],
                            "access_count": row[3]
                        })

        for r in results[:top_k]:
            cursor.execute("""
                UPDATE task_summaries
                SET accessed_at = CURRENT_TIMESTAMP, access_count = access_count + 1
                WHERE task_id = ?
            """, (r["task_id"],))

        conn.commit()
        conn.close()

        return results[:top_k]

    def get_task_summary(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取特定任务摘要

        Args:
            task_id: 任务ID

        Returns:
            任务摘要信息
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT task_id, summary, key_entities, created_at, access_count
            FROM task_summaries
            WHERE task_id = ?
        """, (task_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            try:
                return {
                    "task_id": row[0],
                    "summary": row[1],
                    "key_entities": json.loads(row[2]) if row[2] else [],
                    "created_at": row[3],
                    "access_count": row[4]
                }
            except json.JSONDecodeError:
                return {
                    "task_id": row[0],
                    "summary": row[1],
                    "key_entities": [],
                    "created_at": row[3],
                    "access_count": row[4]
                }
        return None

    def get_task_messages(self, task_id: str) -> List[Dict[str, Any]]:
        """获取任务的所有归档消息

        Args:
            task_id: 任务ID

        Returns:
            消息列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT message_id, role, content_summary, content_type, token_count, created_at
            FROM archived_messages
            WHERE task_id = ?
            ORDER BY created_at
        """, (task_id,))
        rows = cursor.fetchall()
        conn.close()

        messages = []
        for row in rows:
            messages.append({
                "message_id": row[0],
                "role": row[1],
                "content_summary": row[2],
                "content_type": row[3],
                "token_count": row[4],
                "created_at": row[5]
            })

        return messages

    def delete_task(self, task_id: str) -> bool:
        """删除任务及其所有消息

        Args:
            task_id: 任务ID

        Returns:
            是否删除成功
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("DELETE FROM archived_messages WHERE task_id = ?", (task_id,))
            cursor.execute("DELETE FROM message_embeddings WHERE task_id = ?", (task_id,))
            cursor.execute("DELETE FROM task_summaries WHERE task_id = ?", (task_id,))

            conn.commit()
            self.logger.debug(f"任务 {task_id} 已从长期记忆中删除")
            return True

        except Exception as e:
            self.logger.error(f"删除任务 {task_id} 失败: {e}")
            conn.rollback()
            return False

        finally:
            conn.close()

    def list_tasks(self, session_id: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """列出任务

        Args:
            session_id: 会话ID（可选）
            limit: 返回数量限制

        Returns:
            任务列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if session_id:
            cursor.execute("""
                SELECT task_id, summary, created_at, access_count
                FROM task_summaries
                WHERE session_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (session_id, limit))
        else:
            cursor.execute("""
                SELECT task_id, summary, created_at, access_count
                FROM task_summaries
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        tasks = []
        for row in rows:
            tasks.append({
                "task_id": row[0],
                "summary": row[1],
                "created_at": row[2],
                "access_count": row[3]
            })

        return tasks

    def cleanup_old_tasks(self, days: int = 30) -> int:
        """清理旧任务

        Args:
            days: 保留天数

        Returns:
            删除的任务数量
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT task_id FROM task_summaries
                WHERE created_at < datetime('now', '-' || ? || ' days')
            """, (days,))

            old_tasks = [row[0] for row in cursor.fetchall()]

            deleted_count = 0
            for task_id in old_tasks:
                cursor.execute("DELETE FROM archived_messages WHERE task_id = ?", (task_id,))
                cursor.execute("DELETE FROM message_embeddings WHERE task_id = ?", (task_id,))
                cursor.execute("DELETE FROM task_summaries WHERE task_id = ?", (task_id,))
                deleted_count += 1

            conn.commit()
            self.logger.debug(f"清理了 {deleted_count} 个超过 {days} 天的旧任务")

            return deleted_count

        except Exception as e:
            self.logger.error(f"清理旧任务失败: {e}")
            conn.rollback()
            return 0

        finally:
            conn.close()

    def _extract_entities(self, text: str) -> List[str]:
        """提取关键实体

        Args:
            text: 文本

        Returns:
            实体列表
        """
        entities = []

        entities.extend(re.findall(r'"([^"]+)"', text))
        entities.extend(re.findall(r'\d{4}-\d{2}-\d{2}', text))
        entities.extend(re.findall(r'\d{2}:\d{2}', text))
        entities.extend(re.findall(r'\d+\.?\d*', text)[:5])

        return list(set(entities))

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        stats = {}

        cursor.execute("SELECT COUNT(*) FROM task_summaries")
        stats["total_tasks"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM archived_messages")
        stats["total_messages"] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM message_embeddings")
        stats["total_embeddings"] = cursor.fetchone()[0]

        cursor.execute("""
            SELECT AVG(access_count) FROM task_summaries WHERE access_count > 0
        """)
        result = cursor.fetchone()
        stats["avg_access_count"] = result[0] if result and result[0] else 0

        cursor.execute("""
            SELECT COUNT(*) FROM task_summaries
            WHERE created_at > datetime('now', '-7 days')
        """)
        stats["tasks_last_7_days"] = cursor.fetchone()[0]

        conn.close()

        return stats
