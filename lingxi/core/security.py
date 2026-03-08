"""安全沙箱模块

提供文件操作沙箱和命令执行安全限制，防止恶意操作
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Optional, List, Set


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
    """安全沙箱，限制文件操作范围和命令执行"""
    
    def __init__(
        self,
        workspace_root: str = "./workspace",
        max_file_size: int = 10 * 1024 * 1024,
        allowed_commands: Optional[List[str]] = None,
        safety_mode: bool = True
    ):
        """初始化安全沙箱

        Args:
            workspace_root: 工作空间根目录
            max_file_size: 最大文件大小（字节），默认10MB
            allowed_commands: 允许执行的命令白名单
            safety_mode: 是否启用安全模式
        """
        self.workspace_root = Path(workspace_root).resolve()
        self.max_file_size = max_file_size
        self.safety_mode = safety_mode
        
        if allowed_commands is None:
            self.allowed_commands: Set[str] = {
                'ls', 'pwd', 'git', 'cat', 'grep', 'find',
                'dir', 'cd', 'echo', 'type', 'where'
            }
        else:
            self.allowed_commands = set(allowed_commands)
        
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"安全沙箱初始化: workspace={self.workspace_root}, "
                       f"max_file_size={max_file_size}, safety_mode={safety_mode}")
    
    def validate_path(self, file_path: str) -> Path:
        """验证文件路径是否在允许范围内

        Args:
            file_path: 文件路径

        Returns:
            验证后的Path对象

        Raises:
            SecurityError: 路径超出工作空间
        """
        path = Path(file_path).resolve()
        
        try:
            relative_path = path.relative_to(self.workspace_root)
            self.logger.debug(f"路径验证通过: {file_path} -> {relative_path}")
            return path
        except ValueError:
            error_msg = (
                f"拒绝访问路径：{file_path}\n"
                f"路径必须在 {self.workspace_root} 目录内"
            )
            self.logger.warning(error_msg)
            raise SecurityError(error_msg, "PATH_OUTSIDE_WORKSPACE")
    
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
