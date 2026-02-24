import logging
import json
import asyncio
from typing import Dict, Set, Any, Optional, Callable
from fastapi import WebSocket, WebSocketDisconnect
from lingxi.__main__ import LingxiAssistant

logger = logging.getLogger(__name__)


class WebSocketMessage:
    """WebSocket消息协议"""

    @staticmethod
    def create_response(message_type: str, data: Dict[str, Any], success: bool = True) -> Dict[str, Any]:
        """创建响应消息

        Args:
            message_type: 消息类型
            data: 消息数据
            success: 是否成功

        Returns:
            响应消息
        """
        return {
            "type": message_type,
            "success": success,
            "data": data,
            "timestamp": asyncio.get_event_loop().time()
        }

    @staticmethod
    def create_stream_chunk(message_type: str, content: str, chunk_index: int, 
                           is_last: bool = False, metadata: Dict = None) -> Dict[str, Any]:
        """创建流式消息块

        Args:
            message_type: 消息类型
            content: 内容
            chunk_index: 块索引
            is_last: 是否最后一块
            metadata: 元数据

        Returns:
            流式消息块
        """
        return {
            "type": message_type,
            "stream": True,
            "chunk_index": chunk_index,
            "is_last": is_last,
            "content": content,
            "metadata": metadata or {},
            "timestamp": asyncio.get_event_loop().time()
        }

    @staticmethod
    def create_error(message_type: str, error: str, details: str = None) -> Dict[str, Any]:
        """创建错误消息

        Args:
            message_type: 消息类型
            error: 错误信息
            details: 详细信息

        Returns:
            错误消息
        """
        return {
            "type": message_type,
            "success": False,
            "error": error,
            "details": details,
            "timestamp": asyncio.get_event_loop().time()
        }


class WebSocketConnection:
    """WebSocket连接封装"""

    def __init__(self, websocket: WebSocket, connection_id: str):
        """初始化连接

        Args:
            websocket: WebSocket对象
            connection_id: 连接ID
        """
        self.websocket = websocket
        self.connection_id = connection_id
        self.session_id = "default"
        self.is_connected = True
        self.last_activity = asyncio.get_event_loop().time()

    async def send_json(self, data: Dict[str, Any]):
        """发送JSON消息

        Args:
            data: 消息数据

        Returns:
            是否发送成功
        """
        if not self.is_connected:
            return False
        try:
            await self.websocket.send_json(data)
            self.last_activity = asyncio.get_event_loop().time()
            return True
        except Exception as e:
            logger.debug(f"发送JSON消息失败: {e}")
            self.is_connected = False
            return False

    async def send_text(self, text: str):
        """发送文本消息

        Args:
            text: 文本内容

        Returns:
            是否发送成功
        """
        if not self.is_connected:
            return False
        try:
            await self.websocket.send_text(text)
            self.last_activity = asyncio.get_event_loop().time()
            return True
        except Exception as e:
            logger.debug(f"发送文本消息失败: {e}")
            self.is_connected = False
            return False

    def update_activity(self):
        """更新活动时间"""
        self.last_activity = asyncio.get_event_loop().time()

    def disconnect(self):
        """断开连接"""
        self.is_connected = False


