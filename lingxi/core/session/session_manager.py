from __future__ import annotations

import json
import logging
import sqlite3
from typing import Dict, List, Optional, Any
from datetime import datetime
from webbrowser import get

from lingxi.core.context.session_context import SessionContext, ContentType
from lingxi.core.session.session_models import Session
from lingxi.core.session.database_manager import DatabaseManager
from lingxi.core.session.task_manager import TaskManager, task_to_dict, dict_to_task
from lingxi.core.session.step_manager import StepManager, step_to_dict, dict_to_step
from lingxi.core.session.session_models import Task
from lingxi.core.session.workspace_registry import WorkspaceRegistry
from lingxi.core.soul import SoulInjector
from lingxi.core.memory import MemoryManager, MemoryExtractor
from lingxi.utils.config import get_config,set_workspace_path


def session_to_dict(session: Session) -> dict:
    """将 Session 对象转换为字典（用于数据库存储）"""
    return {
        "session_id": session.session_id,
        "user_name": session.user_name,
        "title": session.title,
        "current_task_id": session.current_task_id,
        "total_tokens": session.total_tokens,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None
    }


def dict_to_session(session_dict: dict) -> Session:
    """将字典转换为 Session 对象"""
    return Session(
        session_id=session_dict.get("session_id", ""),
        user_name=session_dict.get("user_name", "default"),
        title=session_dict.get("title", "新会话"),
        current_task_id=session_dict.get("current_task_id", ""),
        total_tokens=session_dict.get("total_tokens", 0),
        created_at=datetime.fromisoformat(session_dict["created_at"]) if session_dict.get("created_at") else None,
        updated_at=datetime.fromisoformat(session_dict["updated_at"]) if session_dict.get("updated_at") else None
    )


