"""灵犀智能助手基类：抽取同步/异步助手的共同逻辑"""

import logging
import re
from pathlib import Path
from typing import Optional, Union, Any, Dict
from abc import ABC, abstractmethod

from lingxi.utils.config import load_config
from lingxi.utils.logging import setup_logging
from lingxi.core.session import SessionManager
from lingxi.core.classifier import TaskClassifier
from lingxi.core.mode_selector import ExecutionModeSelector
from lingxi.core.skill_caller import SkillCaller
from lingxi.core.event.console_subscriber import ConsoleSubscriber
from lingxi.core.event.SessionStore_subscriber import SessionStoreSubscriber
from lingxi.core.context import TaskContext


class BaseAssistant(ABC):
    """灵犀智能助手基类
    
    抽取同步版和异步版的共同逻辑，包括：
    - 初始化逻辑
    - 技能安装意图识别
    - 检查点管理
    - 技能列表管理
    - 上下文管理
    """

    def __init__(self, config_path_or_obj: Union[str, Dict[str, Any]] = "config.yaml"):
        """初始化助手
        
        Args:
            config_path_or_obj: 配置文件路径或配置对象
        """
        if isinstance(config_path_or_obj, dict):
            self.config = config_path_or_obj
        else:
            self.config = load_config(config_path_or_obj)
        setup_logging(self.config)
        self.logger = logging.getLogger(__name__)

        self.logger.info(f"启动{self.config.get('system', {}).get('name', '灵犀')}智能助手")
        self.logger.info(f"版本：{self.config.get('system', {}).get('version', '0.2.0')}")

        self.session_manager = SessionManager(self.config)
        self.classifier = TaskClassifier(self.config)
        self.skill_caller = SkillCaller(self.config)
        self.mode_selector = ExecutionModeSelector(self.config, self.skill_caller)
        self.console_subscriber = ConsoleSubscriber()
        self.session_store_subscriber = SessionStoreSubscriber(self.session_manager)
        
        # 将 session_manager 设置到 workspace_manager 中
        # 注意：skill_caller.workspace_manager 初始为 None，需要手动创建并设置
        from lingxi.management.workspace import WorkspaceManager
        self.workspace_manager = WorkspaceManager(self.config)
        self.skill_caller.set_workspace_manager(self.workspace_manager)
        
        # 设置资源引用（包括 sandbox、skill_caller、session_store）
        self.workspace_manager.set_resources(
            sandbox=self.skill_caller.sandbox,
            skill_caller=self.skill_caller,
            session_store=self.session_manager
        )
        self.logger.debug("workspace_manager 资源引用已设置（sandbox、skill_caller、session_store）")

    def _check_install_skill_intent(self, user_input: str) -> Optional[tuple]:
        """检查是否是安装技能的请求
        
        Args:
            user_input: 用户输入
            
        Returns:
            如果是安装请求，返回 (skill_path, skill_name)，否则返回 None
        """
        user_input_lower = user_input.lower()

        install_keywords = ['安装技能', 'install skill', '添加技能']
        has_install_keyword = any(kw in user_input_lower for kw in install_keywords)
        
        if not has_install_keyword:
            return None

        skill_path = None
        skill_name = None

        name_patterns = [
            r'安装技能\s+(.+?)\s*(?:名称为 |name\s+is|as)\s+(.+)',
            r'install\s+skill\s+(.+?)\s*(?:name\s+is|as)\s+(.+)',
            r'添加技能\s+(.+?)\s*(?:名称为 |name\s+is|as)\s+(.+)',
        ]
        for pattern in name_patterns:
            match = re.match(pattern, user_input_lower)
            if match:
                skill_path = match.group(1).strip()
                skill_name = match.group(2).strip()
                break

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

        if not Path(skill_path).exists():
            self.logger.warning(f"技能路径不存在：{skill_path}")
            return None

        self.logger.debug(f"检测到安装技能请求：{skill_path}, 新名称：{skill_name}")
        return (skill_path, skill_name)

    def install_skill(self, skill_path: str, skill_name: str = None, overwrite: bool = False) -> bool:
        """安装技能（同步版本）
        
        Args:
            skill_path: 技能路径
            skill_name: 技能名称
            overwrite: 是否覆盖已存在的技能目录
            
        Returns:
            是否安装成功
        """
        from lingxi.skills.installer import SkillInstaller
        installer = SkillInstaller(self.config)
        return installer.install(skill_path, skill_name, overwrite)

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
            print(f"会话 ID: {cp['session_id']}")
            print(f"任务：{cp['task']}")
            print(f"进度：{cp['current_step']}/{cp['total_steps']}")
            print(f"状态：{cp['execution_status']}")
            print(f"更新时间：{cp['updated_at']}")
            print("-" * 80)

    def clear_checkpoint(self, session_id: str):
        """清除指定会话的检查点
        
        Args:
            session_id: 会话 ID
        """
        self.session_manager.clear_checkpoint(session_id)
        print(f"已清除会话 {session_id} 的检查点")

    def get_checkpoint_status(self, session_id: str):
        """获取检查点状态
        
        Args:
            session_id: 会话 ID
        """
        status = self.session_manager.get_checkpoint_status(session_id)

        if not status.get("has_checkpoint"):
            print(f"会话 {session_id} 没有检查点")
            return

        print(f"会话 {session_id} 的检查点状态：")
        print(f"任务：{status['task']}")
        print(f"进度：{status['current_step']}/{status['total_steps']}")
        print(f"状态：{status['execution_status']}")
        print(f"重规划次数：{status['replan_count']}")
        print(f"时间戳：{status['timestamp']}")
        if status.get('error_info'):
            print(f"错误信息：{status['error_info']}")

    def list_skills(self):
        """列出可用技能"""
        skills = self.skill_caller.list_available_skills(enabled_only=True)

        if not skills:
            print("没有可用的技能")
            return

        print(f"可用技能列表（共{len(skills)}个）：")
        print("-" * 80)

        for skill in skills:
            print(f"技能名称：{skill['name']}")
            print(f"描述：{skill['description']}")
            print(f"作者：{skill['author']}")
            print(f"版本：{skill['version']}")
            print("-" * 80)

    def get_context_stats(self, session_id: str = "default"):
        """获取上下文统计信息
        
        Args:
            session_id: 会话 ID
        """
        stats = self.session_manager.get_context_stats()

        print(f"会话 {session_id} 的上下文统计：")
        print(f"总消息数：{stats['total_messages']}")
        print(f"总 Token 数：{stats['total_tokens']}")
        print(f"最大 Token 数：{stats['max_tokens']}")
        print(f"使用率：{stats['usage_ratio']:.1%}")
        print(f"已压缩消息数：{stats['compressed_messages']}")
        print(f"当前任务 ID: {stats['current_task_id']}")

    def compress_context(self, session_id: str = "default", strategy: str = None):
        """手动触发上下文压缩
        
        Args:
            session_id: 会话 ID
            strategy: 压缩策略
        """
        stats = self.session_manager.compress_context(strategy)

        print(f"上下文压缩完成：")
        print(f"压缩前 Token 数：{stats['before_tokens']}")
        print(f"压缩后 Token 数：{stats['after_tokens']}")
        print(f"压缩比例：{stats['compression_ratio']:.1%}")

        if stats.get("thinking_compressed"):
            print(f"推理过程压缩：{stats['thinking_compressed']} 条")

        if stats.get("tool_results_compressed"):
            print(f"工具结果压缩：{stats['tool_results_compressed']} 条")

        if stats.get("tasks_archived"):
            print(f"任务归档：{stats['tasks_archived']} 个")

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
            print(f"任务 ID: {result['task_id']}")
            print(f"摘要：{result['summary']}")
            if result['key_entities']:
                print(f"关键实体：{', '.join(result['key_entities'])}")
            print(f"访问次数：{result['access_count']}")
            print("-" * 80)

    @abstractmethod
    def process_input(self, user_input: str, session_id: str = "default", stream: bool = False):
        """处理用户输入（抽象方法）
        
        Args:
            user_input: 用户输入
            session_id: 会话 ID
            stream: 是否启用流式输出
            
        Returns:
            系统响应或流式响应生成器
        """
        pass

    @abstractmethod
    def stream_process_input(self, user_input: str, session_id: str = "default"):
        """流式处理用户输入（抽象方法）
        
        Args:
            user_input: 用户输入
            session_id: 会话 ID
            
        Returns:
            流式响应生成器
        """
        pass
