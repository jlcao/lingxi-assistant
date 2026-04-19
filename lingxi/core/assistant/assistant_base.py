"""灵犀智能助手基类：抽取同步/异步助手的共同逻辑"""

import logging
import re
from pathlib import Path
from typing import Optional, Union, Any, Dict, TYPE_CHECKING
from abc import ABC, abstractmethod

from lingxi.utils.config import load_config
from lingxi.utils.logging import setup_logging
# 执行模式选择器已废弃 - 2026-03-15
# from lingxi.core.execution import ExecutionModeSelector
# 任务分类功能已移除 - 2026-03-15
# from lingxi.core.classification import TaskClassifier
from lingxi.core.action_caller import ActionCaller
from lingxi.core.event.console_subscriber import ConsoleSubscriber
from lingxi.core.context.task_context import TaskContext
from lingxi.core.context.context_manager import ContextManager
from lingxi.core.event.ContextAddMsg_subscriber import ContextAddMsgSubscriber
if TYPE_CHECKING:
    from lingxi.core.session import SessionManager
    from lingxi.core.event.SessionStore_subscriber import SessionStoreSubscriber


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

        from lingxi.core.session import SessionManager
        self.session_manager = SessionManager()
        self.context_manager = ContextManager()
        
        # 任务分类功能已移除 - 2026-03-15
        # self.classifier = TaskClassifier(self.config)
        self.classifier = None  # 保留字段避免引用错误
        # 执行模式选择器已废弃 - 2026-03-15
        # self.mode_selector = ExecutionModeSelector(self.config, self.action_caller)
        self.mode_selector = None  # 保留字段避免引用错误
        self.action_caller = ActionCaller(self.config)
        #self.console_subscriber = ConsoleSubscriber()
        
        #
        
        # 延迟初始化 SessionStoreSubscriber，避免循环依赖
        self._session_store_subscriber = None
        
        # 将 session_manager 设置到 workspace_manager 中
        # 注意：action_caller.workspace_manager 初始为 None，需要手动创建并设置
        from lingxi.management.workspace import WorkspaceManager
        self.workspace_manager = WorkspaceManager(self.config)
        self.action_caller.set_workspace_manager(self.workspace_manager)
        
        # 设置资源引用（包括 sandbox、action_caller、session_store）
        self.workspace_manager.set_resources(
            sandbox=self.action_caller.sandbox,
            action_caller=self.action_caller,
            skill_system=self.action_caller.skill_system,
            session_store=self.session_manager
        )
        self.logger.debug("workspace_manager 资源引用已设置（sandbox、action_caller、skill_system、session_store）")
        
        # WebSocket 管理器引用（由外部设置）
        self.websocket_manager = None
    
    
    def init_session_store_subscriber(self) -> None:
        """初始化会话存储订阅者（延迟初始化，避免循环依赖）
        
        此方法应在 session_manager 完全初始化后调用
        """
        if self._session_store_subscriber is None:
            from lingxi.core.event.SessionStore_subscriber import SessionStoreSubscriber
            self._session_store_subscriber = SessionStoreSubscriber(self.session_manager)
            self.context_add_msg_subscriber = ContextAddMsgSubscriber()
            self.logger.debug("SessionStoreSubscriber 和 ContextAddMsgSubscriber 已初始化")
    
    @property
    def session_store_subscriber(self) -> 'SessionStoreSubscriber':
        """获取会话存储订阅者"""
        if self._session_store_subscriber is None:
            self.init_session_store_subscriber()
        return self._session_store_subscriber

    def install_skill(self, skill_path: str, skill_name: str = None, overwrite: bool = False) -> bool:
        """安装技能（同步版本）
        
        Args:
            skill_path: 技能路径
            skill_name: 技能名称
            overwrite: 是否覆盖已存在的技能目录
            
        Returns:
            是否安装成功
        """
        try:
            self.action_caller.install_skill(skill_path, skill_name, overwrite)
            return True
        except Exception as e:
            self.logger.error(f"安装技能失败：{e}", exc_info=True)
            return False

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
