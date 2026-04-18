#!/usr/bin/env python3
"""技能加载器，负责扫描和自动注册技能"""

import os
import json
import yaml
import logging
import importlib.util
import subprocess
import sys
import gc
import venv
import shutil
from typing import Dict, List, Optional, Any
from pathlib import Path
from lingxi.utils.config import get_workspace_path


class SkillLoader:
    """技能加载器，负责扫描和自动注册技能（单例模式）"""
    
    _instance = None  # 单例实例
    
    def __new__(cls, config: Dict[str, Any], registry=None, cache=None, sandbox=None, **kwargs):
        """单例模式：确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config: Dict[str, Any], registry=None, cache=None, sandbox=None, **kwargs):
        # 防止重复初始化
        if hasattr(self, '_initialized'):
            return
        
        """初始化技能加载器

        Args:
            config: 系统配置
            registry: 技能注册表对象
            cache: 技能缓存对象（可选）
            sandbox: 安全沙箱对象（可选）
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 技能目录路径
        skills_config = config.get("skills", {})
        self.builtin_skills_dir = skills_config.get("builtin_skills_dir", "lingxi/skills/builtin")
        self.user_skills_dir = skills_config.get("user_skills_dir", ".lingxi/skills")

        # 注册表和缓存引用
        self.registry = registry
        self.cache = cache  # 新增缓存引用
        self.sandbox = sandbox  # 新增沙箱引用，用于路径转换

        # ========== 新增：内置Python解释器路径处理 ==========
        self.python_interpreter = self._get_bundled_python_interpreter()
        self.logger.debug(f"使用的Python解释器路径: {self.python_interpreter}")

        self.logger.debug(f"初始化技能加载器，内置技能目录: {self.builtin_skills_dir}, 用户技能目录: {self.user_skills_dir}")
        self._initialized = True

    def _get_bundled_python_interpreter(self) -> str:
        """获取打包EXE内置的Python解释器路径"""
        # 判断是否是PyInstaller打包后的环境
        if getattr(sys, 'frozen', False):
            # _MEIPASS 是PyInstaller解压临时文件的目录（--onefile打包时）
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
            python_exe = "python.exe" if sys.platform == "win32" else "python3"
            
            # 拼接Python解释器路径（适配不同打包方式）
            python_path = os.path.join(base_path, python_exe)
            
            # 兜底：如果临时目录找不到，用sys.executable所在目录（--onedir打包）
            if not os.path.exists(python_path):
                python_path = os.path.join(os.path.dirname(sys.executable), python_exe)
            
            # 最终兜底：使用当前运行的Python解释器
            if not os.path.exists(python_path):
                python_path = sys.executable
                
            return python_path
        else:
            # 非打包环境，返回当前运行的Python解释器
            return sys.executable

    def scan_and_register(self, registry) -> int:
        """扫描技能目录并自动注册所有技能

        Args:
            registry: 技能注册表对象

        Returns:
            成功注册的技能数量
        """
        self.logger.debug("开始扫描技能目录...")

        registered_count = 0

        for skill_dir in self._find_skill_directories():
            try:
                skill_config = self._load_skill_config(skill_dir)
                if skill_config:
                    if self._register_skill(registry, skill_dir, skill_config):
                        registered_count += 1
            except Exception as e:
                self.logger.error(f"注册技能失败 {skill_dir}: {e}")

        self.logger.debug(f"技能扫描完成，成功注册 {registered_count} 个技能")
        return registered_count
    
    def _register_skill(self, registry, skill_dir: str, skill_config: Dict[str, Any]) -> bool:
        """注册单个技能到注册表
        
        Args:
            registry: 技能注册表
            skill_dir: 技能目录路径
            skill_config: 技能配置
            
        Returns:
            是否注册成功
        """
        try:
            skill_id = skill_config.get('name', '')
            if not skill_id:
                self.logger.error(f"技能配置缺少 name 字段：{skill_dir}")
                return False
            
            # 检查是否有 main.py 文件
            has_main_py = os.path.exists(os.path.join(skill_dir, "main.py"))
            
            # 统一使用 register_skill 方法注册，传入完整的 skill_config
            if hasattr(registry, 'register_skill'):
                # 添加额外信息到 skill_config
                skill_config['source'] = 'global'
                skill_config['path'] = str(skill_dir)
                registry.register_skill(skill_config)
                self.logger.info(f"注册技能成功：{skill_id}")
            else:
                self.logger.error(f"Registry 对象没有 register_skill 方法")
                return False
            
            # 注册成功后，加载技能模块到内存
            self._load_local_skill_module(skill_dir, skill_id)
            
            return True
                
        except Exception as e:
            self.logger.error(f"注册技能失败 {skill_dir}: {e}")
            return False

    def _find_skill_directories(self) -> List[str]:
        """查找所有技能目录

        Returns:
            技能目录路径列表
        """
        skill_dirs = []

        self.logger.info(f"开始扫描技能目录，内置技能目录: {self.builtin_skills_dir}, 用户技能目录: {self.user_skills_dir}")
        # 扫描内置技能目录
        workspace_skills_dir = f"{get_workspace_path()}/.lingxi/skills"
        for skills_path in [self.builtin_skills_dir, self.user_skills_dir, workspace_skills_dir]:
            try:
                # ========== 修复：适配打包后的路径 ==========
                # 处理打包后相对路径的问题
                if getattr(sys, 'frozen', False):
                    # 打包后，基于EXE所在目录构建绝对路径
                    exe_dir = os.path.dirname(sys.executable)
                    skills_path = os.path.join(exe_dir, skills_path)
                
                skills_path_obj = Path(skills_path)
                self.logger.info(f"扫描技能目录: {skills_path}, 存在: {skills_path_obj.exists()}")
                if not skills_path_obj.exists():
                    continue

                self.logger.info(f"技能目录 {skills_path} 存在，开始扫描子目录")
                for item in skills_path_obj.iterdir():
                    # 支持两种格式：
                    # 1. 以Skill结尾的目录（传统格式，如PdfParserSkill）
                    # 2. 包含SKILL.md的目录（MCP格式，如docx、pdf、xlsx）
                    if item.is_dir():
                        if item.name.endswith("Skill"):
                            skill_dirs.append(str(item))
                            skill_type = "内置" if skills_path == self.builtin_skills_dir else "用户"
                            self.logger.info(f"发现技能目录（{skill_type}，传统格式）: {item.name}")
                        else:
                            # 检查是否包含SKILL.md文件
                            skill_md_path = item / "SKILL.md"
                            if skill_md_path.exists():
                                skill_dirs.append(str(item))
                                skill_type = "内置" if skills_path == self.builtin_skills_dir else "用户"
                                self.logger.info(f"发现技能目录（{skill_type}，MCP格式）: {item.name}")

            except Exception as e:
                self.logger.error(f"扫描技能目录失败 {skills_path}: {e}")

        self.logger.info(f"技能目录扫描完成，发现 {len(skill_dirs)} 个技能目录")
        return skill_dirs

    def _load_skill_config(self, skill_dir: str) -> Optional[Dict[str, Any]]:
        """加载技能配置文件（带缓存）

        Args:
            skill_dir: 技能目录路径

        Returns:
            技能配置字典，失败返回 None
        """
        # 从 skill_dir 生成 skill_id
        skill_id = os.path.basename(skill_dir)
        
        # 检查缓存
        if self.cache:
            cached_config = self.cache.get_config(skill_id)
            if cached_config:
                self.logger.debug(f"使用缓存的技能配置：{skill_id}")
                return cached_config
        
        # 优先尝试 skill.json（传统格式）
        config_path = os.path.join(skill_dir, "skill.json")

        if os.path.exists(config_path):
            config = self._load_json_config(config_path)
            if config:
                # 添加 skill_id 字段
                config['skill_id'] = skill_id
                # 缓存配置
                if self.cache:
                    self.cache.set_config(skill_id, config, config_path)
            return config

        # 尝试 SKILL.md（MCP 格式）
        skill_md_path = os.path.join(skill_dir, "SKILL.md")
        
        if os.path.exists(skill_md_path):
            config = self._load_mcp_config(skill_md_path)
            if config:
                # 添加 skill_id 字段
                config['skill_id'] = skill_id
                # 缓存配置
                if self.cache:
                    file_path = skill_md_path if os.path.exists(skill_md_path) else os.path.join(skill_dir, "main.py")
                    self.cache.set_config(skill_id, config, file_path)
                
                # 读取并缓存 SKILL.md 内容
                try:
                    with open(skill_md_path, 'r', encoding='utf-8') as f:
                        md_content = f.read()
                    # 缓存 SKILL.md 内容
                    if self.cache:
                        self.cache.set_md_content(skill_id, md_content, skill_md_path)
                        self.logger.debug(f"SKILL.md 内容已缓存：{skill_id}")
                except Exception as e:
                    self.logger.warning(f"读取 SKILL.md 内容失败：{e}")
                
                # 缓存技能目录下的所有文件
                if self.cache:
                    try:
                        cached_count = self.cache.cache_skill_files(skill_id, skill_dir)
                        self.logger.debug(f"技能文件已缓存：{skill_id} ({cached_count} 个文件)")
                    except Exception as e:
                        self.logger.warning(f"缓存技能文件失败：{e}")
            
            return config
        
        self.logger.warning(f"技能配置文件不存在：{skill_dir}")
        return None
    
    def _load_json_config(self, config_path: str) -> Optional[Dict[str, Any]]:
        """从 skill.json 文件加载 JSON 格式配置
        
        Args:
            config_path: skill.json 文件路径
            
        Returns:
            技能配置字典
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config
        except Exception as e:
            self.logger.error(f"加载 skill.json 失败：{e}")
            return None
    
    def _load_mcp_config(self, skill_md_path: str) -> Optional[Dict[str, Any]]:
        """从 SKILL.md 文件加载 MCP 格式配置
        
        Args:
            skill_md_path: SKILL.md 文件路径
            
        Returns:
            技能配置字典
        """
        try:
            import re
            
            with open(skill_md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析 YAML front matter
            yaml_match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
            if not yaml_match:
                # 尝试匹配没有空行的情况
                yaml_match = re.search(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
                if not yaml_match:
                    return None
            
            yaml_content = yaml_match.group(1)
            
            # 简单的 YAML 解析
            config = {}
            for line in yaml_content.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if value.lower() == 'true':
                        value = True
                    elif value.lower() == 'false':
                        value = False
                    elif value.isdigit():
                        value = int(value)
                    config[key] = value
            
            return config
            
        except Exception as e:
            self.logger.error(f"加载 SKILL.md 失败：{e}")
            return None
    
    def _load_local_skill_module(self, skill_dir: str, skill_id: str):
        """加载本地技能模块（适配打包后的Python环境）

        Args:
            skill_dir: 技能目录路径
            skill_id: 技能ID
        """
        if not self.cache:
            self.logger.warning("缓存未初始化，无法加载技能模块")
            return
        
        main_py_path = os.path.join(skill_dir, "main.py")

        if not os.path.exists(main_py_path):
            self.logger.debug(f"本地技能无main.py文件: {skill_id}")
            return

        try:
            module_name = f"skill_{skill_id.replace('.', '_')}"
            sys.path.insert(0, skill_dir)
            
            spec = importlib.util.spec_from_file_location(module_name, main_py_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                module.__file__ = main_py_path
                spec.loader.exec_module(module)

                self.cache.set_module(skill_id, module, main_py_path)

                if hasattr(module, "init"):
                    module.init()
                    self.logger.debug(f"本地技能初始化函数已调用: {skill_id}")

                self.logger.debug(f"本地技能模块加载成功: {skill_id}")
            else:
                self.logger.warning(f"importlib加载失败，使用subprocess执行: {skill_id}")
                self.cache.set_module(skill_id, {
                    'type': 'external',
                    'path': main_py_path,
                    'skill_dir': skill_dir
                }, main_py_path)

        except Exception as e:
            self.logger.error(f"加载本地技能模块失败 {skill_id}: {e}")
            self.cache.set_module(skill_id, {
                'type': 'external',
                'path': main_py_path,
                'skill_dir': skill_dir
            }, main_py_path)

    def execute_local_skill(self, skill_id: str, parameters: Dict[str, Any]) -> str:
        """执行本地技能（适配打包后的Python环境，统一处理所有MCP格式技能）

        Args:
            skill_id: 技能ID
            parameters: 技能参数

        Returns:
            执行结果
        """
        if not self.cache:
            return f"错误: 缓存未初始化: {skill_id}"
        
        if not self.cache.has_module(skill_id):
            return f"错误: 技能模块未加载: {skill_id}"

        if self.sandbox and parameters:
            parameters = self._normalize_paths(parameters, skill_id)

        module = self.cache.get_module(skill_id)

        try:
            if isinstance(module, type(sys)):
                if hasattr(module, "execute"):
                    result = module.execute(parameters)

                    if isinstance(result, dict):
                        if result.get("success"):
                            return result.get("result", "")
                        else:
                            return result.get("error", "技能执行失败")
                    else:
                        return str(result)
                else:
                    return f"错误: 技能模块缺少execute函数: {skill_id}"
            
            elif isinstance(module, dict) and module.get('type') == 'external':
                main_py_path = module.get('path')
                if not main_py_path or not os.path.exists(main_py_path):
                    return f"错误: 技能文件不存在: {main_py_path}"
                
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
                    json.dump(parameters, f)
                    params_file = f.name
                
                cmd = [
                    self.python_interpreter,
                    main_py_path,
                    '--params', params_file
                ]
                
                self.logger.debug(f"执行外部技能: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    encoding="utf-8",
                    cwd=module.get('skill_dir'),
                    timeout=300
                )
                
                try:
                    os.unlink(params_file)
                except:
                    pass
                
                if result.returncode == 0:
                    return result.stdout.strip()
                else:
                    error_msg = f"技能执行失败 (返回码: {result.returncode}): {result.stderr.strip()}"
                    self.logger.error(error_msg)
                    return error_msg
            
            else:
                return f"错误: 不支持的技能模块类型: {skill_id}"

        except Exception as e:
            self.logger.error(f"执行技能失败 {skill_id}: {e}")
            return f"错误: 技能执行失败 - {str(e)}"

    def _normalize_paths(self, parameters: Dict[str, Any], skill_id: str) -> Dict[str, Any]:
        """转换路径参数为绝对路径（基于当前工作目录）

        Args:
            parameters: 技能参数
            skill_id: 技能ID

        Returns:
            转换后的参数
        """
        from pathlib import Path
        
        # 定义需要转换路径的参数名
        path_params = ['file_path', 'file', 'path', 'directory', 'dir', 'workspace', 'workspace_path']
        
        normalized = {}
        for key, value in parameters.items():
            if key in path_params and isinstance(value, str):
                # 如果是相对路径，转换为基于工作目录的绝对路径
                if not Path(value).is_absolute():
                    workspace_root = self.sandbox.get_workspace_root() if self.sandbox else Path.cwd()
                    normalized_value = str(workspace_root / value)
                    self.logger.debug(f"路径转换: {skill_id}.{key}: {value} -> {normalized_value}")
                    normalized[key] = normalized_value
                else:
                    normalized[key] = value
            else:
                normalized[key] = value
        
        return normalized

    def install_skill(self, skill_source: str, registry, skill_name: str = None, overwrite: bool = False) -> bool:
        """安装技能到用户技能目录

        Args:
            skill_source: 技能源路径（目录路径或技能名称）
            registry: 技能注册表对象
            skill_name: 可选的技能名称（如果skill_source是路径，可以指定新名称）
            overwrite: 是否覆盖已存在的技能目录

        Returns:
            是否安装成功
        """
        try:
            source_path = Path(skill_source)

            if not source_path.exists():
                self.logger.error(f"技能源不存在: {skill_source}")
                return False

            if not source_path.is_dir():
                self.logger.error(f"技能源必须是目录: {skill_source}")
                return False

            self.logger.debug(f"开始安装技能: {skill_source}")

            target_dir_name = skill_name if skill_name else source_path.name
            # ========== 修复：适配打包后的目标路径 ==========
            if getattr(sys, 'frozen', False):
                exe_dir = os.path.dirname(sys.executable)
                target_dir = Path(exe_dir).resolve() / self.user_skills_dir / target_dir_name
            else:
                target_dir = Path(self.user_skills_dir).resolve() / target_dir_name

            if target_dir.exists():
                if not overwrite:
                    self.logger.warning(f"技能目录已存在: {target_dir}")
                    return False
                else:
                    import shutil
                    shutil.rmtree(target_dir)
                    self.logger.debug(f"删除已存在的技能目录: {target_dir}")

            os.makedirs(target_dir, exist_ok=True)

            for item in source_path.iterdir():
                if item.is_file():
                    import shutil
                    shutil.copy2(item, target_dir / item.name)
                    self.logger.debug(f"复制文件: {item.name}")

            self.logger.debug(f"技能目录创建完成: {target_dir}")

            skill_config = self._load_skill_config(str(target_dir))
            if not skill_config:
                self.logger.error(f"无法加载技能配置: {target_dir}")
                return False

            if self._register_skill(registry, str(target_dir), skill_config):
                self.logger.debug(f"技能安装成功: {skill_config.get('skill_id')}")
                return True
            else:
                self.logger.error(f"技能注册失败: {skill_config.get('skill_id')}")
                return False

        except Exception as e:
            self.logger.error(f"安装技能失败 {skill_source}: {e}")
            return False

    def get_skill_config(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """获取技能配置

        Args:
            skill_id: 技能ID

        Returns:
            技能配置字典
        """
        for skill_dir in self._find_skill_directories():
            config = self._load_skill_config(skill_dir)
            if config and config.get("skill_id") == skill_id:
                return config
        return None
    
    def unload_module(self, skill_id: str) -> bool:
        """显式卸载技能模块（防止内存泄漏）
        
        Args:
            skill_id: 技能ID
            
        Returns:
            是否卸载成功
        """
        self.logger.info(f"开始卸载技能模块：{skill_id}")
        
        if not self.cache:
            self.logger.warning("缓存未初始化，无法卸载技能模块")
            return False
        
        try:
            if not self.cache.has_module(skill_id):
                self.logger.warning(f"技能模块未加载，无需卸载：{skill_id}")
                return True
            
            self.cache.invalidate(skill_id)
            self.logger.info(f"技能模块卸载成功：{skill_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"卸载技能模块失败 {skill_id}: {e}")
            return False
    
    def unload_all(self) -> int:
        """卸载所有已加载的技能模块
        
        Returns:
            成功卸载的技能数量
        """
        self.logger.info("开始卸载所有技能模块")
        
        if not self.cache:
            self.logger.warning("缓存未初始化，无法卸载技能模块")
            return 0
        
        count = 0
        skill_ids = self.cache.list_loaded_modules()
        
        for skill_id in skill_ids:
            if self.unload_module(skill_id):
                count += 1
        
        gc.collect()
        self.logger.info(f"完成卸载所有技能模块，共 {count} 个")
        return count
    
    def _get_skill_dir(self, skill_id):
        """获取技能目录路径
        
        Args:
            skill_id: 技能ID
            
        Returns:
            技能目录路径，未找到返回 None
        """
        for skill_dir in self._find_skill_directories():
            if os.path.basename(skill_dir) == skill_id:
                return skill_dir
        return None
    
    def has_virtual_env(self, skill_id_or_dir):
        """检测技能是否有虚拟环境
        
        Args:
            skill_id_or_dir: 技能ID 或技能目录路径
            
        Returns:
            是否存在虚拟环境
        """
        if os.path.isdir(skill_id_or_dir):
            skill_dir = skill_id_or_dir
        else:
            skill_dir = self._get_skill_dir(skill_id_or_dir)
            if not skill_dir:
                self.logger.warning(f"技能目录不存在：{skill_id_or_dir}")
                return False
        
        venv_dir = os.path.join(skill_dir, ".venv")
        exists = os.path.exists(venv_dir) and os.path.isdir(venv_dir)
        
        if exists:
            self.logger.debug(f"技能 {os.path.basename(skill_dir)} 已存在虚拟环境：{venv_dir}")
        else:
            self.logger.debug(f"技能 {os.path.basename(skill_dir)} 不存在虚拟环境")
        
        return exists
    
    def create_venv(self, skill_id_or_dir, upgrade_pip=True):
        """为技能创建虚拟环境
        
        Args:
            skill_id_or_dir: 技能ID 或技能目录路径
            upgrade_pip: 是否升级 pip
            
        Returns:
            是否创建成功
        """
        if os.path.isdir(skill_id_or_dir):
            skill_dir = skill_id_or_dir
        else:
            skill_dir = self._get_skill_dir(skill_id_or_dir)
            if not skill_dir:
                self.logger.error(f"技能目录不存在：{skill_id_or_dir}")
                return False
        
        venv_dir = os.path.join(skill_dir, ".venv")
        
        if os.path.exists(venv_dir):
            self.logger.warning(f"技能虚拟环境已存在，跳过创建：{venv_dir}")
            return True
        
        try:
            self.logger.info(f"开始为技能 {os.path.basename(skill_dir)} 创建虚拟环境：{venv_dir}")
            
            venv.create(venv_dir, with_pip=True)
            self.logger.info(f"虚拟环境创建成功：{venv_dir}")
            
            if upgrade_pip:
                pip_path = self._get_pip_path(venv_dir)
                if pip_path and os.path.exists(pip_path):
                    self.logger.info(f"升级 pip...")
                    result = subprocess.run(
                        [pip_path, "install", "--upgrade", "pip"],
                        capture_output=True,
                        text=True,
                        cwd=skill_dir
                    )
                    if result.returncode == 0:
                        self.logger.info("pip 升级成功")
                    else:
                        self.logger.warning(f"pip 升级失败：{result.stderr}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"创建虚拟环境失败 {os.path.basename(skill_dir)}: {e}")
            if os.path.exists(venv_dir):
                shutil.rmtree(venv_dir)
            return False
    
    def _get_pip_path(self, venv_dir):
        """获取虚拟环境中 pip 的路径
        
        Args:
            venv_dir: 虚拟环境目录
            
        Returns:
            pip 可执行文件路径
        """
        if sys.platform == "win32":
            pip_path = os.path.join(venv_dir, "Scripts", "pip.exe")
        else:
            pip_path = os.path.join(venv_dir, "bin", "pip")
        
        if os.path.exists(pip_path):
            return pip_path
        return None
    
    def _get_python_path(self, venv_dir):
        """获取虚拟环境中 Python 的路径
        
        Args:
            venv_dir: 虚拟环境目录
            
        Returns:
            Python 可执行文件路径
        """
        if sys.platform == "win32":
            python_path = os.path.join(venv_dir, "Scripts", "python.exe")
        else:
            python_path = os.path.join(venv_dir, "bin", "python")
        
        if os.path.exists(python_path):
            return python_path
        return None
    
    def install_dependencies(self, skill_id_or_dir, requirements_file=None):
        """安装技能依赖
        
        Args:
            skill_id_or_dir: 技能ID 或技能目录路径
            requirements_file: 依赖文件路径，默认使用 requirements.txt
            
        Returns:
            是否安装成功
        """
        if os.path.isdir(skill_id_or_dir):
            skill_dir = skill_id_or_dir
        else:
            skill_dir = self._get_skill_dir(skill_id_or_dir)
            if not skill_dir:
                self.logger.error(f"技能目录不存在：{skill_id_or_dir}")
                return False
        
        venv_dir = os.path.join(skill_dir, ".venv")
        if not os.path.exists(venv_dir):
            self.logger.info(f"技能虚拟环境不存在，先创建：{os.path.basename(skill_dir)}")
            if not self.create_venv(skill_dir):
                return False
        
        pip_path = self._get_pip_path(venv_dir)
        if not pip_path:
            self.logger.error(f"无法找到 pip 可执行文件：{venv_dir}")
            return False
        
        if not requirements_file:
            requirements_file = os.path.join(skill_dir, "requirements.txt")
        
        if not os.path.exists(requirements_file):
            self.logger.info(f"依赖文件不存在，跳过安装：{requirements_file}")
            return True
        
        try:
            self.logger.info(f"开始安装技能 {os.path.basename(skill_dir)} 的依赖：{requirements_file}")
            
            result = subprocess.run(
                [pip_path, "install", "-r", requirements_file],
                capture_output=True,
                text=True,
                cwd=skill_dir
            )
            
            if result.returncode == 0:
                self.logger.info(f"依赖安装成功：{os.path.basename(skill_dir)}")
                if result.stdout:
                    self.logger.debug(f"安装输出：{result.stdout}")
                return True
            else:
                self.logger.error(f"依赖安装失败 {os.path.basename(skill_dir)}: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"安装依赖时出错 {os.path.basename(skill_dir)}: {e}")
            return False
    
    def get_venv_python_path(self, skill_id_or_dir):
        """获取技能虚拟环境的 Python 解释器路径
        
        Args:
            skill_id_or_dir: 技能ID 或技能目录路径
            
        Returns:
            Python 解释器路径，未找到返回 None
        """
        if os.path.isdir(skill_id_or_dir):
            skill_dir = skill_id_or_dir
        else:
            skill_dir = self._get_skill_dir(skill_id_or_dir)
            if not skill_dir:
                return None
        
        venv_dir = os.path.join(skill_dir, ".venv")
        if not os.path.exists(venv_dir):
            return None
        
        return self._get_python_path(venv_dir)