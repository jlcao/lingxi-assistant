"""WebSocket 连接管理器模块"""

import asyncio
import logging
import uuid
from typing import Dict, Set, Any, Optional, Callable
from fastapi import WebSocket, WebSocketDisconnect

from lingxi.web.websocket_message import WebSocketMessage
from lingxi.web.websocket_connection import WebSocketConnection
from lingxi.core.assistant.async_main import AsyncLingxiAssistant
from lingxi.core.context.task_context_manager import TaskContextManager

logger = logging.getLogger(__name__)


class WebSocketManager:
    """WebSocket 连接管理器（增强版，支持异步）"""

    _instance = None  # 单例实例
    
    def __new__(cls, assistant: AsyncLingxiAssistant = None):
        """单例模式：确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, assistant: AsyncLingxiAssistant = None):
        # 防止重复初始化
        if hasattr(self, '_initialized'):
            return
        
        """初始化 WebSocket 管理器

        Args:
            assistant: 异步灵犀助手实例
        """
        self.active_connections: Dict[str, WebSocketConnection] = {}
        self.session_connections: Dict[str, Set[str]] = {}
        self.assistant = assistant
        # 设置 websocket_manager 引用到 assistant
        if assistant:
            assistant.websocket_manager = self
        self.connection_counter = 0
        self.stream_callbacks: Dict[str, Callable] = {}
        self.task_context_manager = TaskContextManager()
        self._initialized = True

    async def connect(self, websocket: WebSocket, session_id: str = None) -> str:
        """接受 WebSocket 连接

        Args:
            websocket: WebSocket 连接对象
            session_id: 会话 ID（从查询参数传入）

        Returns:
            连接 ID
        """
        self.connection_counter += 1
        connection_id = f"conn_{self.connection_counter}"

        connection = WebSocketConnection(websocket, connection_id)
        
        # 如果传入了 session_id，则使用它
        if session_id:
            connection.session_id = session_id
        self.active_connections[connection_id] = connection
        self.session_connections.setdefault(connection.session_id, set()).add(connection_id)

        logger.info(f"新 WebSocket 连接：{connection_id} (session: {connection.session_id})")
        await self._send_welcome(connection)

        return connection_id

    async def disconnect(self, connection_id: str):
        """断开 WebSocket 连接

        Args:
            connection_id: 连接 ID
        """
        if connection_id not in self.active_connections:
            return

        connection = self.active_connections[connection_id]
        connection.disconnect()

        session_id = connection.session_id
        self.session_connections[session_id].discard(connection_id)
        if not self.session_connections[session_id]:
            del self.session_connections[session_id]

        del self.active_connections[connection_id]
        logger.info(f"WebSocket 连接断开：{connection_id}")

    async def send_to_connection(self, connection_id: str, message: Dict[str, Any]):
        """发送消息到指定连接

        Args:
            connection_id: 连接 ID
            message: 消息内容
        """
        if connection_id not in self.active_connections:
            logger.warning(f"连接不存在：{connection_id}")
            return

        connection = self.active_connections[connection_id]
        try:
            await connection.send_json(message)
        except Exception as e:
            logger.error(f"发送消息失败：{e}")
            await self.disconnect(connection_id)

    async def send_to_session(self, session_id: str, message: Dict[str, Any], 
                             exclude_connection: str = None):
        """发送消息到会话的所有连接

        Args:
            session_id: 会话 ID
            message: 消息内容
            exclude_connection: 排除的连接 ID
        """
        if session_id not in self.session_connections:
            return

        for conn_id in self.session_connections[session_id]:
            if conn_id != exclude_connection:
                await self.send_to_connection(conn_id, message)

    async def broadcast(self, message: Dict[str, Any]):
        """广播消息给所有连接

        Args:
            message: 消息内容
        """
        for connection_id in list(self.active_connections.keys()):
            await self.send_to_connection(connection_id, message)

    async def handle_message(self, connection_id: str, data: Dict[str, Any]):
        """处理接收到的消息

        Args:
            connection_id: 连接 ID
            data: 消息数据
        """
        if connection_id not in self.active_connections:
            return

        connection = self.active_connections[connection_id]
        connection.update_activity()

        try:
            message_type = data.get('type', 'chat')

            if message_type == 'command':
                await self._handle_command_message(connection, data)
            elif message_type == 'stream_chat':
                # 使用 create_task 实现并发处理，避免阻塞消息接收
                asyncio.create_task(self._handle_stream_chat(connection, data))
            elif message_type == 'stop_task':
                await self._handle_stop_task(connection, data)
            elif message_type == 'session':
                await self._handle_session_message(connection, data)
            elif message_type == 'checkpoint':
                await self._handle_checkpoint_message(connection, data)
            elif message_type == 'skill':
                await self._handle_skill_message(connection, data)
            elif message_type == 'context':
                await self._handle_context_message(connection, data)
            elif message_type == 'ping':
                await self._handle_ping(connection)
            else:
                await self._send_error(connection, f"未知消息类型：{message_type}")

        except Exception as e:
            logger.error(f"处理消息失败：{e}", exc_info=True)
            await self._send_error(connection, f"处理消息失败：{str(e)}")

    async def _handle_stream_chat(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """处理流式聊天消息

        Args:
            connection: WebSocket 连接
            data: 消息数据
        """
        message = data.get('content', '')
        # 兼容前端发送的 sessionId 和 session_id 字段
        session_id = data.get('sessionId') or data.get('session_id', connection.session_id)
        # 获取前端发送的 thinkingMode 参数
        thinking_mode = data.get('thinkingMode', False)

        if not message:
            await self._send_error(connection, "消息内容不能为空")
            return

        connection.session_id = session_id
        self.session_connections.setdefault(session_id, set()).add(connection.connection_id)

        try:
            await self._send_stream_response(connection, message, session_id, thinking_mode)
        except Exception as e:
            logger.error(f"处理流式聊天失败：{e}", exc_info=True)
            await self._send_error(connection, f"处理流式聊天失败：{str(e)}")

    async def _handle_stop_task(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """处理终止任务消息

        Args:
            connection: WebSocket 连接
            data: 消息数据
        """
        task_id = data.get('taskId') or data.get('task_id')
        
        if not task_id:
            await self._send_error(connection, "taskId 不能为空")
            return

        try:
            success = await self.task_context_manager.stop_task(task_id)
            if success:
                await self._send_success(connection, {"task_id": task_id, "message": "任务已终止"})
            else:
                await self._send_error(connection, "任务不存在或已完成")
        except Exception as e:
            logger.error(f"终止任务失败: {e}", exc_info=True)
            await self._send_error(connection, f"终止任务失败: {str(e)}")

    async def _handle_command_message(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """处理命令消息

        Args:
            connection: WebSocket 连接
            data: 消息数据
        """
        command = data.get('command', '')
        session_id = data.get('session_id', connection.session_id)
        args = data.get('args', {})

        if not command:
            await self._send_error(connection, "命令不能为空")
            return

        connection.session_id = session_id

        try:
            result = await self._execute_command(connection, command, session_id, args)
            await self._send_command_response(connection, command, result)
        except Exception as e:
            logger.error(f"执行命令失败：{e}", exc_info=True)
            await self._send_error(connection, f"执行命令失败：{str(e)}")

    async def _handle_session_message(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """处理会话消息

        Args:
            connection: WebSocket 连接
            data: 消息数据
        """
        action = data.get('action', '')
        session_id = data.get('session_id', connection.session_id)

        if action == 'switch':
            new_session_id = data.get('new_session_id')
            if new_session_id:
                connection.session_id = new_session_id
                self.session_connections.setdefault(new_session_id, set()).add(connection.connection_id)
                await self._send_success(connection, f"已切换到会话：{new_session_id}")
        elif action == 'clear':
            self.assistant.session_manager.clear_session(session_id)
            await self._send_success(connection, "会话已清空")
        elif action == 'list':
            sessions = self.assistant.session_manager.list_all_sessions()
            await self._send_success(connection, {"sessions": sessions})
        elif action == 'info':
            info = self.assistant.session_manager.get_session_info(session_id)
            await self._send_success(connection, {"session_info": info})
        elif action == 'rename':
            new_title = data.get('new_title', '')
            if new_title:
                success = self.assistant.session_manager.rename_session(session_id, new_title)
                if success:
                    await self._send_success(connection, f"会话已重命名为：{new_title}")
                else:
                    await self._send_error(connection, "重命名失败")
            else:
                await self._send_error(connection, "新标题不能为空")
        elif action == 'delete':
            success = self.assistant.session_manager.delete_session(session_id)
            if success:
                if connection.session_id == session_id:
                    connection.session_id = f"session_{uuid.uuid4().hex[:8]}"
                await self._send_success(connection, f"会话已删除：{session_id}")
            else:
                await self._send_error(connection, "删除失败或会话不存在")
        else:
            await self._send_error(connection, f"未知会话操作：{action}")

    async def _handle_checkpoint_message(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """处理检查点消息

        Args:
            connection: WebSocket 连接
            data: 消息数据
        """
        action = data.get('action', '')
        session_id = data.get('session_id', connection.session_id)

        if action == 'status':
            status = self.assistant.session_manager.get_checkpoint_status(session_id)
            await self._send_success(connection, {"checkpoint_status": status})
        elif action == 'clear':
            self.assistant.session_manager.clear_checkpoint(session_id)
            await self._send_success(connection, "检查点已清除")
        elif action == 'list':
            checkpoints = self.assistant.session_manager.list_active_checkpoints()
            await self._send_success(connection, {"checkpoints": checkpoints})
        elif action == 'cleanup':
            ttl_hours = data.get('ttl_hours', 24)
            count = self.assistant.session_manager.cleanup_expired_checkpoints(ttl_hours)
            await self._send_success(connection, {"cleaned_count": count})
        else:
            await self._send_error(connection, f"未知检查点操作：{action}")

    async def _handle_skill_message(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """处理技能消息

        Args:
            connection: WebSocket 连接
            data: 消息数据
        """
        action = data.get('action', '')

        if action == 'list':
            skills = self.assistant.action_caller.list_available_skills(enabled_only=True)
            await self._send_success(connection, {"skills": skills})
        elif action == 'install':
            skill_source = data.get('skill_source')
            skill_name = data.get('skill_name')
            overwrite = data.get('overwrite', False)

            if not skill_source:
                await self._send_error(connection, "技能源路径不能为空")
                return
            
            # 使用 create_task 实现并发处理，避免阻塞消息接收
            asyncio.create_task(self._install_skill_async(connection, skill_source, skill_name, overwrite))
        else:
            await self._send_error(connection, f"未知技能操作：{action}")

    async def _handle_context_message(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """处理上下文消息

        Args:
            connection: WebSocket 连接
            data: 消息数据
        """
        action = data.get('action', '')
        session_id = data.get('session_id', connection.session_id)

        if action == 'stats':
            stats = self.assistant.session_manager.get_context_stats()
            await self._send_success(connection, {"context_stats": stats})
        elif action == 'compress':
            strategy = data.get('strategy')
            stats = self.assistant.session_manager.compress_context(strategy)
            await self._send_success(connection, {"compression_stats": stats})
        elif action == 'search':
            query = data.get('query')
            top_k = data.get('top_k', 5)
            if not query:
                await self._send_error(connection, "查询文本不能为空")
                return
            results = self.assistant.session_manager.retrieve_relevant_history(query, top_k)
            await self._send_success(connection, {"search_results": results})
        else:
            await self._send_error(connection, f"未知上下文操作：{action}")

    async def _install_skill_async(self, connection: WebSocketConnection, skill_source: str, skill_name: str, overwrite: bool):
        """异步安装技能

        Args:
            connection: WebSocket 连接
            skill_source: 技能源路径
            skill_name: 技能名称
            overwrite: 是否覆盖
        """
        try:
            success = await self.assistant.install_skill_async(skill_source, skill_name, overwrite)
            if success:
                await self._send_success(connection, f"技能安装成功：{skill_source}")
            else:
                await self._send_error(connection, f"技能安装失败：{skill_source}")
        except Exception as e:
            logger.error(f"异步安装技能失败：{e}", exc_info=True)
            await self._send_error(connection, f"技能安装异常：{str(e)}")

    async def _handle_ping(self, connection: WebSocketConnection):
        """处理 ping 消息

        Args:
            connection: WebSocket 连接
        """
        await self._send_success(connection, {"pong": True})

    async def _execute_command(self, connection: WebSocketConnection, command: str, 
                               session_id: str, args: Dict) -> Any:
        """执行命令

        Args:
            connection: WebSocket 连接
            command: 命令
            session_id: 会话 ID
            args: 参数

        Returns:
            执行结果
        """
        if command == 'help':
            return {
                "available_commands": [
                    {"command": "help", "description": "显示帮助"},
                    {"command": "clear", "description": "清空当前会话"},
                    {"command": "status", "description": "显示检查点状态"},
                    {"command": "skills", "description": "列出可用技能"},
                    {"command": "install", "description": "安装技能"},
                    {"command": "context-stats", "description": "显示上下文统计"},
                    {"command": "compress", "description": "手动触发上下文压缩"},
                    {"command": "search", "description": "检索相关历史"},
                    {"command": "session", "description": "创建或切换会话"}
                ]
            }
        elif command == 'clear':
            self.assistant.session_manager.clear_session(session_id)
            return "会话已清空"
        elif command == 'status':
            return self.assistant.session_manager.get_checkpoint_status(session_id)
        elif command == 'skills':
            return self.assistant.action_caller.list_available_skills(enabled_only=True)
        elif command == 'context-stats':
            return self.assistant.session_manager.get_context_stats()
        elif command == 'compress':
            strategy = args.get('strategy')
            return self.assistant.session_manager.compress_context(strategy)
        elif command == 'search':
            query = args.get('query')
            top_k = args.get('top_k', 5)
            return self.assistant.session_manager.retrieve_relevant_history(query, top_k)
        elif command == 'session':
            new_session_id = args.get('session_id')
            if new_session_id:
                connection.session_id = new_session_id
                self.session_connections.setdefault(new_session_id, set()).add(connection.connection_id)
                return f"已切换到会话：{new_session_id}"
            else:
                new_session_id = f"session_{uuid.uuid4().hex[:8]}"
                connection.session_id = new_session_id
                self.session_connections.setdefault(new_session_id, set()).add(connection.connection_id)
                return f"创建新会话：{new_session_id}"
        else:
            raise ValueError(f"未知命令：{command}")

    async def _send_welcome(self, connection: WebSocketConnection):
        """发送欢迎消息

        Args:
            connection: WebSocket 连接
        """
        welcome_msg = WebSocketMessage.create_response(
            "welcome",
            {
                "message": f"欢迎使用{self.assistant.config.get('system', {}).get('name', '灵犀')}智能助手！",
                "version": self.assistant.config.get('system', {}).get('version', '0.2.0'),
                "connection_id": connection.connection_id,
                "session_id": connection.session_id
            }
        )
        await connection.send_json(welcome_msg)

    async def _send_chat_response(self, connection: WebSocketConnection, response: str, session_id: str):
        """发送聊天响应

        Args:
            connection: WebSocket 连接
            response: 响应内容
            session_id: 会话 ID
        """
        response_msg = WebSocketMessage.create_response(
            "chat",
            {
                "content": response,
                "session_id": session_id
            }
        )
        success = await connection.send_json(response_msg)
        if not success:
            logger.debug(f"发送聊天响应失败，连接可能已断开")

    async def _send_stream_response(self, connection: WebSocketConnection, message: str, session_id: str, thinking_mode: bool = False):
        """发送流式响应

        使用完全异步的助手类，直接 await 异步生成器：
        1. 调用异步助手的 stream_process_input 方法
        2. 直接遍历异步生成器并发送消息
        3. 完全非阻塞，支持高并发

        Args:
            connection: WebSocket 连接
            message: 消息内容
            session_id: 会话 ID
            thinking_mode: 是否开启思考模式
        """
        try:
            # 调用异步助手，获取异步生成器
            # 注意：stream_process_input 是异步生成器函数，直接返回异步生成器对象
            response_generator = self.assistant.stream_process_input(message, session_id, thinking_mode)
            
            # 遍历异步生成器并发送消息
            async for chunk in response_generator:
                await connection.send_json(chunk)
                
        except Exception as e:
            logger.error(f"流式响应失败：{e}", exc_info=True)
            if connection.is_connected:
                error_msg = WebSocketMessage.create_error("stream_error", f"流式响应失败：{str(e)}")
                await connection.send_json(error_msg)

    async def _send_command_response(self, connection: WebSocketConnection, command: str, result: Any):
        """发送命令响应

        Args:
            connection: WebSocket 连接
            command: 命令
            result: 结果
        """
        response_msg = WebSocketMessage.create_response(
            "command",
            {
                "command": command,
                "result": result
            }
        )
        success = await connection.send_json(response_msg)
        if not success:
            logger.debug(f"发送命令响应失败，连接可能已断开")

    async def _send_success(self, connection: WebSocketConnection, data: Any):
        """发送成功消息

        Args:
            connection: WebSocket 连接
            data: 数据
        """
        response_msg = WebSocketMessage.create_response("success", data)
        success = await connection.send_json(response_msg)
        if not success:
            logger.debug(f"发送成功消息失败，连接可能已断开")

    async def _send_error(self, connection: WebSocketConnection, error: str, details: str = None):
        """发送错误消息

        Args:
            connection: WebSocket 连接
            error: 错误信息
            details: 详细信息
        """
        error_msg = WebSocketMessage.create_error("error", error, details)
        success = await connection.send_json(error_msg)
        if not success:
            logger.debug(f"发送错误消息失败，连接可能已断开")

    def _list_sessions(self) -> list:
        """列出所有会话

        Returns:
            会话列表
        """
        return list(self.session_connections.keys())

    def get_connection_count(self) -> int:
        """获取连接数

        Returns:
            连接数
        """
        return len(self.active_connections)

    def get_session_count(self) -> int:
        """获取会话数

        Returns:
            会话数
        """
        return len(self.session_connections)

    async def send_thought_chain_event(self, session_id: str, execution_id: str, thoughts: list):
        """发送思维链事件

        Args:
            session_id: 会话 ID
            execution_id: 执行 ID
            thoughts: 思维链列表
        """
        # 转换为前端期望的格式
        for thought in thoughts:
            # 处理 plan_react_core.py 发送的格式（包含 step 和 description 字段）
            if "step" in thought and "description" in thought:
                event = {
                    "choices": [{
                        "delta": {
                            "thought": f"步骤 {thought['step']}: {thought['description']}",
                            "action": None
                        }
                    }]
                }
            else:
                # 处理其他格式（包含 thought 和 action 字段）
                event = {
                    "choices": [{
                        "delta": {
                            "thought": thought.get("thought", ""),
                            "action": thought.get("action", None)
                        }
                    }]
                }
            await self.send_to_session(session_id, event)

    async def send_event(self, session_id: str, event_type: str, execution_id: str, task_id: str = None, step_index: int = None, data: dict = None):
        """发送事件

        Args:
            session_id: 会话 ID
            event_type: 事件类型
            execution_id: 执行 ID
            task_id: 任务 ID
            step_index: 步骤索引
            data: 事件数据
        """
        if data is None:
            data = {}
        if task_id:
            data['task_id'] = task_id
        if step_index is not None:
            data['step_index'] = step_index
        event = {
            "type": event_type,
            "payload": {
                "executionId": execution_id,
                "sessionId": session_id,
                "taskId": task_id,
                "stepIndex": step_index,
                **data
            }
        }
        await self.send_to_session(session_id, event)

    async def send_step_status_event(self, session_id: str, execution_id: str, step_index: int, 
                                     status: str, error: str = None):
        """发送步骤状态事件

        Args:
            session_id: 会话 ID
            execution_id: 执行 ID
            step_index: 步骤索引
            status: 状态
            error: 错误信息
        """
        event = {
            "type": "step_status",
            "payload": {
                "executionId": execution_id,
                "stepIndex": step_index,
                "status": status,
                "error": error
            }
        }
        await self.send_to_session(session_id, event)

    async def send_skill_call_event(self, session_id: str, execution_id: str, skill_id: str, 
                                   parameters: dict, result: dict):
        """发送技能调用事件

        Args:
            session_id: 会话 ID
            execution_id: 执行 ID
            skill_id: 技能 ID
            parameters: 参数
            result: 结果
        """
        event = {
            "type": "skill_call",
            "payload": {
                "executionId": execution_id,
                "skillId": skill_id,
                "parameters": parameters,
                "result": result
            }
        }
        await self.send_to_session(session_id, event)

    async def send_resource_update_event(self, cpu_percent: float, memory_percent: float, 
                                        disk_percent: float, token_usage: dict):
        """发送资源更新事件

        Args:
            cpu_percent: CPU 使用率
            memory_percent: 内存使用率
            disk_percent: 磁盘使用率
            token_usage: Token 使用情况
        """
        event = {
            "type": "resource_update",
            "payload": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent,
                "token_usage": token_usage
            }
        }
        await self.broadcast(event)

    async def send_model_route_event(self, session_id: str, task_level: str, selected_model: str, 
                                     reason: str, estimated_tokens: int = None):
        """发送模型路由事件

        Args:
            session_id: 会话 ID
            task_level: 任务级别
            selected_model: 选择的模型
            reason: 原因
            estimated_tokens: 预估 Token 数
        """
        event = {
            "type": "model_route",
            "payload": {
                "task_level": task_level,
                "selected_model": selected_model,
                "reason": reason,
                "estimated_tokens": estimated_tokens
            }
        }
        await self.send_to_session(session_id, event)

    async def send_task_completed_event(self, session_id: str, execution_id: str, task: str, 
                                        result: dict):
        """发送任务完成事件

        Args:
            session_id: 会话 ID
            execution_id: 执行 ID
            task: 任务
            result: 结果
        """
        event = {
            "type": "task_completed",
            "payload": {
                "executionId": execution_id,
                "task": task,
                "status": "completed",
                "result": result,
                "timestamp": asyncio.get_event_loop().time()
            }
        }
        await self.send_to_session(session_id, event)

    async def send_task_failed_event(self, session_id: str, execution_id: str, task: str, 
                                      error: dict):
        """发送任务失败事件

        Args:
            session_id: 会话 ID
            execution_id: 执行 ID
            task: 任务
            error: 错误信息
        """
        event = {
            "type": "task_failed",
            "payload": {
                "executionId": execution_id,
                "task": task,
                "status": "failed",
                "error": error
            }
        }
        await self.send_to_session(session_id, event)
