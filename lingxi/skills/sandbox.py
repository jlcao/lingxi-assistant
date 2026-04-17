#!/usr/bin/env python3
"""分级安全沙盒 - L1（线程）/ L2（子进程）

根据设计文档要求：
- L1（受信任技能）：线程 + 钩子拦截
- L2（第三方/不可信）：子进程 + 独立 venv
"""

import logging
import sys
import os
import subprocess
import threading
from typing import Any, Dict, Optional, Callable
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, TimeoutError

from .skill_response import ToolResponse, ResponseCode
from .execution_context import ExecutionContext, TrustLevel


class SandboxError(Exception):
    """沙盒异常"""
    pass


class SandboxLevel(str):
    """沙盒等级"""
    L1 = "L1"
    L2 = "L2"


class L1Sandbox:
    """L1 沙盒 - 线程级隔离（受信任技能）

    使用线程池执行，提供基本的钩子拦截。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self._executor = ThreadPoolExecutor(
            max_workers=self.config.get("l1_max_workers", 10),
            thread_name_prefix="sandbox-l1"
        )
        self._intercept_hooks: Dict[str, Callable] = {}
        self.logger.info("L1 沙盒已初始化")

    def run(
        self,
        func: Callable,
        *args,
        skill_id: Optional[str] = None,
        context: Optional[ExecutionContext] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> ToolResponse:
        """在 L1 沙盒中执行函数

        Args:
            func: 要执行的函数
            *args: 位置参数
            skill_id: 技能ID
            context: 执行上下文
            timeout: 超时时间（秒）
            **kwargs: 关键字参数

        Returns:
            SkillResponse 实例
        """
        import time

        trace_id = context.trace_id if context else None
        start_time = time.time()

        def wrapped():
            try:
                self._before_execution(skill_id, context)
                result = func(*args, **kwargs)
                self._after_execution(skill_id, context)
                return result
            except Exception as e:
                self.logger.error(f"L1 沙盒执行异常: {skill_id}", exc_info=e)
                raise

        try:
            future = self._executor.submit(wrapped)
            result = future.result(timeout=timeout)

            cost_ms = (time.time() - start_time) * 1000

            if isinstance(result, ToolResponse):
                resp = result
            else:
                resp = ToolResponse.success(
                    data=result,
                    skill_id=skill_id,
                    trace_id=trace_id,
                    cost_ms=cost_ms
                )

            return resp

        except TimeoutError:
            cost_ms = (time.time() - start_time) * 1000
            return ToolResponse.error(
                message=f"技能执行超时（{timeout}秒）",
                code=ResponseCode.INTERNAL_ERROR,
                skill_id=skill_id,
                trace_id=trace_id
            )
        except Exception as e:
            cost_ms = (time.time() - start_time) * 1000
            return ToolResponse.error(
                message=f"L1 沙盒执行失败: {str(e)}",
                code=ResponseCode.INTERNAL_ERROR,
                skill_id=skill_id,
                trace_id=trace_id
            )

    def _before_execution(self, skill_id: Optional[str], context: Optional[ExecutionContext]):
        """执行前钩子"""
        self.logger.debug(f"L1 沙盒执行前: {skill_id}")

    def _after_execution(self, skill_id: Optional[str], context: Optional[ExecutionContext]):
        """执行后钩子"""
        self.logger.debug(f"L1 沙盒执行后: {skill_id}")

    def shutdown(self, wait: bool = True):
        """关闭沙盒"""
        self._executor.shutdown(wait=wait)
        self.logger.info("L1 沙盒已关闭")


class L2Sandbox:
    """L2 沙盒 - 进程级隔离（第三方/不可信技能）

    使用独立子进程执行，支持 venv 虚拟环境隔离。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self._venv_base_path = Path(self.config.get("l2_venv_base", "./venvs")).resolve()
        self._venv_base_path.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"L2 沙盒已初始化，venv 目录: {self._venv_base_path}")

    def run(
        self,
        skill_dir: str,
        parameters: Dict[str, Any],
        skill_id: Optional[str] = None,
        context: Optional[ExecutionContext] = None,
        timeout: Optional[float] = None,
        use_venv: bool = False
    ) -> ToolResponse:
        """在 L2 沙盒中执行技能

        Args:
            skill_dir: 技能目录
            parameters: 技能参数
            skill_id: 技能ID
            context: 执行上下文
            timeout: 超时时间（秒）
            use_venv: 是否使用 venv

        Returns:
            SkillResponse 实例
        """
        import time
        import json
        import tempfile

        trace_id = context.trace_id if context else None
        start_time = time.time()

        skill_path = Path(skill_dir)
        main_py = skill_path / "main.py"

        if not main_py.exists():
            return ToolResponse.error(
                message=f"技能主文件不存在: {main_py}",
                skill_id=skill_id,
                trace_id=trace_id
            )

        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
                json.dump(parameters, f)
                params_file = f.name

            python_exec = self._get_python_executable(skill_id, use_venv)

            cmd = [
                str(python_exec),
                str(main_py),
                '--params', params_file
            ]

            self.logger.debug(f"L2 沙盒执行: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                timeout=timeout,
                cwd=str(skill_path)
            )

            try:
                os.unlink(params_file)
            except:
                pass

            cost_ms = (time.time() - start_time) * 1000

            if result.returncode == 0:
                output = result.stdout.strip()
                try:
                    resp_data = json.loads(output)
                    if "success" in resp_data:
                        resp = ToolResponse.from_dict(resp_data)
                    else:
                        resp = ToolResponse.success(data=output)
                except json.JSONDecodeError:
                    resp = ToolResponse.success(data=output)

                resp.meta["cost_ms"] = cost_ms
                return resp
            else:
                error_msg = result.stderr.strip() or result.stdout.strip() or "未知错误"
                return ToolResponse.error(
                    message=f"L2 沙盒执行失败: {error_msg}",
                    skill_id=skill_id,
                    trace_id=trace_id
                )

        except subprocess.TimeoutExpired:
            cost_ms = (time.time() - start_time) * 1000
            return ToolResponse.error(
                message=f"L2 沙盒执行超时（{timeout}秒）",
                skill_id=skill_id,
                trace_id=trace_id
            )
        except Exception as e:
            cost_ms = (time.time() - start_time) * 1000
            self.logger.error(f"L2 沙盒执行异常: {skill_id}", exc_info=e)
            return ToolResponse.error(
                message=f"L2 沙盒执行异常: {str(e)}",
                skill_id=skill_id,
                trace_id=trace_id
            )

    def _get_python_executable(self, skill_id: Optional[str], use_venv: bool) -> Path:
        """获取 Python 解释器路径

        Args:
            skill_id: 技能ID
            use_venv: 是否使用 venv

        Returns:
            Python 解释器路径
        """
        # 首先检查配置中是否指定了 Python 路径
        skills_config = self.config.get("skills", {})
        python_path_config = skills_config.get("python_path")
        if python_path_config and not use_venv:
            python_path = Path(python_path_config)
            if python_path.exists():
                return python_path
            else:
                self.logger.warning(f"配置的 Python 路径不存在: {python_path_config}")

        if not use_venv:
            return Path(sys.executable)

        if not skill_id:
            return Path(sys.executable)

        venv_path = self._venv_base_path / skill_id
        if not venv_path.exists():
            self._create_venv(skill_id)

        if sys.platform == "win32":
            python_path = venv_path / "Scripts" / "python.exe"
        else:
            python_path = venv_path / "bin" / "python"

        if python_path.exists():
            return python_path

        return Path(sys.executable)

    def _create_venv(self, skill_id: str):
        """创建 venv 虚拟环境

        Args:
            skill_id: 技能ID
        """
        import venv

        venv_path = self._venv_base_path / skill_id
        self.logger.info(f"创建 venv 环境: {venv_path}")
        venv.create(str(venv_path), with_pip=True)

    def install_dependencies(self, skill_id: str, requirements_path: str):
        """安装技能依赖

        Args:
            skill_id: 技能ID
            requirements_path: requirements.txt 路径
        """
        python_exec = self._get_python_executable(skill_id, use_venv=True)
        pip_path = python_exec.parent / ("pip.exe" if sys.platform == "win32" else "pip")

        cmd = [str(pip_path), "install", "-r", requirements_path]
        self.logger.info(f"安装依赖: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)


class SandboxManager:
    """沙盒管理器 - 统一管理 L1/L2 沙盒"""

    _instance = None
    _initialized = False

    def __new__(cls, config: Optional[Dict[str, Any]] = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        if self._initialized:
            return

        self.config = config or {}
        self.logger = logging.getLogger(__name__)

        self._l1_sandbox = L1Sandbox(config)
        self._l2_sandbox = L2Sandbox(config)

        self._initialized = True
        self.logger.info("沙盒管理器已初始化")

    def run(
        self,
        func_or_dir: Any,
        *args,
        skill_id: Optional[str] = None,
        context: Optional[ExecutionContext] = None,
        trust_level: TrustLevel = TrustLevel.L1,
        timeout: Optional[float] = None,
        **kwargs
    ) -> ToolResponse:
        """在合适的沙盒中执行

        Args:
            func_or_dir: 函数（L1）或技能目录（L2）
            *args: 位置参数
            skill_id: 技能ID
            context: 执行上下文
            trust_level: 信任等级
            timeout: 超时时间
            **kwargs: 关键字参数

        Returns:
            SkillResponse 实例
        """
        if trust_level == TrustLevel.L2:
            if isinstance(func_or_dir, str) and os.path.isdir(func_or_dir):
                parameters = kwargs.get("parameters", {})
                return self._l2_sandbox.run(
                    func_or_dir,
                    parameters,
                    skill_id=skill_id,
                    context=context,
                    timeout=timeout
                )
            else:
                self.logger.warning(f"L2 信任等级需要技能目录，降级为 L1")

        return self._l1_sandbox.run(
            func_or_dir,
            *args,
            skill_id=skill_id,
            context=context,
            timeout=timeout,
            **kwargs
        )

    def shutdown(self, wait: bool = True):
        """关闭所有沙盒"""
        self._l1_sandbox.shutdown(wait=wait)
        self.logger.info("沙盒管理器已关闭")

