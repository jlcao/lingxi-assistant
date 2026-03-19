"""工作目录管理模块

提供工作目录初始化、切换、资源配置管理功能
"""

import os
import yaml
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

from .workspace_exceptions import WorkspaceError, WorkspaceNotFoundError, WorkspaceInitError, WorkspaceSwitchError


class WorkspaceManager:
    """工作目录管理器（事件驱动 + 资源管理器模式）（单例模式）"""
    
    _instance = None  # 单例实例
    
    def __new__(cls, config: Dict[str, Any]):
        """单例模式：确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config: Dict[str, Any]):
        # 防止重复初始化
        if hasattr(self, '_initialized'):
            return
        
        """初始化工作目录管理器
        
        Args:
            config: 全局配置文件
        """
        self.config = config
        self.current_workspace: Optional[Path] = None
        self.previous_workspace: Optional[Path] = None
        self.lingxi_config: Optional[Dict[str, Any]] = None
        
        # 资源引用（切换时更新）
        self.sandbox = None
        self.skill_caller = None
        self.skill_system = None 
        self.session_store = None
        self.event_publisher = None
        self.logger = logging.getLogger(__name__)
        
        # 初始化用户目录下的全局 .lingxi 目录
        self._initialize_global_lingxi_directory()
        
        # 读取持久化的工作目录并初始化
        workspace_config = config.get("workspace", {})
        last_workspace = workspace_config.get("last_workspace")
        if last_workspace:
            self.logger.info(f"读取到持久化的工作目录：{last_workspace}")
            try:
                self.initialize(last_workspace)
            except Exception as e:
                self.logger.warning(f"初始化持久化工作目录失败：{e}，将使用默认目录")
        else:
            self.logger.debug("未找到持久化的工作目录配置")
        
        self._initialized = True
    
    def _initialize_global_lingxi_directory(self):
        """初始化用户目录下的全局 .lingxi 目录
        
        第一次运行时创建全局目录配置到用户目录下的.lingxi目录，配置里面包含现有的conf,data,skills目录
        """
        # 获取用户目录
        user_home = Path.home()
        global_lingxi_dir = user_home / ".lingxi"
        
        # 如果已存在，直接返回
        if global_lingxi_dir.exists():
            self.logger.debug(f"全局 .lingxi 目录已存在：{global_lingxi_dir}")
            return
        
        # 创建目录结构
        (global_lingxi_dir / "conf").mkdir(parents=True, exist_ok=True)
        (global_lingxi_dir / "data").mkdir(parents=True, exist_ok=True)
        (global_lingxi_dir / "skills").mkdir(parents=True, exist_ok=True)
        
        # 创建默认配置文件
        config_file = global_lingxi_dir / "conf" / "config.yml"
        if not config_file.exists():
            self._create_default_workspace_config(config_file)
        
        self.logger.info(f"全局 .lingxi 目录初始化完成：{global_lingxi_dir}")
    
    def set_resources(self, sandbox=None, skill_caller=None, skill_system=None, session_store=None, event_publisher=None):
        """设置资源引用
        
        Args:
            sandbox: SecuritySandbox 实例
            skill_caller: SkillCaller 实例
            session_store: SessionStore 实例
            event_publisher: EventPublisher 实例
        """
        self.sandbox = sandbox
        self.skill_caller = skill_caller
        self.session_store = session_store
        self.event_publisher = event_publisher
        self.logger.debug(f"工作目录资源引用已设置，session_store: {session_store is not None}")
        
        # 如果当前工作目录未初始化，尝试从配置中读取并初始化
        if self.current_workspace is None:
            workspace_config = self.config.get("workspace", {})
            last_workspace = workspace_config.get("last_workspace")
            if last_workspace:
                self.logger.info(f"从配置读取持久化的工作目录：{last_workspace}")
                try:
                    self.initialize(last_workspace)
                except Exception as e:
                    self.logger.warning(f"初始化持久化工作目录失败：{e}")
            else:
                self.logger.debug("未找到持久化的工作目录配置")
        else:
            # 如果当前工作目录已初始化，且 session_store 已设置，重新初始化数据库
            if self.session_store:
                self.logger.info("当前工作目录已初始化，重新初始化数据库")
                # 使用全局配置中的数据库路径，传入一个虚拟的 data_dir（已废弃）
                self._initialize_database(Path("."))
    
    def initialize(self, workspace_path: Optional[str] = None) -> Path:
        """初始化工作目录
        
        Args:
            workspace_path: 工作目录路径（None 则使用当前目录）
        
        Returns:
            .lingxi 目录路径
        """
        # 1. 确定工作目录
        if workspace_path is None:
            workspace_path = os.getcwd()
        
        workspace_path = Path(workspace_path).resolve()
        
        # 2. 初始化 .lingxi 目录结构
        lingxi_dir = self._initialize_lingxi_directory(workspace_path)
        
        # 3. 加载配置
        self.lingxi_config = self._load_workspace_config(lingxi_dir)
        
        # 4. 设置当前工作目录
        self.current_workspace = workspace_path
        
        # 5. 更新 sandbox 的工作目录
        if self.sandbox:
            self.sandbox.update_workspace(workspace_path)
            self.logger.debug(f"SecuritySandbox 工作目录已更新：{workspace_path}")
        
        # 6. 初始化数据库（如果 session_store 已设置）
        if self.session_store:
            self.logger.info(f"开始初始化数据库，数据目录：{lingxi_dir / 'data'}")
            self._initialize_database(lingxi_dir / "data")
        
        # 7. 发布事件
        if self.event_publisher:
            self.event_publisher.publish("workspace_initialized", 
                workspace=str(workspace_path),
                lingxi_dir=str(lingxi_dir)
            )
        
        self.logger.info(f"工作目录初始化完成：{workspace_path}")
        return lingxi_dir
    
    async def switch_workspace(self, workspace_path: str, force: bool = False) -> Dict[str, Any]:
        """切换工作目录（等待任务完成）
        
        Args:
            workspace_path: 新的工作目录路径
            force: 是否强制切换（忽略执行中任务）
        
        Returns:
            切换结果
        """
        self.logger.info(f"开始切换工作区，当前 session_store: {self.session_store is not None}")
        self.previous_workspace = self.current_workspace
        
        # 1. 检查是否有执行中的任务
        if not force and self._has_running_tasks():
            self.logger.info("等待任务完成...")
            await self._wait_for_tasks_completion(timeout=300)  # 5 分钟超时
        
        # 2. 验证路径有效性
        workspace_path = Path(workspace_path).resolve()
        if not workspace_path.exists():
            raise WorkspaceNotFoundError(f"工作目录不存在：{workspace_path}")
        
        # 3. 保存当前会话状态
        self._save_session_state()
        
        # 4. 卸载当前资源
        self._unload_resources()
        
        # 5. 初始化/加载新工作目录
        lingxi_dir = self._initialize_lingxi_directory(workspace_path)
        self.lingxi_config = self._load_workspace_config(lingxi_dir)
        
        # 6. 加载新资源
        self._load_resources(workspace_path, lingxi_dir)
        
        # 7. 更新当前工作目录
        self.current_workspace = workspace_path
        
        # 8. 持久化配置
        self._persist_workspace_path(workspace_path)
        
        # 9. 发布事件
        if self.event_publisher:
            self.event_publisher.publish("workspace_switched",
                previous_workspace=str(self.previous_workspace),
                current_workspace=str(workspace_path),
                lingxi_dir=str(lingxi_dir),
                switched_at=datetime.now().isoformat()
            )
        
        # 10. 更新 SkillSystem 的工作目录
        if self.skill_system:
            self.skill_system.update_workspace(str(workspace_path))
            self.logger.debug(f"SkillSystem 工作目录已更新为：{workspace_path}")
        
        self.logger.info(f"工作目录已切换：{workspace_path}")
        
        return {
            "success": True,
            "data": {
                "previous_workspace": str(self.previous_workspace) if self.previous_workspace else None,
                "current_workspace": str(workspace_path),
                "lingxi_dir": str(lingxi_dir),
                "switched_at": datetime.now().isoformat()
            }
        }
    
    def _initialize_lingxi_directory(self, workspace_path: Path) -> Path:
        """初始化 .lingxi 目录结构
        
        目录结构：
        .lingxi/
        ├── conf/
        │   └── config.yml
        ├── data/
        └── skills/
        
        Args:
            workspace_path: 工作目录路径
        
        Returns:
            .lingxi 目录路径
        """
        lingxi_dir = workspace_path / ".lingxi"
        
        # 如果已存在，直接返回
        if lingxi_dir.exists():
            self.logger.debug(f".lingxi 目录已存在：{lingxi_dir}")
            return lingxi_dir
        
        # 创建目录结构
        (lingxi_dir / "conf").mkdir(parents=True, exist_ok=True)
        (lingxi_dir / "data").mkdir(parents=True, exist_ok=True)
        (lingxi_dir / "skills").mkdir(parents=True, exist_ok=True)
        
        # 创建默认配置文件（如果不存在）
        config_file = lingxi_dir / "conf" / "config.yml"
        if not config_file.exists():
            self._create_default_workspace_config(config_file)
        
        self.logger.debug(f".lingxi 目录初始化完成：{lingxi_dir}")
        return lingxi_dir
    
    def _create_default_workspace_config(self, config_file: Path):
        """创建默认工作目录配置文件
        
        Args:
            config_file: 配置文件路径
        """
        default_config = {
            "workspace": {
                "name": "默认工作空间",
                "description": "灵犀助手工作目录"
            },
            "skills": {
                "enabled": []
            },
            "database": {
                "assistant_db": "./data/assistant.db",
                "memory_db": "./data/long_term_memory.db"
            },
            "security": {
                "safety_mode": True,
                "max_file_size": 10485760
            }
        }
        
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(default_config, f, allow_unicode=True, default_flow_style=False)
        
        self.logger.debug(f"创建默认配置文件：{config_file}")
    
    def _load_workspace_config(self, lingxi_dir: Path) -> Dict[str, Any]:
        """加载工作目录配置（优先级高于全局配置）
        
        Args:
            lingxi_dir: .lingxi 目录路径
        
        Returns:
            合并后的配置
        """
        config_file = lingxi_dir / "conf" / "config.yml"
        
        if not config_file.exists():
            return self.config
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                workspace_config = yaml.safe_load(f)
            
            # 处理配置文件为空的情况
            if workspace_config is None:
                self.logger.warning(f"配置文件为空：{config_file}，使用全局配置")
                return self.config
            
            # 合并配置（工作目录配置覆盖全局配置）
            merged_config = self._deep_merge(self.config, workspace_config)
            
            self.logger.debug(f"工作目录配置已加载：{config_file}")
            return merged_config
        except yaml.YAMLError as e:
            self.logger.warning(f"配置文件格式错误：{config_file}，使用全局配置。错误：{e}")
            return self.config
    
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """深度合并字典（override 优先）
        
        Args:
            base: 基础字典
            override: 覆盖字典
        
        Returns:
            合并后的字典
        """
        result = base.copy()
        
        for key, value in override.items():
            if isinstance(value, dict) and key in result:
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _unload_resources(self):
        """卸载当前工作目录的资源"""
        self.logger.info("开始卸载资源...")
        
        # 1. 关闭数据库连接
        if self.session_store:
            # SessionManager 没有 close 方法，不需要显式关闭
            # if hasattr(self.session_store, 'close'):
            #     self.session_store.close()
            self.logger.debug("数据库连接保持打开状态（SessionManager 自动管理）")
        
        # 2. 注销工作目录级别的技能
        if self.skill_caller and hasattr(self.skill_caller, 'skill_registry'):
            self._unregister_workspace_skills()
            self.logger.debug("工作目录技能已注销")
        
        self.logger.info("资源卸载完成")
    
    def _load_resources(self, workspace_path: Path, lingxi_dir: Path):
        """加载新工作目录的资源
        
        Args:
            workspace_path: 工作目录路径
            lingxi_dir: .lingxi 目录路径
        """
        self.logger.info("开始加载资源...")
        self.logger.info(f"_load_resources 开始时 session_store: {self.session_store is not None}")
        
        # 1. 更新 SecuritySandbox 的 workspace_root
        if self.sandbox:
            self.sandbox.update_workspace(workspace_path)
            self.logger.debug("SecuritySandbox 工作目录已更新")
        
        # 2. 重新加载技能注册表（工作目录技能优先）
        if self.skill_caller and hasattr(self.skill_caller, 'skill_registry'):
            self._register_workspace_skills(lingxi_dir / "skills")
            self.logger.debug("工作目录技能已注册")
        
        # 3. 重新初始化数据库连接
        self.logger.info(f"_load_resources 中 session_store 状态：{self.session_store is not None}")
        if self.session_store:
            self.logger.info(f"开始初始化数据库，数据目录：{lingxi_dir / 'data'}")
            self._initialize_database(lingxi_dir / "data")
            self.logger.debug("数据库连接已初始化")
        else:
            self.logger.warning("session_store 为 None，跳过数据库初始化")
        
        self.logger.info(f"_load_resources 结束时 session_store: {self.session_store is not None}")
        self.logger.info("资源加载完成")
    
    def _register_workspace_skills(self, skills_dir: Path):
        """注册工作目录级别的技能
        
        Args:
            skills_dir: 技能目录
        """
        if not skills_dir.exists():
            return
        
        registry = self.skill_caller.skill_registry
        
        # 先注销旧的工作目录技能
        self._unregister_workspace_skills()
        
        # 注册新技能
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "main.py").exists():
                try:
                    registry.register_skill_from_dir(skill_dir, source="workspace")
                    self.logger.info(f"注册工作目录技能：{skill_dir.name}")
                except Exception as e:
                    self.logger.error(f"注册技能失败 {skill_dir.name}: {e}")
    
    def _unregister_workspace_skills(self):
        """注销工作目录级别的技能"""
        if not hasattr(self.skill_caller, 'skill_registry'):
            return
        
        registry = self.skill_caller.skill_registry
        workspace_skills = [
            name for name, info in registry.skill_cache.items()
            if info.get("source") == "workspace"
        ]
        
        for skill_name in workspace_skills:
            del registry.skill_cache[skill_name]
            self.logger.debug(f"已注销工作目录技能：{skill_name}")
    
    def _initialize_database(self, data_dir: Path):
        """初始化数据库连接
        
        行为说明：
        - 使用全局配置中的数据库路径，不再使用工作目录下的数据库
        - 如果数据库不存在：SessionManager 会自动创建新数据库并初始化表结构
        - 如果数据库已存在：保留所有历史会话数据，不做任何清空
        
        Args:
            data_dir: 数据目录（已废弃，使用全局配置中的路径）
        """
        self.logger.info(f"_initialize_database 方法被调用，session_store: {self.session_store is not None}")
        
        if not self.session_store:
            self.logger.warning("session_store 为 None，跳过数据库初始化")
            return
        
        # 从全局配置中获取数据库路径
        from lingxi.utils.config import get_config
        config = get_config()
        
        # 使用全局配置中的数据库路径
        lingxi_db = Path(config['database']['lingxi_db'])
        skills_db = Path(config['database']['skills_db'])
        
        # 确保全局数据目录存在
        global_data_dir = lingxi_db.parent
        if not global_data_dir.exists():
            global_data_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"全局数据目录已创建：{global_data_dir}")
        
        # 检查数据库是否存在
        db_status = "已存在" if lingxi_db.exists() else "新建"
        self.logger.info(f"全局数据库：{db_status} - {lingxi_db}")
        
        # 使用 SessionManager 的 update_db_path 方法更新数据库路径
        # 这样可以确保 DatabaseManager 的 db_path 也被正确更新
        if hasattr(self.session_store, 'update_db_path'):
            self.session_store.update_db_path(str(lingxi_db))
            self.logger.info(f"SessionManager 数据库路径已更新为全局路径：{lingxi_db}")
        else:
            self.logger.warning("session_store 没有 update_db_path 方法，使用备用方案")
            # 备用方案：直接更新 db_path 属性（不推荐，但保持向后兼容）
            if hasattr(self.session_store, 'config'):
                self.session_store.config['session'] = self.session_store.config.get('session', {})
                self.session_store.config['session']['db_path'] = str(lingxi_db)
                self.session_store.config['session']['memory_db'] = str(lingxi_db)
                self.session_store.db_path = str(lingxi_db)
                self.logger.info(f"SessionManager.db_path 当前值：{self.session_store.db_path}")
            else:
                self.logger.error("session_store 没有 config 属性，无法更新数据库路径")
        
        self.logger.info(f"数据库初始化完成：{lingxi_db}")
    
    def _has_running_tasks(self) -> bool:
        """检查是否有执行中的任务
        
        Returns:
            是否有执行中的任务
        """
        # TODO: 实现任务检查逻辑
        # 可以通过检查执行引擎的状态
        return False
    
    async def _wait_for_tasks_completion(self, timeout: int = 300):
        """等待任务完成
        
        Args:
            timeout: 超时时间（秒）
        """
        import asyncio
        start_time = datetime.now()
        
        while self._has_running_tasks():
            if (datetime.now() - start_time).total_seconds() > timeout:
                self.logger.warning("等待任务完成超时")
                break
            await asyncio.sleep(1)
    
    def _save_session_state(self):
        """保存当前会话状态"""
        # TODO: 实现会话状态保存逻辑
        self.logger.debug("会话状态已保存")
    
    def _persist_workspace_path(self, workspace_path: Path):
        """持久化工作目录路径到全局配置
        
        Args:
            workspace_path: 工作目录路径
        """
        # 尝试找到配置文件
        config_paths = [
            Path(__file__).parent.parent / "config.yaml",
            Path.cwd() / "config.yaml"
        ]
        
        config_file = None
        for path in config_paths:
            if path.exists():
                config_file = path
                break
        
        if not config_file:
            self.logger.warning("未找到配置文件，跳过持久化")
            return
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if 'workspace' not in config:
                config['workspace'] = {}
            
            config['workspace']['last_workspace'] = str(workspace_path)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            
            self.logger.debug(f"工作目录已持久化：{workspace_path}")
        except Exception as e:
            self.logger.error(f"持久化配置失败：{e}")
    
    def get_current_workspace(self) -> Optional[Path]:
        """获取当前工作目录
        
        Returns:
            当前工作目录路径
        """
        return self.current_workspace
    
    def get_lingxi_directory(self) -> Optional[Path]:
        """获取 .lingxi 目录路径
        
        Returns:
            .lingxi 目录路径
        """
        if self.current_workspace:
            return self.current_workspace / ".lingxi"
        return None
    
    def validate_workspace(self, workspace_path: Path) -> bool:
        """验证工作目录是否有效
        
        Args:
            workspace_path: 工作目录路径
        
        Returns:
            是否有效
        """
        # 检查目录是否存在
        if not workspace_path.exists():
            return False
        
        # 检查是否有 .lingxi 目录（没有就创建）
        lingxi_dir = workspace_path / ".lingxi"
        if not lingxi_dir.exists():
            self.logger.info(f"工作目录缺少 .lingxi 子目录，将自动创建：{lingxi_dir}")
        
        return True


# 全局工作空间管理器实例
_workspace_manager: Optional[WorkspaceManager] = None


def get_workspace_manager(config: Optional[Dict[str, Any]] = None) -> WorkspaceManager:
    """获取或创建工作空间管理器实例
    
    Args:
        config: 配置文件，None 则使用全局配置
    
    Returns:
        WorkspaceManager 实例
    """
    global _workspace_manager
    
    if _workspace_manager is None:
        if config is None:
            from lingxi.utils.config import get_config
            config = get_config()
        
        _workspace_manager = WorkspaceManager(config)
    
    return _workspace_manager


def reset_workspace_manager():
    """重置工作空间管理器（用于测试）"""
    global _workspace_manager
    _workspace_manager = None
