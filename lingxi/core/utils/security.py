"""安全沙箱模块

提供文件操作沙箱和命令执行安全限制，防止恶意操作
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Optional, List, Set
from lingxi.utils.config import get_config
from lingxi.utils.config import get_workspace_path


class SecurityError(Exception):
    """安全异常"""
    
    def __init__(self, message: str, error_code: str = "SECURITY_ERROR"):
        """初始化安全异常

        Args:
            message: 错误信息
            error_code: 错误码
        """
        super().__init__(message)
        self.error_code = error_code


class ExecutionError(Exception):
    """执行异常"""
    pass


class SecuritySandbox:
    """安全沙箱，限制文件操作范围和命令执行（单例模式）"""
    
    _instance = None  # 单例实例
    
    def __new__(
        cls,
        workspace_root: str = "./workspace",
        max_file_size: int = 10 * 1024 * 1024,
        allowed_commands: Optional[List[str]] = None,
        safety_mode: bool = True,
        white_list_paths: Optional[List[str]] = None
    ):
        """单例模式：确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(
        self,
        workspace_root: str = None,
        max_file_size: int = None,
        allowed_commands: Optional[List[str]] = None,
        safety_mode: bool = None,
        white_list_paths: Optional[List[str]] = None
    ):
        self.config = get_config()
        # 从配置中获取安全沙箱配置
        sandbox_config = self.config.get('security', {}).get('sandbox', {})
        
        # 防止重复初始化
        if hasattr(self, '_initialized'):
            # 如果已初始化，检查是否需要更新工作目录
            if workspace_root:
                self.update_workspace(Path(workspace_root))
            # 更新白名单
            if white_list_paths:
                self.set_white_list_paths(white_list_paths)
            return
        
        # 优先使用传入的参数，否则使用配置中的值，最后使用默认值
        self.workspace_root = Path(workspace_root or sandbox_config.get('workspace_root', './workspace')).resolve()
        self.max_file_size = max_file_size or sandbox_config.get('max_file_size', 10 * 1024 * 1024)
        self.safety_mode = safety_mode if safety_mode is not None else sandbox_config.get('safety_mode', True)
        
        if allowed_commands is None:
            config_commands = sandbox_config.get('allowed_commands')
            if config_commands:
                self.allowed_commands: Set[str] = set(config_commands)
            else:
                self.allowed_commands: Set[str] = {
                    'ls', 'pwd', 'git', 'cat', 'grep', 'find',
                    'dir', 'cd', 'echo', 'type', 'where'
                }
        else:
            self.allowed_commands = set(allowed_commands)
        
        # 初始化白名单路径
        self.white_list_paths: List[Path] = []
        
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        # 添加白名单路径（优先使用传入的参数，否则使用配置中的值）
        paths_to_add = white_list_paths or sandbox_config.get('white_list_paths', [])
        for path_str in paths_to_add:
            self.add_white_list_path(path_str)
        
        self.logger.info(f"安全沙箱初始化：workspace={self.workspace_root}, "
                       f"max_file_size={self.max_file_size}, safety_mode={self.safety_mode}, "
                       f"white_list_paths={[str(p) for p in self.white_list_paths]}")
        self._initialized = True

    def check_security_parameters(self, skill_name: str, action_type: str, params: dict):
        """检查参数是否符合安全要求

        Args:
            skill_name: 技能名称
            action_type: 行动类型
            params: 要检查的参数字典

        Returns:
            bool: 所有路径参数验证通过返回 True，否则返回 False

        Raises:
            SecurityError: 参数超出安全范围
        """
        if not params:
            return True
        if skill_name == "read_skill":
            self.logger.info(f"读取技能说明文件,跳过沙箱检查: {params.get('file_path', 'SKILL.md')}")
            return True
        
        path_keywords = ['path', 'file', 'dir', 'directory', 'folder', 'filepath', 'dirpath']
        
        for key, value in params.items():
            if value is None:
                continue
            
            is_path_param = any(keyword in key.lower() for keyword in path_keywords)
            
            if is_path_param:
                if isinstance(value, list):
                    for path_value in value:
                        if path_value is not None:
                            self.validate_path(str(path_value))
                else:
                    self.validate_path(str(value))
        
        if skill_name == "execute" and action_type == "tool":
            cwd = params.get("cwd")
            if cwd:
                self.validate_path(cwd)
            
            command = params.get("command", "")
            if command:
                self._extract_and_validate_paths_in_command(command)
        
        return True
    
    def _extract_and_validate_paths_in_command(self, command: str):
        """从命令字符串中提取并验证路径
        
        Args:
            command: 命令字符串
            
        Raises:
            SecurityError: 如果命令中包含工作目录外的路径
        """
        import re
        
        # 首先提取并过滤掉 URL（避免误判）
        url_pattern = r'https?://[^\s"\']+'
        urls = set(re.findall(url_pattern, command, re.IGNORECASE))
        
        # 从命令中移除 URL，避免后续正则匹配
        command_without_urls = command
        for url in urls:
            command_without_urls = command_without_urls.replace(url, ' ')
        
        path_patterns = [
            r'["\']([^"\']*\.(py|sh|bat|cmd|exe|txt|json|yaml|yml|xml|csv|log|git))["\']',
            r'(?<![a-zA-Z0-9_\-\.])([a-zA-Z]:[\\/][a-zA-Z0-9_\-\.\\\/]+\.[a-zA-Z0-9]+)(?![a-zA-Z0-9_\-\.])',
            r'(?<![a-zA-Z0-9_\-\.])([\\/][a-zA-Z0-9_\-\.\\\/]+\.[a-zA-Z0-9]+)(?![a-zA-Z0-9_\-\.])',
        ]
        
        found_paths = set()
        
        # 使用移除 URL 后的命令进行路径提取
        for pattern in path_patterns:
            matches = re.findall(pattern, command_without_urls, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    path = match[0] if match[0] else match[1]
                else:
                    path = match
                if path:
                    found_paths.add(path)
        
        # 验证提取的路径
        for path_str in found_paths:
            try:
                if '/' in path_str or '\\' in path_str:
                    self.validate_path(path_str)
            except SecurityError:
                raise
    
    def validate_path(self, file_path: str) -> Path:
        """验证文件路径是否在允许范围内

        Args:
            file_path: 文件路径

        Returns:
            验证后的Path对象

        Raises:
            SecurityError: 路径超出工作空间和白名单范围
        """
        # 处理缺少驱动器号的路径（如 \work\workspace1\.lingxi）
        if file_path.startswith('\\') and len(file_path) > 1 and not file_path[1].isalpha():
            # 对于以 \ 开头但不是网络路径的情况，使用工作目录的驱动器号
            drive_letter = self.workspace_root.drive
            file_path = drive_letter + file_path
        
        path = Path(file_path).expanduser().resolve()
        
        # 检查是否在工作目录内
        try:
            relative_path = path.relative_to(self.workspace_root)
            self.logger.debug(f"路径验证通过: {file_path} -> {relative_path}")
            return path
        except ValueError:
            # 检查是否在白名单路径内
            for white_path in self.white_list_paths:
                try:
                    relative_path = path.relative_to(white_path)
                    self.logger.debug(f"路径验证通过（白名单）: {file_path} -> {relative_path}")
                    return path
                except ValueError:
                    continue
            
            # 路径既不在工作目录也不在白名单内
            error_msg = (
                f"拒绝访问路径：{file_path}\n"
                f"路径必须在 {self.workspace_root} 目录内或白名单路径内\n"
                f"白名单路径：{[str(p) for p in self.white_list_paths]}"
            )
            self.logger.warning(error_msg)
            raise SecurityError(error_msg, "PATH_OUTSIDE_ALLOWED_RANGE")
    
    def safe_read(self, file_path: str) -> str:
        """安全读取文件

        Args:
            file_path: 文件路径

        Returns:
            文件内容

        Raises:
            SecurityError: 路径超出范围或文件过大
            FileNotFoundError: 文件不存在
        """
        path = self.validate_path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"文件不存在：{file_path}")
        
        if not path.is_file():
            raise SecurityError(f"不是文件：{file_path}", "NOT_A_FILE")
        
        file_size = path.stat().st_size
        if file_size > self.max_file_size:
            error_msg = (
                f"文件过大：{file_path} ({file_size} bytes)\n"
                f"最大允许：{self.max_file_size} bytes ({self.max_file_size // (1024*1024)}MB)"
            )
            self.logger.warning(error_msg)
            raise SecurityError(error_msg, "FILE_TOO_LARGE")
        
        self.logger.debug(f"读取文件: {file_path} ({file_size} bytes)")
        return path.read_text(encoding='utf-8')
    
    def safe_write(self, file_path: str, content: str, overwrite: bool = False):
        """安全写入文件

        Args:
            file_path: 文件路径
            content: 文件内容
            overwrite: 是否覆盖已存在的文件

        Raises:
            SecurityError: 路径超出范围或文件已存在且未允许覆盖
        """
        path = self.validate_path(file_path)
        
        if path.exists():
            if not overwrite:
                error_msg = (
                    f"文件已存在：{file_path}\n"
                    f"如需覆盖，请显式设置 overwrite=True"
                )
                self.logger.warning(error_msg)
                raise SecurityError(error_msg, "FILE_EXISTS")
            
            if path.is_dir():
                raise SecurityError(f"路径是目录：{file_path}", "IS_DIRECTORY")
        
        self.logger.debug(f"写入文件: {file_path} ({len(content)} chars)")
        path.write_text(content, encoding='utf-8')
    
    def safe_delete(self, file_path: str):
        """安全删除文件

        Args:
            file_path: 文件路径

        Raises:
            SecurityError: 路径超出范围
        """
        path = self.validate_path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"文件不存在：{file_path}")
        
        self.logger.debug(f"删除文件: {file_path}")
        path.unlink()
    
    def safe_list_dir(self, dir_path: str = ".") -> List[str]:
        """安全列出目录内容

        Args:
            dir_path: 目录路径，默认为工作空间根目录

        Returns:
            文件/目录名称列表
        """
        path = self.validate_path(dir_path)
        
        if not path.exists():
            raise FileNotFoundError(f"目录不存在：{dir_path}")
        
        if not path.is_dir():
            raise SecurityError(f"不是目录：{dir_path}", "NOT_A_DIRECTORY")
        
        return [item.name for item in path.iterdir()]
    
    def safe_exec(self, command: str, timeout: int = 30, cwd: Optional[str] = None) -> str:
        """安全执行系统命令

        Args:
            command: 要执行的命令
            timeout: 超时时间（秒）
            cwd: 工作目录

        Returns:
            命令输出

        Raises:
            SecurityError: 命令不在白名单或为高危操作
            ExecutionError: 命令执行失败
        """
        command_parts = command.strip().split()
        
        if not command_parts:
            raise SecurityError("命令为空", "EMPTY_COMMAND")
        
        base_command = command_parts[0]
        
        if base_command not in self.allowed_commands:
            error_msg = (
                f"禁止执行命令：{command}\n"
                f"允许的命令：{', '.join(sorted(self.allowed_commands))}"
            )
            self.logger.warning(error_msg)
            raise SecurityError(error_msg, "COMMAND_NOT_ALLOWED")
        
        if self.safety_mode:
            dangerous_patterns = ['rm', 'del', 'format', 'shutdown', 'reboot']
            if any(danger in command.lower() for danger in dangerous_patterns):
                error_msg = (
                    f"高危操作需要用户确认：{command}\n"
                    f"请发送 require_confirmation 事件等待用户批准"
                )
                self.logger.warning(error_msg)
                raise SecurityError(error_msg, "DANGEROUS_OPERATION")
        
        if cwd:
            cwd_path = self.validate_path(cwd)
        else:
            cwd_path = str(self.workspace_root)
        
        self.logger.debug(f"执行命令: {command} (cwd={cwd_path})")
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd_path
            )
            
            if result.returncode != 0:
                error_msg = f"命令执行失败（返回码 {result.returncode}）：{result.stderr}"
                self.logger.error(error_msg)
                raise ExecutionError(error_msg)
            
            return result.stdout
            
        except subprocess.TimeoutExpired:
            error_msg = f"命令执行超时（{timeout}秒）：{command}"
            self.logger.error(error_msg)
            raise ExecutionError(error_msg)
        except Exception as e:
            error_msg = f"命令执行异常：{str(e)}"
            self.logger.error(error_msg)
            raise ExecutionError(error_msg)
    
    def get_workspace_root(self) -> Path:
        """获取工作空间根目录

        Returns:
            工作空间根目录 Path 对象
        """
        return self.workspace_root
    
    def update_workspace(self, new_workspace: Path):
        """更新工作目录根目录
        
        Args:
            new_workspace: 新的工作目录路径
        """
        old_workspace = self.workspace_root
        self.workspace_root = Path(new_workspace).resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"工作目录已更新：{old_workspace} -> {self.workspace_root}")
    
    def add_white_list_path(self, path_str: str) -> None:
        """添加白名单路径
        
        Args:
            path_str: 白名单路径
        """
        path = Path(path_str).expanduser().resolve()
        if path not in self.white_list_paths:
            self.white_list_paths.append(path)
            self.logger.info(f"已添加白名单路径：{path}")
    
    def remove_white_list_path(self, path_str: str) -> bool:
        """移除白名单路径
        
        Args:
            path_str: 白名单路径
        
        Returns:
            是否移除成功
        """
        path = Path(path_str).expanduser().resolve()
        if path in self.white_list_paths:
            self.white_list_paths.remove(path)
            self.logger.info(f"已移除白名单路径：{path}")
            return True
        return False
    
    def set_white_list_paths(self, paths: List[str]) -> None:
        """设置白名单路径
        
        Args:
            paths: 白名单路径列表
        """
        self.white_list_paths = []
        for path_str in paths:
            self.add_white_list_path(path_str)
        self.logger.info(f"白名单路径已设置：{[str(p) for p in self.white_list_paths]}")
    
    def get_white_list_paths(self) -> List[Path]:
        """获取白名单路径
        
        Returns:
            白名单路径列表
        """
        return self.white_list_paths
    
    def is_path_allowed(self, file_path: str) -> bool:
        """检查路径是否在允许范围内

        Args:
            file_path: 文件路径

        Returns:
            是否允许
        """
        try:
            self.validate_path(file_path)
            return True
        except SecurityError:
            return False
    
    def is_command_allowed(self, command: str) -> bool:
        """检查命令是否允许执行

        Args:
            command: 命令

        Returns:
            是否允许
        """
        command_parts = command.strip().split()
        if not command_parts:
            return False
        
        base_command = command_parts[0]
        return base_command in self.allowed_commands
