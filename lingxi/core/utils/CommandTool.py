#!/usr/bin/env python3
"""System execute tool - 继承 ToolBase"""

import logging
import locale
import os
import sys
import platform
import subprocess
import tempfile
import re
import importlib.util
from typing import Dict, Any, Optional
from lingxi.core.utils import ToolExecutionError, ToolValidationError, utils
from lingxi.core.utils.Tool import ToolBase
from lingxi.utils.config import get_config


class CommandTool(ToolBase):
    """系统命令执行工具类"""
    
    def __init__(self):
        super().__init__("execute", "用于执行shell命令，支持powershell、bash等多种shell类型")
        self.temp_files = []  # 跟踪临时文件，确保清理
        config = get_config()
        self.python_interpreter = config.get('python_interpreter', 'python')

    def validate_parameters(self, parameters: Dict[str, Any]) -> bool:
        """校验参数是否符合要求
        
        Args:
            parameters: 执行参数字典
        
        Returns:
            是否校验通过
        """
        command = parameters.get("command")
        cwd = parameters.get("cwd")
        shell_type = parameters.get("shell_type")
        # 参数校验
        if not command:
            raise ToolValidationError("缺少必要参数: command")
            
        if not cwd:
            raise ToolValidationError("缺少必要参数: cwd")
            
        # 检查工作目录是否存在
        if not os.path.exists(cwd):
            raise ToolValidationError(f"指定的工作目录不存在: {cwd}")
            
        if not os.path.isdir(cwd):
            raise ToolValidationError(f"指定的路径不是目录: {cwd}")        
            
        return True
    
    
    def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行系统命令
        
        Args:
            parameters: 执行参数字典
                - command: 要执行的命令内容（必填）
                - cwd: 执行命令的工作目录（必填）
                - shell_type: shell类型（可选，自动检测）
        
        Returns:
            结构化返回结果
                - status: 执行状态 S(成功)/F(失败)
                - error: 错误信息（成功时为空字符串）
                - output: 命令输出内容（失败时也可能有内容）
        """
        command = parameters.get("command")
        cwd = parameters.get("cwd")
        shell_type = parameters.get("shell_type")

        try:
            
            
            # 2. 修复命令中的路径转义问题
            command = self._fix_over_escaped_paths(command)
            self.logger.debug(f"执行命令: {command} (工作目录: {cwd})")
            
            # 3. 自动检测shell类型
            if not shell_type:
                shell_type = "powershell" if platform.system() == "Windows" else "bash"
            
            # 初始化执行相关变量
            process = None
            stdout = ""
            stderr = ""

            python_match = re.match(r'^python\s+-c\s+(["\'])(.*?)\1\s*$', command, re.DOTALL)
            if python_match:
                    # 处理 Python 代码执行
                    python_code = python_match.group(2)
                    
                    # 检查 Python 解释器是否可用
                    if not self._check_python_available():
                        raise ToolExecutionError("Python 环境不可用。请确保已安装 Python 并配置了正确的 python_interpreter 路径。或者尝试使用 PowerShell/Bash 命令替代。")
                    
                    # 创建临时Python文件
                    with tempfile.NamedTemporaryFile(
                        mode='w', suffix='.py', encoding='utf-8',
                        delete=False, dir=cwd
                    ) as f:
                        f.write(python_code)
                        temp_file = f.name
                        self.temp_files.append(temp_file)
                    
                    self.logger.debug(f"使用Python解释器: {self.python_interpreter}")
                    
                    # 执行临时文件（使用UTF-8编码）
                    encoding = 'utf-8'
                    
                    process = subprocess.Popen(
                        [self.python_interpreter, temp_file],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=cwd,
                        encoding=encoding,
                        errors='replace'
                    )
                    stdout, stderr = process.communicate(timeout=30)
            
            # 4. 执行命令
            elif shell_type == "powershell":
                encoding = 'utf-8'
                
                # 检查是否是 Python 代码执行命令
    
                    # 处理普通PowerShell命令
                with tempfile.NamedTemporaryFile(
                        mode='w', suffix='.ps1', encoding='utf-8-sig',
                        delete=False, dir=cwd
                    ) as f:
                        # 设置PowerShell编码
                        f.write('[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n')
                        f.write('$OutputEncoding = [System.Text.Encoding]::UTF8\n')
                        f.write('chcp 65001 | Out-Null\n')
                        f.write(command)
                        f.write('\n')
                        f.write('if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\n')
                        temp_file = f.name
                        self.temp_files.append(temp_file)
                    
                    # 执行PowerShell脚本
                process = subprocess.Popen(
                        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", temp_file],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=cwd,
                        encoding='utf-8',
                        errors='replace'
                    )
                stdout, stderr = process.communicate(timeout=30)
            
            elif shell_type == "bash":
                # 执行bash命令
                process = subprocess.Popen(
                    ["bash", "-c", command],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=cwd,
                    encoding='utf-8',
                    errors='replace'
                )
                stdout, stderr = process.communicate(timeout=30)
            
            else:
                raise ToolExecutionError(f"不支持的shell类型: {shell_type}")
            
            # 5. 处理执行结果
            full_output = stdout + stderr
            # 限制输出长度，最长保留1000个字符
            if len(full_output) > 1000:
                full_output = full_output[:1000] + "..."
            
            # 检查Python错误
            if self._check_python_errors(full_output):
                raise ToolExecutionError(f"检测到Python执行错误: {full_output}")
            
            # 检查错误输出和返回码
            return_code = process.returncode if process else -1
            
            if stderr.strip() or return_code != 0:
                error_msg = f"命令执行失败 (返回码: {return_code}): {stderr.strip()}"
                raise ToolExecutionError(error_msg)
            
            return full_output
        
        except subprocess.TimeoutExpired:
            raise ToolExecutionError("命令执行超时（30秒）")
        
        except Exception as e:
            error_msg = f"执行命令时发生异常: {str(e)}"
            raise ToolExecutionError(error_msg)
        
        finally:
            # 确保临时文件被清理
            self._cleanup_temp_files()
    
    



    def _fix_over_escaped_paths(self, command: str) -> str:
        """修复过度转义的路径
        
        Args:
            command: 原始命令字符串
            
        Returns:
            修复后的命令字符串
        """
        # 匹配 Windows 路径模式（驱动器字母 + 冒号 + 反斜杠 + 路径）
        path_pattern = r'([A-Za-z]):(\\\\+)((?:[^"\'\s\\]+(?:\\\\+)?)+)'
        
        def fix_path(match):
            drive = match.group(1)
            backslashes = match.group(2)
            rest = match.group(3)
            
            # 计算需要的反斜杠数量（2个反斜杠 = 1个实际反斜杠）
            while len(backslashes) > 2:
                backslashes = backslashes[:len(backslashes)//2]
            
            # 确保至少有2个反斜杠（表示1个实际反斜杠）
            if len(backslashes) < 2:
                backslashes = '\\\\'
            
            # 修复路径中间的过度转义
            rest = re.sub(r'\\\\+', lambda m: '\\\\' if len(m.group()) > 2 else m.group(), rest)
            
            return f'{drive}:{backslashes}{rest}'
        
        # 应用修复
        command = re.sub(path_pattern, fix_path, command)
        return command
    
    def _check_python_available(self) -> bool:
        """检查 Python 解释器是否可用
        
        Returns:
            Python 可用返回 True，否则返回 False
        """
        try:
            result = subprocess.run(
                [self.python_interpreter, "--version"],
                capture_output=True,
                timeout=5,
                text=True
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False
    
    def _check_python_errors(self, output: str) -> bool:
        """检查输出中是否包含 Python 错误信息
        
        Args:
            output: 命令执行的输出字符串
            
        Returns:
            存在Python错误返回True，否则返回False
        """
        python_error_indicators = [
            'ModuleNotFoundError', 'ImportError', 'SyntaxError', 
            'NameError', 'Traceback', 'File "<string>"'
        ]
        return any(indicator in output for indicator in python_error_indicators)
    
    def _cleanup_temp_files(self):
        """清理所有临时文件"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                    self.logger.debug(f"临时文件已清理: {temp_file}")
            except Exception as cleanup_err:
                self.logger.warning(f"清理临时文件失败 {temp_file}: {cleanup_err}")
        self.temp_files.clear()
    
    def get_parameters_description(self) -> str:
        """
        获取工具参数描述
        
        Returns:
            参数描述字符串  
        """
        str = f"""- execute 工具调用示例
            ```json
            {{"cwd": "当前工作目录,必填","command": "python -c \"print('Hello World')\"","shell_type": "powershell|bash"}}
            ```"""
        return str


