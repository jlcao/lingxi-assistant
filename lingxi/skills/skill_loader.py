#!/usr/bin/env python3
"""技能加载器，负责扫描和自动注册技能"""

import os
import json
import yaml
import logging
import importlib.util
from typing import Dict, List, Optional, Any
from pathlib import Path


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

        # 已加载的技能模块（Python模块对象，用于执行技能）
        self.loaded_modules: Dict[str, Any] = {}

        # MCP格式技能配置（SKILL.md格式的技能，存储配置信息）
        self.mcp_skills: Dict[str, Dict[str, Any]] = {}

        # 注册表和缓存引用
        self.registry = registry
        self.cache = cache  # 新增缓存引用
        self.sandbox = sandbox  # 新增沙箱引用，用于路径转换

        self.logger.debug(f"初始化技能加载器，内置技能目录: {self.builtin_skills_dir}, 用户技能目录: {self.user_skills_dir}")
        self._initialized = True

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
            
            # 根据是否有 main.py 文件选择注册方法
            if has_main_py and hasattr(registry, 'register_skill_from_dir'):
                registry.register_skill_from_dir(Path(skill_dir))
                self.logger.info(f"注册技能成功：{skill_id}")
            elif hasattr(registry, 'register_skill'):
                # 兼容两种 registry 实现：
                # 1. registry.py: register_skill(name, description, author, version, parameters)
                # 2. registry_memory.py: register_skill(skill_config)
                try:
                    # 尝试使用分开参数的方式（registry.py）
                    registry.register_skill(
                        name=skill_config.get('name', skill_id),
                        description=skill_config.get('description', ''),
                        author=skill_config.get('author', ''),
                        version=skill_config.get('version', '1.0.0'),
                        parameters=skill_config.get('parameters')
                    )
                    self.logger.info(f"注册技能成功：{skill_id}")
                except TypeError:
                    # 如果失败，使用字典方式（registry_memory.py）
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
        for skills_path in [self.builtin_skills_dir, self.user_skills_dir]:
            try:
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
    
    def _parse_parameters(self, input_schema: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """解析输入参数配置

        Args:
            input_schema: 输入参数模式

        Returns:
            参数列表
        """
        parameters = []

        if not input_schema:
            return parameters

        properties = input_schema.get("properties", {})
        required_fields = input_schema.get("required", [])

        for param_name, param_config in properties.items():
            parameters.append({
                "name": param_name,
                "type": param_config.get("type", "string"),
                "required": param_name in required_fields,
                "description": param_config.get("description", "")
            })

        return parameters

    def _load_local_skill_module(self, skill_dir: str, skill_id: str):
        """加载本地技能模块

        Args:
            skill_dir: 技能目录路径
            skill_id: 技能ID
        """
        # 检查缓存
        if self.cache:
            cached_module = self.cache.get_module(skill_id)
            if cached_module:
                self.logger.debug(f"使用缓存的技能模块：{skill_id}")
                self.loaded_modules[skill_id] = cached_module
                return
        
        main_py_path = os.path.join(skill_dir, "main.py")

        if not os.path.exists(main_py_path):
            self.logger.debug(f"本地技能无main.py文件: {skill_id}")
            return

        try:
            module_name = f"skill_{skill_id.replace('.', '_')}"

            spec = importlib.util.spec_from_file_location(module_name, main_py_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                self.loaded_modules[skill_id] = module

                # 添加到缓存
                if self.cache:
                    self.cache.set_module(skill_id, module, main_py_path)

                if hasattr(module, "init"):
                    module.init()
                    self.logger.debug(f"本地技能初始化函数已调用: {skill_id}")

                self.logger.debug(f"本地技能模块加载成功: {skill_id}")

        except Exception as e:
            self.logger.error(f"加载本地技能模块失败 {skill_id}: {e}")

    def execute_local_skill(self, skill_id: str, parameters: Dict[str, Any]) -> str:
        """执行本地技能（统一处理所有MCP格式技能）

        Args:
            skill_id: 技能ID
            parameters: 技能参数

        Returns:
            执行结果
        """
        # 检查技能模块是否已加载
        if skill_id not in self.loaded_modules:
            return f"错误: 技能模块未加载: {skill_id}"

        # 转换路径参数为绝对路径（基于当前工作目录）
        if self.sandbox and parameters:
            parameters = self._normalize_paths(parameters, skill_id)

        module = self.loaded_modules[skill_id]

        try:
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
                    workspace_root = self.sandbox.get_workspace_root()
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
