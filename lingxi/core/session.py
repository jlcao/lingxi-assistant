import logging
import sqlite3
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from lingxi.core.classifier import TaskClassifier
from lingxi.core.llm_client import LLMClient
from lingxi.context.manager import ContextManager, ContentType


class SessionManager:
    """会话管理器，实现SQLite存储、检查点功能和上下文管理"""

    def __init__(self, config: Dict[str, Any], session_id: str = "default"):
        """初始化会话管理器

        Args:
            config: 系统配置
            session_id: 会话ID
        """
        self.config = config
        self.session_id = session_id
        self.db_path = config.get("session", {}).get("db_path", "data/assistant.db")
        self.max_history_turns = config.get("session", {}).get("max_history_turns", 50)
        self.memory_cache = {}

        self._init_db()

        self.context_manager = ContextManager(config, session_id)

        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"初始化会话管理器，数据库: {self.db_path}")

    def _init_db(self):
        """初始化SQLite数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_name TEXT DEFAULT 'default',
                history_json TEXT,
                checkpoint_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def get_history(self, session_id: str, max_turns: int = None) -> List[Dict[str, Any]]:
        """获取会话历史

        Args:
            session_id: 会话ID
            max_turns: 最大返回轮次

        Returns:
            会话历史记录
        """
        if max_turns is None:
            max_turns = self.max_history_turns

        if session_id in self.memory_cache:
            return self.memory_cache[session_id][-max_turns:]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT history_json FROM sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        conn.close()

        if row and row[0]:
            history = json.loads(row[0])
            self.memory_cache[session_id] = history
            return history[-max_turns:]
        return []

    def add_turn(self, session_id: str, role: str, content: str,
                 content_type: ContentType = None,
                 task_id: str = None,
                 metadata: Dict = None,
                 thought: str = None,
                 observation: str = None,
                 skill_calls: List[Dict] = None,
                 steps: List[Dict] = None,
                 thought_chain: Dict = None):
        """添加对话轮次

        Args:
            session_id: 会话ID
            role: 角色（user/assistant/tool/system）
            content: 内容
            content_type: 内容类型
            task_id: 任务ID
            metadata: 元数据
            thought: 思考过程
            observation: 观察结果
            skill_calls: 技能调用列表
            steps: 任务步骤列表
            thought_chain: 思考链
        """
        history = self.get_history(session_id)
        
        # 构建完整的对话轮次信息
        turn_info = {
            "role": role,
            "content": content,
            "time": time.time(),
            "content_type": content_type.value if content_type else None,
            "task_id": task_id,
            "metadata": metadata,
            "thought": thought,
            "observation": observation,
            "skill_calls": skill_calls,
            "steps": steps,
            "thought_chain": thought_chain
        }
        
        history.append(turn_info)

        if len(history) > self.max_history_turns:
            history = history[-self.max_history_turns:]

        self.memory_cache[session_id] = history
        self._save_to_db(session_id, history)

        self.context_manager.add_message(
            role=role,
            content=content,
            content_type=content_type,
            task_id=task_id,
            metadata=metadata
        )

    def _save_to_db(self, session_id: str, history: List[Dict[str, Any]]):
        """保存会话历史到数据库

        Args:
            session_id: 会话ID
            history: 会话历史
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO sessions (session_id, history_json, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (session_id, json.dumps(history, ensure_ascii=False)))
        conn.commit()
        conn.close()

    def save_checkpoint(self, session_id: str, state: Dict[str, Any]):
        """保存执行检查点

        Args:
            session_id: 会话ID
            state: 检查点状态
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO sessions (session_id, checkpoint_json, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (session_id, json.dumps(state, ensure_ascii=False)))
        conn.commit()
        conn.close()

    def restore_checkpoint(self, session_id: str) -> Optional[Dict[str, Any]]:
        """恢复检查点

        Args:
            session_id: 会话ID

        Returns:
            检查点状态，如果不存在则返回None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT checkpoint_json FROM sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        conn.close()

        if row and row[0]:
            return json.loads(row[0])
        return None

    def clear_session(self, session_id: str):
        """清空会话

        Args:
            session_id: 会话ID
        """
        if session_id in self.memory_cache:
            del self.memory_cache[session_id]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()

    def clear_session_history(self, session_id: str):
        """清除会话历史记录，但保留会话本身

        Args:
            session_id: 会话ID
        """
        if session_id in self.memory_cache:
            self.memory_cache[session_id] = []

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sessions SET history_json = '[]', updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """, (session_id,))
        conn.commit()
        conn.close()

    def get_checkpoint_status(self, session_id: str) -> Dict[str, Any]:
        """获取检查点状态信息

        Args:
            session_id: 会话ID

        Returns:
            检查点状态信息
        """
        checkpoint = self.restore_checkpoint(session_id)
        if not checkpoint:
            return {"has_checkpoint": False}

        return {
            "has_checkpoint": True,
            "task": checkpoint.get("task"),
            "current_step": checkpoint.get("current_step_idx", 0),
            "total_steps": len(checkpoint.get("plan", [])),
            "execution_status": checkpoint.get("execution_status"),
            "replan_count": checkpoint.get("replan_count", 0),
            "timestamp": checkpoint.get("timestamp"),
            "error_info": checkpoint.get("error_info")
        }

    def clear_checkpoint(self, session_id: str):
        """清除指定会话的检查点

        Args:
            session_id: 会话ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sessions SET checkpoint_json = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """, (session_id,))
        conn.commit()
        conn.close()

    def cleanup_expired_checkpoints(self, ttl_hours: int = 24) -> int:
        """清理过期的检查点

        Args:
            ttl_hours: 生存时间（小时）

        Returns:
            清理的检查点数量
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT session_id, checkpoint_json, updated_at FROM sessions")
        sessions = cursor.fetchall()

        current_time = time.time()
        ttl_seconds = ttl_hours * 3600
        cleaned_count = 0

        for session_id, checkpoint_json, updated_at in sessions:
            if checkpoint_json:
                try:
                    checkpoint = json.loads(checkpoint_json)
                    checkpoint_time = checkpoint.get("timestamp", updated_at)

                    if current_time - checkpoint_time > ttl_seconds:
                        cursor.execute("""
                            UPDATE sessions SET checkpoint_json = NULL, updated_at = CURRENT_TIMESTAMP
                            WHERE session_id = ?
                        """, (session_id,))
                        cleaned_count += 1
                        self.logger.debug(f"清除过期检查点：{session_id}")
                except Exception as e:
                    self.logger.error(f"处理检查点{session_id}时出错：{e}")

        conn.commit()
        conn.close()

        if cleaned_count > 0:
            self.logger.debug(f"清理了{cleaned_count}个过期检查点")

        return cleaned_count

    def list_active_checkpoints(self) -> List[Dict[str, Any]]:
        """列出所有活跃的检查点

        Returns:
            检查点列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT session_id, checkpoint_json, updated_at
            FROM sessions
            WHERE checkpoint_json IS NOT NULL
        """)
        rows = cursor.fetchall()
        conn.close()

        checkpoints = []
        for session_id, checkpoint_json, updated_at in rows:
            try:
                checkpoint = json.loads(checkpoint_json)
                checkpoints.append({
                    "session_id": session_id,
                    "task": checkpoint.get("task"),
                    "current_step": checkpoint.get("current_step_idx", 0),
                    "total_steps": len(checkpoint.get("plan", [])),
                    "execution_status": checkpoint.get("execution_status"),
                    "updated_at": updated_at
                })
            except Exception as e:
                self.logger.error(f"解析检查点{session_id}时出错：{e}")

        return checkpoints

    def process_input(self, user_input: str, session_id: str = "default") -> str:
        """处理用户输入（简化版，仅用于测试）

        Args:
            user_input: 用户输入
            session_id: 会话ID

        Returns:
            响应
        """
        classifier = TaskClassifier(self.config)
        task_info = classifier.classify(user_input)

        self.add_turn(session_id, "user", user_input,
                     content_type=ContentType.USER_INPUT)

        response = f"任务级别: {task_info['level']}\n置信度: {task_info['confidence']}\n理由: {task_info['reason']}"
        self.add_turn(session_id, "assistant", response,
                     content_type=ContentType.ASSISTANT_RESPONSE)

        return response

    def get_context_for_llm(self) -> List[Dict[str, str]]:
        """获取发送给LLM的上下文

        Returns:
            上下文列表
        """
        return self.context_manager.get_context_for_llm()

    def get_context_stats(self) -> Dict[str, Any]:
        """获取上下文统计信息

        Returns:
            统计信息
        """
        return self.context_manager.get_stats()

    def set_current_task(self, task_id: str):
        """设置当前任务ID

        Args:
            task_id: 任务ID
        """
        self.context_manager.set_current_task(task_id)

    def compress_context(self, strategy: str = None) -> Dict[str, Any]:
        """手动触发上下文压缩

        Args:
            strategy: 压缩策略

        Returns:
            压缩统计信息
        """
        return self.context_manager.compress(strategy)

    def retrieve_relevant_history(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """检索相关历史记忆

        Args:
            query: 查询文本
            top_k: 返回数量

        Returns:
            相关历史记录
        """
        return self.context_manager.retrieve_relevant_history(query, top_k)

    def list_all_sessions(self) -> List[Dict[str, Any]]:
        """列出所有会话

        Returns:
            会话列表，包含session_id、创建时间、更新时间、消息数量等信息
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT session_id, history_json, created_at, updated_at
            FROM sessions
            ORDER BY updated_at DESC
        """)
        rows = cursor.fetchall()
        conn.close()

        sessions = []
        for session_id, history_json, created_at, updated_at in rows:
            try:
                history = json.loads(history_json) if history_json else []
                first_user_msg = ""
                for msg in history:
                    if msg.get("role") == "user":
                        first_user_msg = msg.get("content", "")[:50]
                        break

                sessions.append({
                    "session_id": session_id,
                    "message_count": len(history),
                    "first_message": first_user_msg,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "has_checkpoint": False
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
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT session_id, history_json, checkpoint_json, created_at, updated_at
            FROM sessions
            WHERE session_id = ?
        """, (session_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        session_id, history_json, checkpoint_json, created_at, updated_at = row
        history = json.loads(history_json) if history_json else []

        return {
            "session_id": session_id,
            "history": history,
            "message_count": len(history),
            "created_at": created_at,
            "updated_at": updated_at,
            "has_checkpoint": checkpoint_json is not None
        }

    def rename_session(self, session_id: str, new_title: str) -> bool:
        """重命名会话（通过在历史记录开头添加标题）

        Args:
            session_id: 会话ID
            new_title: 新标题

        Returns:
            是否成功
        """
        history = self.get_history(session_id)
        if not history:
            return False

        if history and history[0].get("role") == "system" and history[0].get("type") == "title":
            history[0]["content"] = new_title
        else:
            history.insert(0, {"role": "system", "type": "title", "content": new_title, "time": time.time()})

        self.memory_cache[session_id] = history
        self._save_to_db(session_id, history)
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

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return deleted

    def create_session(self, user_name: str = "default") -> str:
        """创建新会话

        Args:
            user_name: 用户名

        Returns:
            会话ID
        """
        import uuid
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sessions (session_id, user_name, history_json)
            VALUES (?, ?, ?)
        """, (session_id, user_name, json.dumps([])))
        conn.commit()
        conn.close()
        
        self.memory_cache[session_id] = []
        return session_id