# ------------------- 测试用例 -------------------
if __name__ == "__main__":
    from lingxi.core.utils.Tool import Tool
    
    # 创建工具管理器
    tool_manager = Tool()
    
    # 测试1: 执行简单的目录查看命令
    test_params1 = {
        "cwd": os.getcwd(),
        "command": "dir" if platform.system() == "Windows" else "ls -l",
        "shell_type": ""
    }
    result1 = tool_manager.execute_tool("execute", **test_params1)
    print("测试1结果:")
    print(f"状态: {result1['status']}")
    print(f"错误: {result1['error']}")
    print(f"输出: {result1['output'][:200]}...")  # 只显示前200个字符
    print("-" * 50)
    
    # 测试2: 执行Python代码
    test_params2 = {
        "cwd": os.getcwd(),
        "command": 'python -c "print(\'Hello World\'); import sys; print(sys.version)"',
        "shell_type": ""
    }
    result2 = tool_manager.execute_tool("execute", **test_params2)
    print("测试2结果:")
    print(f"状态: {result2['status']}")
    print(f"错误: {result2['error']}")
    print(f"输出: {result2['output']}")
    print("-" * 50)
    
    # 测试3: 执行错误的命令
    test_params3 = {
        "cwd": os.getcwd(),
        "command": "invalid_command_123456",
        "shell_type": ""
    }
    result3 = tool_manager.execute_tool("execute", **test_params3)
    print("测试3结果:")
    print(f"状态: {result3['status']}")
    print(f"错误: {result3['error']}")
    print(f"输出: {result3['output']}")
    
    # 列出所有工具
    print("\n=== 所有工具 ===")
    for name, info in tool_manager.list_tools().items():
        print(f"- {name}: {info['description']}")