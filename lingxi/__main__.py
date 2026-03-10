"""同步灵犀智能助手主类"""

import sys
import logging
import argparse
from typing import Optional, Union, Any, Dict, List
from lingxi.core.assistant.assistant_base import BaseAssistant
from lingxi.core.context import TaskContext
from lingxi.utils.config import load_config


class LingxiAssistant(BaseAssistant):
    """同步灵犀智能助手"""

    def process_input(self, user_input: str, session_id: str = "default", stream: bool = False) -> Union[str, Any]:
        """处理用户输入

        Args:
            user_input: 用户输入
            session_id: 会话 ID
            stream: 是否启用流式输出

        Returns:
            系统响应（非流式）或流式响应生成器（流式）
        """
        self.logger.debug(f"处理用户输入：{user_input}")

        try:
            install_result = self._check_install_skill_intent(user_input)
            if install_result:
                skill_path, skill_name = install_result
                success = self.install_skill(skill_path, skill_name)
                if success:
                    response = f"技能安装成功：{skill_path}"
                else:
                    response = f"技能安装失败：{skill_path}"
                return response

            history = self.session_manager.get_history(session_id)

            engine = self.mode_selector.get_engine(mode="plan_react", session_manager=self.session_manager)

            workspace_path = str(self.workspace_manager.current_workspace) if self.workspace_manager.current_workspace else None

            context = TaskContext(
                user_input=user_input,
                task_info={"level": "complex"},
                session_id=session_id,
                session_history=history,
                stream=stream,
                workspace_path=workspace_path
            )

            response = engine.process(context)

            return response

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            self.logger.error(f"处理失败：{e}\n{error_trace}")
            error_response = f"抱歉，处理您的请求时出现错误：{str(e)}\n\n堆栈信息:\n{error_trace}"
            if stream:
                def error_generator():
                    yield {"type": "error", "message": error_response}
                return error_generator()
            return error_response

    def stream_process_input(self, user_input: str, session_id: str = "default") -> Any:
        """流式处理用户输入

        Args:
            user_input: 用户输入
            session_id: 会话 ID

        Returns:
            流式响应生成器
        """
        return self.process_input(user_input, session_id, stream=True)

    def _check_install_skill_intent(self, user_input: str) -> Optional[tuple]:
        """检查是否是安装技能的请求

        Args:
            user_input: 用户输入

        Returns:
            如果是安装请求，返回 (skill_path, skill_name)，否则返回 None
        """
        import re
        from pathlib import Path

        user_input_lower = user_input.lower()

        # 检查是否包含安装技能的关键词
        install_keywords = ['安装技能', 'install skill', '添加技能']
        has_install_keyword = any(kw in user_input_lower for kw in install_keywords)
        
        if not has_install_keyword:
            return None

        # 提取路径和名称
        skill_path = None
        skill_name = None

        # 尝试匹配带名称的格式
        name_patterns = [
            r'安装技能\s+(.+?)\s*(?:名称为|name\s+is|as)\s+(.+)',
            r'install\s+skill\s+(.+?)\s*(?:name\s+is|as)\s+(.+)',
            r'添加技能\s+(.+?)\s*(?:名称为|name\s+is|as)\s+(.+)',
        ]
        for pattern in name_patterns:
            match = re.match(pattern, user_input_lower)
            if match:
                skill_path = match.group(1).strip()
                skill_name = match.group(2).strip()
                break

        # 如果没有匹配到带名称的格式，尝试匹配不带名称的格式
        if not skill_path:
            install_patterns = [
                r'安装技能\s+(.+)',
                r'install\s+skill\s+(.+)',
                r'添加技能\s+(.+)',
            ]
            for pattern in install_patterns:
                match = re.match(pattern, user_input_lower)
                if match:
                    skill_path = match.group(1).strip()
                    break

        if not skill_path:
            return None

        # 检查路径是否存在
        if not Path(skill_path).exists():
            self.logger.warning(f"技能路径不存在: {skill_path}")
            return None

        self.logger.debug(f"检测到安装技能请求: {skill_path}, 新名称: {skill_name}")
        return (skill_path, skill_name)

    def cleanup_checkpoints(self, ttl_hours: int = 24) -> int:
        """清理过期检查点

        Args:
            ttl_hours: 生存时间（小时）

        Returns:
            清理的检查点数量
        """
        return self.session_manager.cleanup_expired_checkpoints(ttl_hours)

    def list_checkpoints(self):
        """列出所有活跃检查点"""
        checkpoints = self.session_manager.list_active_checkpoints()

        if not checkpoints:
            print("没有活跃的检查点")
            return

        print(f"活跃检查点列表（共{len(checkpoints)}个）：")
        print("-" * 80)

        for cp in checkpoints:
            print(f"会话ID: {cp['session_id']}")
            print(f"任务: {cp['task']}")
            print(f"进度: {cp['current_step']}/{cp['total_steps']}")
            print(f"状态: {cp['execution_status']}")
            print(f"更新时间: {cp['updated_at']}")
            print("-" * 80)

    def clear_checkpoint(self, session_id: str):
        """清除指定会话的检查点

        Args:
            session_id: 会话ID
        """
        self.session_manager.clear_checkpoint(session_id)
        print(f"已清除会话 {session_id} 的检查点")

    def get_checkpoint_status(self, session_id: str):
        """获取检查点状态

        Args:
            session_id: 会话ID
        """
        status = self.session_manager.get_checkpoint_status(session_id)

        if not status.get("has_checkpoint"):
            print(f"会话 {session_id} 没有检查点")
            return

        print(f"会话 {session_id} 的检查点状态：")
        print(f"任务: {status['task']}")
        print(f"进度: {status['current_step']}/{status['total_steps']}")
        print(f"状态: {status['execution_status']}")
        print(f"重规划次数: {status['replan_count']}")
        print(f"时间戳: {status['timestamp']}")
        if status.get('error_info'):
            print(f"错误信息: {status['error_info']}")

    def list_skills(self):
        """列出可用技能"""
        skills = self.skill_caller.list_available_skills(enabled_only=True)

        if not skills:
            print("没有可用的技能")
            return

        print(f"可用技能列表（共{len(skills)}个）：")
        print("-" * 80)

        for skill in skills:
            print(f"技能名称: {skill['name']}")
            print(f"描述: {skill['description']}")
            print(f"作者: {skill['author']}")
            print(f"版本: {skill['version']}")
            print("-" * 80)

    def get_context_stats(self, session_id: str = "default"):
        """获取上下文统计信息

        Args:
            session_id: 会话ID
        """
        stats = self.session_manager.get_context_stats()

        print(f"会话 {session_id} 的上下文统计：")
        print(f"总消息数: {stats['total_messages']}")
        print(f"总Token数: {stats['total_tokens']}")
        print(f"最大Token数: {stats['max_tokens']}")
        print(f"使用率: {stats['usage_ratio']:.1%}")
        print(f"已压缩消息数: {stats['compressed_messages']}")
        print(f"当前任务ID: {stats['current_task_id']}")

    def compress_context(self, session_id: str = "default", strategy: str = None):
        """手动触发上下文压缩

        Args:
            session_id: 会话ID
            strategy: 压缩策略
        """
        stats = self.session_manager.compress_context(strategy)

        print(f"上下文压缩完成：")
        print(f"压缩前Token数: {stats['before_tokens']}")
        print(f"压缩后Token数: {stats['after_tokens']}")
        print(f"压缩比例: {stats['compression_ratio']:.1%}")

        if stats.get("thinking_compressed"):
            print(f"推理过程压缩: {stats['thinking_compressed']} 条")

        if stats.get("tool_results_compressed"):
            print(f"工具结果压缩: {stats['tool_results_compressed']} 条")

        if stats.get("tasks_archived"):
            print(f"任务归档: {stats['tasks_archived']} 个")

        if stats.get("sliding_window_applied"):
            print(f"滑动窗口已应用")

    def retrieve_history(self, query: str, top_k: int = 5):
        """检索相关历史记忆

        Args:
            query: 查询文本
            top_k: 返回数量
        """
        results = self.session_manager.retrieve_relevant_history(query, top_k)

        if not results:
            print(f"没有找到与 '{query}' 相关的历史记录")
            return

        print(f"与 '{query}' 相关的历史记录（共{len(results)}条）：")
        print("-" * 80)

        for result in results:
            print(f"任务ID: {result['task_id']}")
            print(f"摘要: {result['summary']}")
            if result['key_entities']:
                print(f"关键实体: {', '.join(result['key_entities'])}")
            print(f"访问次数: {result['access_count']}")
            print("-" * 80)

    def _process_stream_response(self, response_generator: Any, final_response: List[str]):
        """处理流式响应 - 使用事件订阅者自动处理输出

        Args:
            response_generator: 流式响应生成器
            final_response: 最终响应列表
        """
        try:
            for chunk in response_generator:
                if isinstance(chunk, dict):
                    if chunk.get('type') == 'finish':
                        result = chunk.get('result', '')
                        final_response.append(result)
                    elif chunk.get('type') == 'error':
                        print(f"❌ 错误: {chunk.get('message', '未知错误')}")
                        break
        except StopIteration:
            pass

    def interactive_mode(self, session_id: str = "default"):
        """交互式模式

        Args:
            session_id: 会话 ID
        """
        print(f"欢迎使用{self.config.get('system', {}).get('name', '灵犀')}智能助手！")
        print(f"版本：{self.config.get('system', {}).get('version', '0.2.0')}")
        print("输入 'exit' 或 'quit' 退出系统")
        print("输入 '/help' 查看帮助")
        print("=" * 60)

        stream_mode = True  # 默认启用流式输出模式

        while True:
            try:
                user_input = input("用户: ").strip()

                if user_input.lower() in ["exit", "quit"]:
                    print("再见！")
                    break

                if not user_input:
                    continue

                if user_input.startswith("/"):
                    cmd_result = self._handle_command(user_input, session_id, stream_mode)
                    # 检查是否是 /stream 命令的特殊处理
                    if isinstance(cmd_result, tuple):
                        session_id, stream_mode = cmd_result
                    else:
                        session_id = cmd_result
                    continue

                if stream_mode:
                    # 流式输出模式
                    response_generator = self.stream_process_input(user_input, session_id)
                    final_response = []
                    self._process_stream_response(response_generator, final_response)
                    
                    print()  # 换行
                else:
                    # 非流式输出模式
                    response = self.process_input(user_input, session_id)
                    print(f"灵犀: {response}")
                print("=" * 60)

            except EOFError:
                print("\n输入结束，退出系统")
                break
            except KeyboardInterrupt:
                print("\n再见！")
                break
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                self.logger.error(f"交互模式错误: {e}\n{error_trace}")
                print(f"错误: {e}\n堆栈信息:\n{error_trace}")
                break

    def _handle_command(self, command: str, session_id: str, stream_mode: bool = False) -> Union[str, tuple]:
        """处理命令

        Args:
            command: 命令
            session_id: 会话ID
            stream_mode: 当前的流式输出模式

        Returns:
            新的会话ID（如果切换了会话）或 (会话ID, 新的流式模式) 元组
        """
        cmd_parts = command.split()
        cmd = cmd_parts[0].lower()

        if cmd == "/help":
            print("可用命令：")
            print("  /help - 显示帮助")
            print("  /clear - 清空当前会话")
            print("  /status - 显示检查点状态")
            print("  /skills - 列出可用技能")
            print("  /install <path> - 安装技能")
            print("  /context-stats - 显示上下文统计")
            print("  /compress - 手动触发上下文压缩")
            print("  /search <query> - 检索相关历史")
            print("  /session [id] - 创建新会话或切换到指定会话")
            print("  /stream [on|off] - 切换流式输出模式")
            print("  /exit - 退出系统")

        elif cmd == "/clear":
            self.session_manager.clear_session(session_id)
            print("会话已清空")

        elif cmd == "/status":
            self.get_checkpoint_status(session_id)

        elif cmd == "/skills":
            self.list_skills()

        elif cmd == "/install":
            if len(cmd_parts) < 2:
                print("请提供技能源路径")
                return session_id
            skill_source = " ".join(cmd_parts[1:])
            success = self.install_skill(skill_source)
            if success:
                print(f"技能安装成功: {skill_source}")
            else:
                print(f"技能安装失败: {skill_source}")

        elif cmd == "/context-stats":
            self.get_context_stats(session_id)

        elif cmd == "/compress":
            strategy = cmd_parts[1] if len(cmd_parts) > 1 else None
            self.compress_context(session_id, strategy)

        elif cmd == "/search":
            if len(cmd_parts) < 2:
                print("请提供查询文本")
                return session_id
            query = " ".join(cmd_parts[1:])
            self.retrieve_history(query)

        elif cmd == "/session":
            if len(cmd_parts) > 1:
                new_session_id = cmd_parts[1]
                print(f"切换到会话: {new_session_id}")
            else:
                import uuid
                new_session_id = f"session_{uuid.uuid4().hex[:8]}"
                print(f"创建新会话: {new_session_id}")
            return new_session_id

        elif cmd == "/exit":
            print("再见！")
            sys.exit(0)

        elif cmd == "/stream":
            # 切换流式输出模式
            if len(cmd_parts) > 1:
                mode = cmd_parts[1].lower()
                if mode == "on":
                    print("已启用流式输出模式")
                    return (session_id, True)
                elif mode == "off":
                    print("已禁用流式输出模式")
                    return (session_id, False)
                else:
                    print("用法: /stream [on|off]")
            else:
                # 切换模式
                new_mode = not stream_mode
                print(f"已{'启用' if new_mode else '禁用'}流式输出模式")
                return (session_id, new_mode)

        else:
            print(f"未知命令: {cmd}")

        return session_id


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="灵犀智能助手")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径")
    parser.add_argument("--session", default="default", help="会话ID")
    parser.add_argument("-w", "--web", action="store_true", help="启动 Web 服务器模式")
    parser.add_argument("--cleanup-checkpoints", action="store_true", help="清理过期检查点")
    parser.add_argument("--list-checkpoints", action="store_true", help="列出活跃检查点")
    parser.add_argument("--clear-checkpoint", help="清除指定会话的检查点")
    parser.add_argument("--list-skills", action="store_true", help="列出可用技能")
    parser.add_argument("--install-skill", help="安装技能（指定技能源目录路径）")
    parser.add_argument("--skill-name", help="安装技能时指定新名称（可选）")
    parser.add_argument("--overwrite", action="store_true", help="覆盖已存在的技能目录")

    args = parser.parse_args()

    # 检查是否是控制台模式
    is_console_mode = not args.web and not any([
        args.cleanup_checkpoints,
        args.list_checkpoints,
        args.clear_checkpoint,
        args.list_skills,
        args.install_skill
    ])

    if is_console_mode:
        # 控制台交互式模式，修改配置中的日志级别
        import yaml
        import os
        
        # 加载配置文件
        config_path = args.config
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                initial_config = yaml.safe_load(f)
        else:
            # 如果配置文件不存在，使用空字典
            initial_config = {}
        
        # 修改日志级别为 ERROR
        if 'logging' not in initial_config:
            initial_config['logging'] = {}
        initial_config['logging']['level'] = 'ERROR'
        
        # 使用修改后的初始配置调用 load_config，确保环境变量被正确加载
        config = load_config(args.config, initial_config)
        
        # 传递加载后的配置给 LingxiAssistant
        assistant = LingxiAssistant(config)
    else:
        # 其他模式，使用默认配置
        assistant = LingxiAssistant(args.config)

    if args.cleanup_checkpoints:
        count = assistant.cleanup_checkpoints()
        print(f"清理了 {count} 个过期检查点")
        return

    if args.list_checkpoints:
        assistant.list_checkpoints()
        return

    if args.clear_checkpoint:
        assistant.clear_checkpoint(args.clear_checkpoint)
        return

    if args.list_skills:
        assistant.list_skills()
        return

    if args.install_skill:
        success = assistant.install_skill(args.install_skill, args.skill_name, args.overwrite)
        if success:
            print("技能安装成功")
        else:
            print("技能安装失败")
        return

    if args.web:
        # 启动 Web 服务器
        import sys
        import os
        from pathlib import Path
        
        project_root = Path(__file__).parent.parent
        sys.path.insert(0, str(project_root))
        
        from lingxi.web.fastapi_server import run_server
        from lingxi.utils.config import get_config
        from lingxi.web.websocket import WebSocketManager
        from lingxi.web.state import set_websocket_manager, set_assistant
        from lingxi.core.assistant.async_main import AsyncLingxiAssistant
        from lingxi.core.event.websocket_subscriber import WebSocketSubscriber
        
        print("=" * 60)
        print("灵犀智能助手 - WebSocket服务器")
        print("=" * 60)
        print()
        
        config = get_config()
        web_config = config.get('web', {})
        host = web_config.get('host', 'localhost')
        port = web_config.get('port', 5000)
        
        print(f"服务器地址: http://{host}:{port}")
        print(f"WebSocket 端点：ws://{host}:{port}/ws")
        print(f"Web 界面：http://{host}:{port}/static/index.html")
        print(f"API 文档：http://{host}:{port}/docs")
        print()
        print("按 Ctrl+C 停止服务器")
        print("=" * 60)
        print()
        
        # 初始化助手和 WebSocket 管理器
        try:
            assistant = AsyncLingxiAssistant(config)
            set_assistant(assistant)
            
            # 初始化 WebSocket 管理器和订阅者
            websocket_manager = WebSocketManager(assistant)
            set_websocket_manager(websocket_manager)
            
            # 初始化 WebSocket 事件订阅者
            websocket_subscriber = WebSocketSubscriber(websocket_manager)
            
            print("异步助手已初始化")
            print("WebSocket 事件推送：已启用（全异步）")
            print()
        except Exception as e:
            print(f"初始化失败：{e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        try:
            run_server(config)
        except KeyboardInterrupt:
            print("\n\n服务器已停止")
        except Exception as e:
            print(f"\n\n服务器启动失败：{e}")
            sys.exit(1)
    else:
        assistant.interactive_mode(args.session)


if __name__ == "__main__":
    main()
