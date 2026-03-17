from __future__ import annotations

import json
import logging
import sqlite3
from typing import Dict, List, Optional, Any
from datetime import datetime

from lingxi.context.manager import ContextManager, ContentType
from lingxi.core.session.session_models import Session
from lingxi.core.session.database_manager import DatabaseManager
from lingxi.core.session.task_manager import TaskManager, task_to_dict, dict_to_task
from lingxi.core.session.step_manager import StepManager, step_to_dict, dict_to_step
from lingxi.core.session.workspace_registry import WorkspaceRegistry
from lingxi.core.soul import SoulInjector
from lingxi.core.memory import MemoryManager, MemoryExtractor


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

    def __new__(cls, config: Dict[str, Any], session_id: str = "default"):
        """单例模式：确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: Dict[str, Any], session_id: str = "default"):
        """初始化会话管理器

        Args:
            config: 系统配置
            session_id: 会话ID
        """
        self.config = config
        self.db_path = config.get("session", {}).get("db_path", "data/assistant.db")
        self.max_history_turns = config.get("session", {}).get("max_history_turns", 50)
        self.memory_cache = {}

        self.logger = logging.getLogger(__name__)
        self.logger.debug(f"初始化会话管理器，数据库: {self.db_path}")

        self.db_manager = DatabaseManager(self.db_path, self.logger)
        self.step_manager = StepManager(self.db_manager, self.logger)
        self.task_manager = TaskManager(self.db_manager, self.step_manager, self.logger)

        # 初始化工作目录注册表
        self.workspace_registry = WorkspaceRegistry(self.db_path)

        self.context_manager = ContextManager(config, session_id)
        
        # 初始化 SOUL 注入器
        self.workspace_path = config.get("workspace", {}).get("last_workspace", "./workspace")
        self.soul_injector = SoulInjector(self.workspace_path)
        self.soul_injector.load()  # 加载 SOUL.md
        self.logger.debug(f"SOUL 注入器已初始化，工作目录：{self.workspace_path}")
        
        # 记忆管理器
        self.memory_manager = MemoryManager(config)
        self.memory_extractor = MemoryExtractor(self.memory_manager)
        self.session_context_cache = {}
        
        # 自动加载 MEMORY.md
        if self.workspace_path:
            count = self.memory_manager.load_memory(self.workspace_path)
            self.logger.info(f"加载了 {count} 条记忆")
        
        self._initialized = True

    def get_session_context(self,session_id:str) -> ContextManager:
        """获取当前会话的上下文管理器"""
        session_context = self.session_context_cache.get(session_id)
        if session_context is None:
            session_context = ContextManager(self.config, session_id)
            self.session_context_cache[session_id] = session_context
            self._build_soul_and_memory(session_id);
        return session_context
    

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
        
        # 更新工作目录注册表，使用新的数据库路径
        self.workspace_registry = WorkspaceRegistry(new_db_path)
        
        self.logger.info(f"数据库路径已更新：{new_db_path}")

    def switch_workspace(self, workspace_path: str):
        """切换工作目录并重新加载 SOUL

        Args:
            workspace_path: 新的工作目录路径
        """
        self.workspace_path = workspace_path
        self.soul_injector = SoulInjector(workspace_path)
        self.soul_injector.load()
        self.logger.info(f"工作目录已切换到：{workspace_path}，SOUL 已重新加载")

    def get_history(self, session_id: str, max_turns: int = None, compress: bool = False) -> List[Dict[str, Any]]:
        """获取会话历史

        Args:
            session_id: 会话 ID
            max_turns: 最大返回轮次
            compress: 是否启用历史压缩（默认 False）

        Returns:
            会话历史记录（任务列表，包含步骤信息）
        """
        tasks = self.task_manager.get_tasks_by_session(session_id)

        if max_turns and len(tasks) > max_turns:
            tasks = tasks[:max_turns]

        # 如果启用压缩，调用压缩方法
        if compress:
            tasks = self._compress_history(tasks)

        return tasks

    def _compress_history(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """压缩会话历史，保留最近完整对话，压缩旧对话为摘要

        压缩策略：
        - 保留最近 10 轮完整对话（user_input + result）
        - 更早的对话压缩 result 字段为简短摘要
        - 移除详细步骤信息（steps 字段）
        - 支持 LLM 智能摘要（需配置启用）

        Args:
            tasks: 原始任务列表

        Returns:
            压缩后的任务列表
        """
        if not tasks:
            return tasks

        # 从配置中获取压缩相关配置
        compression_config = self.config.get("context_management", {}).get("compression", {})
        max_full_turns = compression_config.get("max_history_turns", 10)
        use_llm = compression_config.get("use_llm", False)
        llm_threshold = compression_config.get("llm_threshold", 50)

        self.logger.debug(f"历史压缩：共 {len(tasks)} 条任务，use_llm={use_llm}, llm_threshold={llm_threshold}")

        # 判断是否使用 LLM 智能压缩
        if use_llm and len(tasks) > llm_threshold:
            self.logger.info(f"任务数 ({len(tasks)}) 超过阈值 ({llm_threshold})，启用 LLM 智能压缩")
            try:
                return self._llm_compress_history(tasks, max_full_turns)
            except Exception as e:
                self.logger.warning(f"LLM 压缩失败，降级为轻量级压缩：{e}")
                # 降级为轻量级压缩
                return self._simple_compress_history(tasks, max_full_turns)
        else:
            # 使用轻量级压缩
            self.logger.debug(f"使用轻量级压缩（任务数 {len(tasks)} <= 阈值 {llm_threshold} 或 use_llm=False）")
            return self._simple_compress_history(tasks, max_full_turns)

    def _simple_compress_history(self, tasks: List[Dict[str, Any]], max_full_turns: int = 10) -> List[Dict[str, Any]]:
        """轻量级压缩历史：保留最近完整对话，压缩旧对话为简单摘要

        Args:
            tasks: 原始任务列表
            max_full_turns: 保留的完整对话轮数

        Returns:
            压缩后的任务列表
        """
        if not tasks:
            return tasks

        compressed_tasks = []

        for i, task in enumerate(tasks):
            # 复制任务以避免修改原始数据
            compressed_task = dict(task)

            # 判断是否是最近的任务（需要保留完整信息）
            is_recent = i >= len(tasks) - max_full_turns

            if not is_recent:
                # 压缩旧任务：移除详细步骤，简化 result
                if "steps" in compressed_task:
                    # 只保留步骤数量信息，移除详细内容
                    step_count = len(compressed_task["steps"]) if compressed_task["steps"] else 0
                    compressed_task["steps"] = [{"note": f"[已压缩] 共 {step_count} 个步骤"}] if step_count > 0 else []

                # 压缩 result 字段：如果 result 很长，截取前一部分并添加摘要标记
                if compressed_task.get("result"):
                    result_text = str(compressed_task["result"])
                    if len(result_text) > 200:
                        compressed_task["result"] = f"[摘要] {result_text[:200]}..."

            compressed_tasks.append(compressed_task)

        self.logger.debug(f"轻量级压缩完成：{len(tasks)} -> {len(compressed_tasks)} 条任务，保留最近 {max_full_turns} 轮完整对话")
        return compressed_tasks

    def _llm_compress_history(self, tasks: List[Dict[str, Any]], max_full_turns: int = 10) -> List[Dict[str, Any]]:
        """使用 LLM 智能压缩历史：对旧对话生成语义摘要

        压缩策略：
        - 保留最近 max_full_turns 轮完整对话
        - 对更早的对话使用 LLM 生成语义摘要
        - 移除详细步骤信息

        Args:
            tasks: 原始任务列表
            max_full_turns: 保留的完整对话轮数

        Returns:
            压缩后的任务列表
        """
        if not tasks:
            return tasks

        self.logger.info(f"LLM 智能压缩：共 {len(tasks)} 条任务，保留最近 {max_full_turns} 轮")

        # 分离旧任务和新任务
        if len(tasks) <= max_full_turns:
            # 任务数不超过阈值，无需压缩
            return tasks

        old_tasks = tasks[:-max_full_turns]
        recent_tasks = tasks[-max_full_turns:]

        # 对旧任务使用 LLM 生成摘要
        compressed_old_tasks = []
        for i, task in enumerate(old_tasks):
            compressed_task = dict(task)
            
            # 移除详细步骤
            if "steps" in compressed_task:
                step_count = len(compressed_task["steps"]) if compressed_task["steps"] else 0
                compressed_task["steps"] = [{"note": f"[LLM 压缩] 共 {step_count} 个步骤"}] if step_count > 0 else []

            # 使用 LLM 压缩 result 字段
            if compressed_task.get("result"):
                result_text = str(compressed_task["result"])
                try:
                    compressed_task["result"] = self._summarize_with_llm(result_text, task.get("user_input", ""))
                except Exception as e:
                    self.logger.warning(f"LLM 摘要失败（任务 {i+1}/{len(old_tasks)}），使用轻量级摘要：{e}")
                    # 降级为轻量级摘要
                    if len(result_text) > 200:
                        compressed_task["result"] = f"[摘要] {result_text[:200]}..."
            
            compressed_old_tasks.append(compressed_task)

        # 合并旧任务和新任务
        compressed_tasks = compressed_old_tasks + recent_tasks

        self.logger.info(f"LLM 智能压缩完成：{len(tasks)} -> {len(compressed_tasks)} 条任务")
        return compressed_tasks

    def _summarize_with_llm(self, text: str, user_input: str = "") -> str:
        """使用 LLM 生成文本摘要

        Args:
            text: 需要摘要的文本
            user_input: 原始用户输入（可选，用于提供上下文）

        Returns:
            摘要文本

        Raises:
            Exception: 当 LLM 调用失败时
        """
        from lingxi.core.llm.llm_client import LLMClient

        # 构造摘要提示
        if user_input:
            prompt = f"""请为以下对话结果生成简洁的摘要（50 字以内），保留关键信息：

