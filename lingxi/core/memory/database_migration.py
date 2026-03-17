#!/usr/bin/env python3
"""记忆数据库迁移脚本"""

import sqlite3
import logging
import os

logger = logging.getLogger(__name__)


def migrate(db_path: str):
    """
    执行数据库迁移
    
    Args:
        db_path: 数据库文件路径
    """
    # 确保目录存在
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 创建记忆表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            category TEXT NOT NULL,
            tags TEXT,
            importance INTEGER DEFAULT 3,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            access_count INTEGER DEFAULT 0,
            workspace_path TEXT NOT NULL,
            metadata TEXT
        )
        """)
        
        # 创建索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON memories(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_workspace ON memories(workspace_path)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created ON memories(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_content ON memories(content)")
        
        # 创建访问日志表
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory_access_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            memory_id TEXT NOT NULL,
            accessed_at REAL NOT NULL,
            query TEXT,
            context TEXT,
            
            FOREIGN KEY (memory_id) REFERENCES memories(id)
        )
        """)
        
        # 创建访问日志索引
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_access_memory ON memory_access_log(memory_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_access_time ON memory_access_log(accessed_at)")
        
        conn.commit()
        logger.info(f"记忆数据库迁移完成：{db_path}")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"数据库迁移失败：{e}")
        raise
    finally:
        conn.close()


def drop_all(db_path: str):
    """删除所有表（用于测试）"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("DROP TABLE IF EXISTS memories")
    cursor.execute("DROP TABLE IF EXISTS memory_access_log")
    
    conn.commit()
    conn.close()
    logger.info(f"数据库已删除：{db_path}")