class WebSocketManager:
    """WebSocket连接管理器（增强版）"""

    def __init__(self, assistant: LingxiAssistant):
        """初始化WebSocket管理器

        Args:
            assistant: 灵犀助手实例
        """
        self.active_connections: Dict[str, WebSocketConnection] = {}
        self.session_connections: Dict[str, Set[str]] = {}
        self.assistant = assistant
        self.connection_counter = 0
        self.stream_callbacks: Dict[str, Callable] = {}

    async def connect(self, websocket: WebSocket) -> str:
        """接受WebSocket连接

        Args:
            websocket: WebSocket连接对象

        Returns:
            连接ID
        """
        await websocket.accept()
        self.connection_counter += 1
        connection_id = f"conn_{self.connection_counter}"

        connection = WebSocketConnection(websocket, connection_id)
        self.active_connections[connection_id] = connection
        self.session_connections.setdefault(connection.session_id, set()).add(connection_id)

        logger.info(f"新WebSocket连接: {connection_id}")
        await self._send_welcome(connection)

        return connection_id

    async def disconnect(self, connection_id: str):
        """断开WebSocket连接

        Args:
            connection_id: 连接ID
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
        logger.info(f"WebSocket连接断开: {connection_id}")

    async def send_to_connection(self, connection_id: str, message: Dict[str, Any]):
        """发送消息到指定连接

        Args:
            connection_id: 连接ID
            message: 消息内容
        """
        if connection_id not in self.active_connections:
            logger.warning(f"连接不存在: {connection_id}")
            return

        connection = self.active_connections[connection_id]
        try:
            await connection.send_json(message)
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            await self.disconnect(connection_id)

    async def send_to_session(self, session_id: str, message: Dict[str, Any], 
                             exclude_connection: str = None):
        """发送消息到会话的所有连接

        Args:
            session_id: 会话ID
            message: 消息内容
            exclude_connection: 排除的连接ID
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
            connection_id: 连接ID
            data: 消息数据
        """
        if connection_id not in self.active_connections:
            return

        connection = self.active_connections[connection_id]
        connection.update_activity()

        try:
            message_type = data.get('type', 'chat')

            if message_type == 'chat':
                await self._handle_chat_message(connection, data)
            elif message_type == 'command':
                await self._handle_command_message(connection, data)
            elif message_type == 'stream_chat':
                await self._handle_stream_chat(connection, data)
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
                await self._send_error(connection, f"未知消息类型: {message_type}")

        except Exception as e:
            logger.error(f"处理消息失败: {e}", exc_info=True)
            await self._send_error(connection, f"处理消息失败: {str(e)}")

    async def _handle_chat_message(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """处理聊天消息

        Args:
            connection: WebSocket连接
            data: 消息数据
        """
        message = data.get('content', '')
        session_id = data.get('session_id', connection.session_id)

        if not message:
            await self._send_error(connection, "消息内容不能为空")
            return

        connection.session_id = session_id
        self.session_connections.setdefault(session_id, set()).add(connection.connection_id)

        try:
            response = self.assistant.process_input(message, session_id)
            await self._send_chat_response(connection, response, session_id)
        except Exception as e:
            logger.error(f"处理聊天消息失败: {e}", exc_info=True)
            await self._send_error(connection, f"处理消息失败: {str(e)}")

    async def _handle_stream_chat(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """处理流式聊天消息

        Args:
            connection: WebSocket连接
            data: 消息数据
        """
        message = data.get('content', '')
        session_id = data.get('session_id', connection.session_id)

        if not message:
            await self._send_error(connection, "消息内容不能为空")
            return

        connection.session_id = session_id
        self.session_connections.setdefault(session_id, set()).add(connection.connection_id)

        try:
            await self._send_stream_response(connection, message, session_id)
        except Exception as e:
            logger.error(f"处理流式聊天失败: {e}", exc_info=True)
            await self._send_error(connection, f"处理流式聊天失败: {str(e)}")

    async def _handle_command_message(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """处理命令消息

        Args:
            connection: WebSocket连接
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
            logger.error(f"执行命令失败: {e}", exc_info=True)
            await self._send_error(connection, f"执行命令失败: {str(e)}")

    async def _handle_session_message(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """处理会话消息

        Args:
            connection: WebSocket连接
            data: 消息数据
        """
        action = data.get('action', '')
        session_id = data.get('session_id', connection.session_id)

        if action == 'switch':
            new_session_id = data.get('new_session_id')
            if new_session_id:
                connection.session_id = new_session_id
                self.session_connections.setdefault(new_session_id, set()).add(connection.connection_id)
                await self._send_success(connection, f"已切换到会话: {new_session_id}")
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
                    await self._send_success(connection, f"会话已重命名为: {new_title}")
                else:
                    await self._send_error(connection, "重命名失败")
            else:
                await self._send_error(connection, "新标题不能为空")
        elif action == 'delete':
            success = self.assistant.session_manager.delete_session(session_id)
            if success:
                if connection.session_id == session_id:
                    import uuid
                    connection.session_id = f"session_{uuid.uuid4().hex[:8]}"
                await self._send_success(connection, f"会话已删除: {session_id}")
            else:
                await self._send_error(connection, "删除失败或会话不存在")
        else:
            await self._send_error(connection, f"未知会话操作: {action}")

    async def _handle_checkpoint_message(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """处理检查点消息

        Args:
            connection: WebSocket连接
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
            await self._send_error(connection, f"未知检查点操作: {action}")

    async def _handle_skill_message(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """处理技能消息

        Args:
            connection: WebSocket连接
            data: 消息数据
        """
        action = data.get('action', '')

        if action == 'list':
            skills = self.assistant.skill_caller.list_available_skills(enabled_only=True)
            await self._send_success(connection, {"skills": skills})
        elif action == 'install':
            skill_source = data.get('skill_source')
            skill_name = data.get('skill_name')
            overwrite = data.get('overwrite', False)

            if not skill_source:
                await self._send_error(connection, "技能源路径不能为空")
                return

            success = self.assistant.install_skill(skill_source, skill_name, overwrite)
            if success:
                await self._send_success(connection, f"技能安装成功: {skill_source}")
            else:
                await self._send_error(connection, f"技能安装失败: {skill_source}")
        else:
            await self._send_error(connection, f"未知技能操作: {action}")

    async def _handle_context_message(self, connection: WebSocketConnection, data: Dict[str, Any]):
        """处理上下文消息

        Args:
            connection: WebSocket连接
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
            await self._send_error(connection, f"未知上下文操作: {action}")

    async def _handle_ping(self, connection: WebSocketConnection):
        """处理ping消息

        Args:
            connection: WebSocket连接
        """
        await self._send_success(connection, {"pong": True})

    async def _execute_command(self, connection: WebSocketConnection, command: str, 
                               session_id: str, args: Dict) -> Any:
        """执行命令

        Args:
            connection: WebSocket连接
            command: 命令
            session_id: 会话ID
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
            return self.assistant.skill_caller.list_available_skills(enabled_only=True)
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
                return f"已切换到会话: {new_session_id}"
            else:
                import uuid
                new_session_id = f"session_{uuid.uuid4().hex[:8]}"
                connection.session_id = new_session_id
                self.session_connections.setdefault(new_session_id, set()).add(connection.connection_id)
                return f"创建新会话: {new_session_id}"
        else:
            raise ValueError(f"未知命令: {command}")

    async def _send_welcome(self, connection: WebSocketConnection):
        """发送欢迎消息

        Args:
            connection: WebSocket连接
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
            connection: WebSocket连接
            response: 响应内容
            session_id: 会话ID
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

    async def _send_stream_response(self, connection: WebSocketConnection, message: str, session_id: str):
        """发送流式响应

        Args:
            connection: WebSocket连接
            message: 消息内容
            session_id: 会话ID
        """
        start_msg = WebSocketMessage.create_response(
            "stream_start",
            {"session_id": session_id}
        )
        if not await connection.send_json(start_msg):
            logger.debug(f"发送流式开始消息失败，连接可能已断开")
            return

        try:
            response = self.assistant.process_input(message, session_id)

            chunk_size = 100
            for i in range(0, len(response), chunk_size):
                chunk = response[i:i + chunk_size]
                is_last = i + chunk_size >= len(response)
                chunk_msg = WebSocketMessage.create_stream_chunk(
                    "stream_chunk",
                    chunk,
                    i // chunk_size,
                    is_last
                )
                if not await connection.send_json(chunk_msg):
                    logger.debug(f"发送流式数据块失败，连接可能已断开")
                    return
                await asyncio.sleep(0.01)

            end_msg = WebSocketMessage.create_response(
                "stream_end",
                {"session_id": session_id}
            )
            await connection.send_json(end_msg)
        except Exception as e:
            logger.error(f"流式响应处理失败: {e}", exc_info=True)

    async def _send_command_response(self, connection: WebSocketConnection, command: str, result: Any):
        """发送命令响应

        Args:
            connection: WebSocket连接
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
            connection: WebSocket连接
            data: 数据
        """
        response_msg = WebSocketMessage.create_response("success", data)
        success = await connection.send_json(response_msg)
        if not success:
            logger.debug(f"发送成功消息失败，连接可能已断开")

    async def _send_error(self, connection: WebSocketConnection, error: str, details: str = None):
        """发送错误消息

        Args:
            connection: WebSocket连接
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
            session_id: 会话ID
            execution_id: 执行ID
            thoughts: 思维链列表
        """
        event = {
            "event_type": "thought_chain",
            "data": {
                "execution_id": execution_id,
                "thoughts": thoughts
            }
        }
        await self.send_to_session(session_id, event)

    async def send_step_status_event(self, session_id: str, execution_id: str, step_index: int, 
                                     status: str, error: str = None):
        """发送步骤状态事件

        Args:
            session_id: 会话ID
            execution_id: 执行ID
            step_index: 步骤索引
            status: 状态
            error: 错误信息
        """
        event = {
            "event_type": "step_status",
            "data": {
                "execution_id": execution_id,
                "step_index": step_index,
                "status": status,
                "error": error,
                "timestamp": asyncio.get_event_loop().time()
            }
        }
        await self.send_to_session(session_id, event)

    async def send_skill_call_event(self, session_id: str, execution_id: str, skill_id: str, 
                                   parameters: dict, result: dict):
        """发送技能调用事件

        Args:
            session_id: 会话ID
            execution_id: 执行ID
            skill_id: 技能ID
            parameters: 参数
            result: 结果
        """
        event = {
            "event_type": "skill_call",
            "data": {
                "execution_id": execution_id,
                "skill_id": skill_id,
                "parameters": parameters,
                "result": result,
                "timestamp": asyncio.get_event_loop().time()
            }
        }
        await self.send_to_session(session_id, event)

    async def send_resource_update_event(self, cpu_percent: float, memory_percent: float, 
                                        disk_percent: float, token_usage: dict):
        """发送资源更新事件

        Args:
            cpu_percent: CPU使用率
            memory_percent: 内存使用率
            disk_percent: 磁盘使用率
            token_usage: Token使用情况
        """
        event = {
            "event_type": "resource_update",
            "data": {
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
            session_id: 会话ID
            task_level: 任务级别
            selected_model: 选择的模型
            reason: 原因
            estimated_tokens: 预估Token数
        """
        event = {
            "event_type": "model_route",
            "data": {
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
            session_id: 会话ID
            execution_id: 执行ID
            task: 任务
            result: 结果
        """
        event = {
            "event_type": "task_completed",
            "data": {
                "execution_id": execution_id,
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
            session_id: 会话ID
            execution_id: 执行ID
            task: 任务
            error: 错误信息
        """
        event = {
            "event_type": "task_failed",
            "data": {
                "execution_id": execution_id,
                "task": task,
                "status": "failed",
                "error": error,
                "timestamp": asyncio.get_event_loop().time()
            }
        }
        await self.send_to_session(session_id, event)
