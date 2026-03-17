import logging
from typing import Dict, List, Optional, Any
from lingxi.skills.registry import SkillRegistry
from lingxi.skills.registry_memory import SkillRegistry as SkillRegistryMemory
from lingxi.skills.skill_loader import SkillLoader
from lingxi.skills.skill_cache import SkillCache


class BuiltinSkills:
    """技能管理类，统一管理所有 MCP 格式技能（单例模式）"""
    
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
        
        """初始化技能管理

        Args:
            config: 系统配置
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

        # 根据配置选择注册表类型
        skills_config = config.get("skills", {})
        use_memory = skills_config.get("use_memory_registry", True)

        if use_memory:
            self.logger.debug("使用纯内存注册表")
            self.registry = SkillRegistryMemory(config)
        else:
            self.logger.debug("使用SQLite数据库注册表")
            self.registry = SkillRegistry(config)


        # 初始化缓存
        cache_ttl = skills_config.get("cache_ttl", 300)
        self.cache = SkillCache(ttl=cache_ttl)
        self.logger.debug(f"技能缓存已初始化，TTL={cache_ttl}秒")

        # 初始化技能加载器
        self.skill_loader = SkillLoader(config, self.registry, self.cache)

        # 扫描并自动注册所有MCP格式技能
        self.skill_loader.scan_and_register(self.registry)

        self.logger.debug("初始化技能管理完成")
        self._initialized = True

    def execute_skill(self, skill_name: str, parameters: Dict[str, Any]) -> str:
        """执行技能

        Args:
            skill_name: 技能名称
            parameters: 技能参数

        Returns:
            技能执行结果
        """
        # 记录参数长度，避免日志过长
        param_summary = {}
        for key, value in parameters.items():
            if isinstance(value, str):
                param_summary[key] = f"<{len(value)} chars>"
            else:
                param_summary[key] = value
        self.logger.debug(f"执行技能: {skill_name} - {param_summary}")

        try:
            # 统一通过SkillLoader执行所有技能
            if skill_name in self.skill_loader.loaded_modules:
                return self.skill_loader.execute_local_skill(skill_name, parameters)
            else:
                return f"未知技能: {skill_name}"

        except Exception as e:
            self.logger.error(f"执行技能失败: {e}")
            return f"技能执行错误: {str(e)}"

    def list_skills(self) -> List[Dict[str, Any]]:
        """列出所有已注册的技能

        Returns:
            技能列表
        """
        return self.registry.list_skills()

    def get_skill_info(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """获取技能信息

        Args:
            skill_name: 技能名称

        Returns:
            技能信息字典
        """
        return self.registry.get_skill(skill_name)