class SessionManager:
    """会话管理器，实现会话管理、检查点功能和上下文管理"""

    _instance = None

    def __new__(cls):
        """单例模式：确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初始化会话管理器

        Args:
            config: 系统配置
            session_id: 会话 ID
        """
        
        self.config = get_config()
        
        # 处理数据库路径：如果是相对路径，转换为相对于用户目录的绝对路径
      
        self.db_path = self.config.get("session", {}).get("db_path") or self.config.get("database", {}).get("lingxi_db", "data/assistant.db")
        # 确保路径是绝对路径，相对于用户目录
        from pathlib import Path
        if not Path(self.db_path).is_absolute():
            from lingxi.utils.config import GLOBAL_LINGXI_DIR
            self.db_path = str(GLOBAL_LINGXI_DIR / self.db_path)
        
        self.max_history_turns = self.config.get("session", {}).get("max_history_turns", 50)
        self.memory_cache = {}

        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"初始化会话管理器，数据库: {self.db_path}")

        self.db_manager = DatabaseManager()
        self.step_manager = StepManager()
        self.task_manager = TaskManager()

        # 初始化工作目录注册表
        self.workspace_registry = WorkspaceRegistry()
        
        # 初始化 SOUL 注入器和记忆管理器
        self.workspace_path = self.config.get("workspace", {}).get("last_workspace", "./workspace")
        self.soul_injector = SoulInjector()
        self.soul_injector.load()
        self.logger.debug(f"SOUL 注入器已初始化，工作目录：{self.workspace_path}")
        
        # 记忆管理器
        self.memory_manager = MemoryManager(self.config)
        self.memory_extractor = MemoryExtractor(self.memory_manager)
        
        # 自动加载 MEMORY.md
        if self.workspace_path:
            count = self.memory_manager.load_memory(self.workspace_path)
            self.logger.info(f"加载了 {count} 条记忆")
        
        self.session_context_cache = {}
    
        self._initialized = True
    

    def update_db_path(self, new_db_path: str):
        """更新数据库路径（用于工作区切换）

        Args:
            new_db_path: 新的数据库路径
        """
        self.db_path = new_db_path
        self.config['session'] = self.config.get('session', {})
        self.config['session']['db_path'] = new_db_path
        
        # 调用 DatabaseManager 的 update_db_path 方法
        if hasattr(self.db_manager, 'update_db_path'):
            self.db_manager.update_db_path(new_db_path)
        else:
            # 备用方案：直接更新 db_path 并重新初始化
            self.db_manager.db_path = new_db_path
            self.db_manager._init_db()
        
        # 更新工作目录注册表的数据库路径
        self.workspace_registry.db_path = new_db_path
        self.workspace_registry._connection_cache = None
        self.workspace_registry._migrate_database()
        
        self.logger.info(f"数据库路径已更新：{new_db_path}")

    def switch_workspace(self, workspace_path: str):
        """切换工作目录并重新加载 SOUL

        Args:
            workspace_path: 新的工作目录路径
        """
        self.workspace_path = workspace_path
        self.soul_injector = SoulInjector(workspace_path)
        self.soul_injector.load()
        set_workspace_path(workspace_path) #更新公共的工作目录路径
        self.logger.info(f"工作目录已切换到：{workspace_path}，SOUL 已重新加载")

    def get_history(self, session_id: str) -> List[Task]:
        """获取会话历史

        Args:
            session_id: 会话 ID
        Returns:
            会话历史记录（任务列表，包含步骤信息）
        """
        tasks = self.task_manager.get_tasks_by_session(session_id)

        # 压缩方法已经迁移到ContextManager中
        #if compress:
        #    tasks = self._compress_history(tasks)

        return tasks

    def update_session_tokens(self, session_id: str, input_tokens: int, output_tokens: int):
        """更新会话 Token 总数

        Args:
            session_id: 会话ID
            input_tokens: 输入 Token 数量
            output_tokens: 输出 Token 数量
        """
        sql = """
            UPDATE sessions 
            SET total_tokens = total_tokens + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """
        self.db_manager.execute_sql(sql, (input_tokens + output_tokens, session_id))
        self.logger.debug(f"会话 Token 已更新，session_id: {session_id}, tokens: {input_tokens + output_tokens}")

    def clear_session(self, session_id: str):
        """清空会话（包括所有任务和步骤）

        Args:
            session_id: 会话ID
        """
        if session_id in self.memory_cache:
            del self.memory_cache[session_id]

        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

        conn.commit()
        conn.close()

        self.logger.debug(f"会话已清空，session_id: {session_id}")

    def clear_session_history(self, session_id: str):
        """清除会话历史记录（删除所有任务和步骤），但保留会话本身

        Args:
            session_id: 会话ID
        """
        if session_id in self.memory_cache:
            del self.memory_cache[session_id]

        self.task_manager.delete_tasks_by_session(session_id)

        sql = """
            UPDATE sessions SET current_task_id = NULL, total_tokens = 0, checkpoint_json = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """
        self.db_manager.execute_sql(sql, (session_id,))

        self.logger.debug(f"会话历史已清空，session_id: {session_id}")

    def list_all_sessions(self, workspace_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出所有会话

        Args:
            workspace_path: 工作目录路径（可选）

        Returns:
            会话列表，包含session_id、创建时间、更新时间、消息数量等信息
        """
        if workspace_path:
            # 从工作目录注册表中获取该工作目录关联的会话
            workspace_sessions = self.workspace_registry.get_sessions_by_workspace_path(workspace_path)
            
            # 构建会话ID列表
            session_ids = [s['session_id'] for s in workspace_sessions]
            if not session_ids:
                return []
            
            # 构建IN查询
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            placeholders = ','.join(['?'] * len(session_ids))
            query = f"""
                SELECT s.session_id, s.title, s.created_at, s.updated_at, COUNT(t.task_id) as task_count
                FROM sessions s
                LEFT JOIN tasks t ON s.session_id = t.session_id
                WHERE s.session_id IN ({placeholders})
                GROUP BY s.session_id
                ORDER BY s.updated_at DESC
            """
            cursor.execute(query, session_ids)
        else:
            # 列出所有会话
            conn = self.db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.session_id, s.title, s.created_at, s.updated_at, COUNT(t.task_id) as task_count
                FROM sessions s
                LEFT JOIN tasks t ON s.session_id = t.session_id
                GROUP BY s.session_id
                ORDER BY s.updated_at DESC
            """)
        
        rows = cursor.fetchall()
        conn.close()

        sessions = []
        for session_id, title, created_at, updated_at, task_count in rows:
            try:
                cursor = self.db_manager.get_connection()
                c = cursor.cursor()
                c.execute("""
                    SELECT user_input FROM tasks
                    WHERE session_id = ? AND user_input IS NOT NULL
                    ORDER BY created_at ASC
                    LIMIT 1
                """, (session_id,))
                first_message_row = c.fetchone()
                first_message = first_message_row[0][:50] if first_message_row and first_message_row[0] else ""
                cursor.close()

                sessions.append({
                    "sessionId": session_id,
                    "title": title,
                    "taskCount": task_count,
                    "firstMessage": first_message,
                    "createdAt": created_at,
                    "updatedAt": updated_at,
                    "hasCheckpoint": False
                })
            except Exception as e:
                self.logger.error(f"解析会话{session_id}时出错：{e}")

        return sessions

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话详细信息

        Args:
            session_id: 会话ID

        Returns:
            会话信息
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT session_id, title, total_tokens, checkpoint_json, created_at, updated_at
            FROM sessions
            WHERE session_id = ?
        """, (session_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        session_id, title, total_tokens, checkpoint_json, created_at, updated_at = row

        task_list = self.task_manager.get_tasks_by_session(session_id)

        return {
            "session_id": session_id,
            "title": title,
            "task_count": len(task_list),
            "task_list": task_list,
            "total_tokens": total_tokens,
            "created_at": created_at,
            "updated_at": updated_at,
            "has_checkpoint": checkpoint_json is not None
        }
    
    def get_session_info_for_frontend(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取会话详细信息（前端前端使用）

        Args:
            session_id: 会话ID

        Returns:
            会话信息
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT session_id, title, total_tokens, checkpoint_json, created_at, updated_at
            FROM sessions
            WHERE session_id = ?
        """, (session_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        session_id, title, total_tokens, checkpoint_json, created_at, updated_at = row

        task_list = self.task_manager.get_tasks_by_session_for_frontend(session_id)

        return {
            "sessionId": session_id,
            "title": title,
            "taskCount": len(task_list),
            "tasks": task_list,
            "totalTokens": total_tokens,
            "createdAt": created_at,
            "updatedAt": updated_at,
            "hasCheckpoint": checkpoint_json is not None
        }


    def rename_session(self, session_id: str, new_title: str) -> bool:
        """重命名会话

        Args:
            session_id: 会话ID
            new_title: 新标题

        Returns:
            是否成功
        """
        sql = """
            UPDATE sessions SET title = ?, updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """
        self.db_manager.execute_sql(sql, (new_title, session_id))

        self.logger.debug(f"会话已重命名，session_id: {session_id}, new_title: {new_title}")
        return True

    def delete_session(self, session_id: str) -> bool:
        """删除会话

        Args:
            session_id: 会话ID

        Returns:
            是否成功
        """
        if session_id in self.memory_cache:
            del self.memory_cache[session_id]

        conn = self.db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return deleted

    def create_session(self, user_name: str = "default", system_prompt: str = None) -> str:
        """创建新会话

        Args:
            user_name: 用户名
            system_prompt: 基础系统提示词（可选）

        Returns:
            会话 ID
        """
        import uuid
        session_id = str(uuid.uuid4())
        return self.create_session_by_id(session_id, user_name, system_prompt)

    def create_session_by_id(self, session_id: str, user_name: str = "default", system_prompt: str = None, workspace_path: Optional[str] = None) -> str:
        """根据指定的会话 ID 创建新会话

        Args:
            session_id: 会话 ID
            user_name: 用户名
            system_prompt: 基础系统提示词（可选）
            workspace_path: 工作目录路径（可选）

        Returns:
            会话 ID
        """
        sql = """
            INSERT INTO sessions (session_id, user_name, title, total_tokens, created_at, updated_at)
            VALUES (?, ?, '新会话', 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """
        self.db_manager.execute_sql(sql, (session_id, user_name))

        # 如果指定了工作目录，关联会话和工作目录
        if workspace_path:
            success = self.workspace_registry.associate_session_with_workspace(session_id, workspace_path)
            if success:
                self.logger.debug(f"会话已关联到工作目录：{session_id} -> {workspace_path}")
            else:
                self.logger.warning(f"会话关联工作目录失败：{session_id} -> {workspace_path}")

        self.logger.debug(f"会话已创建，session_id: {session_id}, user_name: {user_name}")
        return session_id
    
    def update_session_title(self, session_id: str, title: str) -> bool:
        """更新会话标题
        
        Args:
            session_id: 会话 ID
            title: 新的标题
            
        Returns:
            是否更新成功
        """
        sql = """
            UPDATE sessions 
            SET title = ?, updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """
        try:
            self.db_manager.execute_sql(sql, (title, session_id))
            self.logger.debug(f"会话标题已更新：session_id={session_id}, title={title[:50]}...")
            return True
        except Exception as e:
            self.logger.error(f"更新会话标题失败：{e}")
            return False

  