用户问题：{user_input}

对话结果：{text[:2000] if len(text) > 2000 else text}

请用一句话总结核心内容，不要包含多余的解释。"""
        else:
            prompt = f"""请为以下文本生成简洁的摘要（50 字以内），保留关键信息：

{text[:2000] if len(text) > 2000 else text}

请用一句话总结核心内容，不要包含多余的解释。"""

        # 创建 LLM 客户端并调用
        llm_client = LLMClient(self.config)
        
        try:
            summary = llm_client.complete(prompt, task_level="simple")
            
            # 清理摘要：去除多余空白和引号
            summary = str(summary).strip().strip('"').strip("'")
            
            # 确保摘要不会太长
            if len(summary) > 100:
                summary = summary[:97] + "..."
            
            self.logger.debug(f"LLM 摘要生成成功：{summary[:50]}...")
            return f"[LLM 摘要] {summary}"
            
        except Exception as e:
            self.logger.error(f"LLM 摘要调用失败：{e}")
            # 抛出异常，让调用者处理降级
            raise

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

    def _save_to_db(self, session_id: str, history: List[Dict[str, Any]]):
        """保存会话历史到数据库（已废弃，保留向后兼容）"""
        pass

    def _save_task_list_to_db(self, session_id: str, task_list: Dict[str, Any]):
        """保存任务列表到数据库（已废弃，保留向后兼容）"""
        pass

    def save_checkpoint(self, session_id: str, state: Dict[str, Any]):
        """保存检查点

        Args:
            session_id: 会话ID
            state: 状态字典
        """
        checkpoint_json = json.dumps(state, ensure_ascii=False)
        sql = """
            UPDATE sessions SET checkpoint_json = ?, updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """
        self.db_manager.execute_sql(sql, (checkpoint_json, session_id))
        self.logger.debug(f"检查点已保存，session_id: {session_id}")

    def restore_checkpoint(self, session_id: str) -> Optional[Dict[str, Any]]:
        """恢复检查点

        Args:
            session_id: 会话ID

        Returns:
            状态字典
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT checkpoint_json FROM sessions WHERE session_id = ?
        """, (session_id,))

        row = cursor.fetchone()
        conn.close()

        if row and row[0]:
            try:
                return json.loads(row[0])
            except json.JSONDecodeError:
                self.logger.error(f"检查点数据解析失败，session_id: {session_id}")

        return None

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

    def get_checkpoint_status(self, session_id: str) -> Dict[str, Any]:
        """获取检查点状态

        Args:
            session_id: 会话ID

        Returns:
            检查点状态字典
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT checkpoint_json, updated_at FROM sessions WHERE session_id = ?
        """, (session_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "session_id": session_id,
                "has_checkpoint": row[0] is not None,
                "checkpoint_updated_at": row[1],
                "checkpoint_size": len(row[0]) if row[0] else 0
            }

        return {
            "session_id": session_id,
            "has_checkpoint": False,
            "checkpoint_updated_at": None,
            "checkpoint_size": 0
        }

    def clear_checkpoint(self, session_id: str):
        """清除检查点

        Args:
            session_id: 会话ID
        """
        sql = """
            UPDATE sessions SET checkpoint_json = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """
        self.db_manager.execute_sql(sql, (session_id,))
        self.logger.debug(f"检查点已清除，session_id: {session_id}")

    def cleanup_expired_checkpoints(self, ttl_hours: int = 24) -> int:
        """清理过期检查点

        Args:
            ttl_hours: 生存时间（小时）

        Returns:
            清理的检查点数量
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT session_id, updated_at FROM sessions
            WHERE checkpoint_json IS NOT NULL
        """)

        expired_sessions = []
        for row in cursor.fetchall():
            session_id, updated_at = row
            if isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at)

            age_hours = (datetime.now() - updated_at).total_seconds() / 3600
            if age_hours > ttl_hours:
                expired_sessions.append(session_id)

        for session_id in expired_sessions:
            cursor.execute("""
                UPDATE sessions SET checkpoint_json = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE session_id = ?
            """, (session_id,))

        conn.commit()
        conn.close()

        self.logger.debug(f"已清理 {len(expired_sessions)} 个过期检查点")
        return len(expired_sessions)

    def list_active_checkpoints(self) -> List[Dict[str, Any]]:
        """列出所有活跃检查点

        Returns:
            检查点列表
        """
        conn = self.db_manager.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT session_id, checkpoint_json, updated_at FROM sessions
            WHERE checkpoint_json IS NOT NULL
            ORDER BY updated_at DESC
        """)

        rows = cursor.fetchall()
        conn.close()

        checkpoints = []
        for row in rows:
            session_id, checkpoint_json, updated_at = row
            try:
                state = json.loads(checkpoint_json)
                checkpoints.append({
                    "session_id": session_id,
                    "state": state,
                    "updated_at": updated_at,
                    "size": len(checkpoint_json)
                })
            except json.JSONDecodeError:
                self.logger.error(f"检查点数据解析失败，session_id: {session_id}")

        return checkpoints

    def get_context_for_llm(self) -> List[Dict[str, str]]:
        """获取用于 LLM 的上下文

        Returns:
            上下文列表
        """
        return self.context_manager.get_context_for_llm()

    def get_context_stats(self) -> Dict[str, Any]:
        """获取上下文统计信息

        Returns:
            统计信息字典
        """
        return self.context_manager.get_context_stats()

    def set_current_task(self, task_id: str):
        """设置当前任务

        Args:
            task_id: 任务ID
        """
        sql = """
            UPDATE sessions SET current_task_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """
        self.db_manager.execute_sql(sql, (task_id, self.session_id))
        self.logger.debug(f"当前任务已设置，task_id: {task_id}")

    def compress_context(self, strategy: str = None) -> Dict[str, Any]:
        """压缩上下文

        Args:
            strategy: 压缩策略

        Returns:
            压缩结果字典
        """
        return self.context_manager.compress_context(strategy)

    def retrieve_relevant_history(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """检索相关历史

        Args:
            query: 查询字符串
            top_k: 返回数量

        Returns:
            相关历史列表
        """
        return self.context_manager.retrieve_relevant_history(query, top_k)

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
                    "session_id": session_id,
                    "title": title,
                    "message_count": task_count,
                    "first_message": first_message,
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
        # 注入 SOUL 到会话
        self._build_soul_and_memory(session_id);

        self.logger.debug(f"会话已创建，session_id: {session_id}, user_name: {user_name}")
        return session_id

    def _build_soul_and_memory(self,session_id: str) -> None :
        if self.soul_injector.soul_data:
            final_system_prompt = self.soul_injector.soul_content
            
            # 注入记忆到系统提示词
            if self.memory_manager.memories:
                memory_context = self._build_memory_context()
                if memory_context:
                    final_system_prompt += "\n\n# 用户记忆\n\n" + memory_context
                    self.logger.debug(f"已注入 {len(self.memory_manager.memories)} 条记忆到系统提示词")
            
            # 将会话的系统提示词存储到上下文管理器
            self.get_session_context(session_id).add_context_item("system", final_system_prompt)
            self.get_session_context(session_id).set_soul(final_system_prompt)
            self.logger.debug(f"SOUL 已注入到会话：{session_id}")    

    def _build_memory_context(self) -> str:
        """构建记忆上下文"""
        # 获取高重要性记忆
        important_memories = [
            m for m in self.memory_manager.memories.values()
            if m.importance >= 4
        ]
        
        if not important_memories:
            return ""
        
        # 按分类组织
        by_category = {}
        for memory in important_memories[:15]:  # 最多 15 条
            cat = memory.category
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(memory.content)
        
        # 生成上下文
        lines = []
        category_names = {
            "preference": "用户偏好",
            "fact": "重要事实",
            "decision": "历史决策"
        }
        
        for cat, contents in by_category.items():
            cat_name = category_names.get(cat, cat)
            lines.append(f"## {cat_name}")
            for content in contents:
                lines.append(f"- {content}")
            lines.append("")
        
        return "\n".join(lines)

    def end_session(self, session_id: str, auto_extract_memory: bool = True):
        """
        结束会话并提取记忆
        
        Args:
            session_id: 会话 ID
            auto_extract_memory: 是否自动提取记忆
        """
        # 获取会话历史（从任务管理器）
        session_history = self.task_manager.get_tasks_by_session(session_id)
        
        # 转换为记忆提取器需要的格式
        history_for_extraction = []
        for task in session_history:
            if task.get("user_input"):
                history_for_extraction.append({"role": "user", "content": task["user_input"]})
            if task.get("result"):
                history_for_extraction.append({"role": "assistant", "content": task["result"]})
        
        # 自动提取记忆
        if auto_extract_memory and history_for_extraction:
            try:
                memories = self.memory_extractor.extract_from_session(
                    history_for_extraction,
                    auto_save=True,
                    min_importance=3
                )
                self.logger.info(f"会话结束提取了 {len(memories)} 条记忆")
            except Exception as e:
                self.logger.error(f"提取记忆失败：{e}")
        
        # 保存 MEMORY.md
        try:
            self.memory_manager.save_to_file()
        except Exception as e:
            self.logger.error(f"保存 MEMORY.md 失败：{e}")

    def transaction(self):
        """事务上下文管理器（委托给数据库管理器）"""
        return self.db_manager.transaction

    @property
    def _get_connection(self):
        """获取数据库连接（委托给数据库管理器）"""
        return self.db_manager.get_connection

    @property
    def _execute_sql(self):
        """执行SQL语句（委托给数据库管理器）"""
        return self.db_manager.execute_sql

    @property
    def create_task(self):
        """创建任务（委托给任务管理器）"""
        return self.task_manager.create_task

    @property
    def get_task(self):
        """获取任务（委托给任务管理器）"""
        return self.task_manager.get_task

    @property
    def add_step(self):
        """添加步骤（委托给步骤管理器）"""
        return self.step_manager.add_step

    @property
    def set_task_result(self):
        """设置任务结果（委托给任务管理器）"""
        return self.task_manager.set_task_result

    @property
    def update_task_tokens(self):
        """更新任务Token（委托给任务管理器）"""
        return self.task_manager.update_task_tokens

    @property
    def get_task_tokens(self):
        """获取任务Token（委托给任务管理器）"""
        return self.task_manager.get_task_tokens

    @property
    def save_plan(self):
        """保存计划（委托给任务管理器）"""
        return self.task_manager.save_plan

    @property
    def restore_task(self):
        """恢复任务（委托给任务管理器）"""
        return self.task_manager.restore_task

    @property
    def update_task_progress(self):
        """更新任务进度（委托给任务管理器）"""
        return self.task_manager.update_task_progress

    @property
    def increment_replan_count(self):
        """增加重新规划次数（委托给任务管理器）"""
        return self.task_manager.increment_replan_count

    @property
    def set_task_error(self):
        """设置任务错误（委托给任务管理器）"""
        return self.task_manager.set_task_error
