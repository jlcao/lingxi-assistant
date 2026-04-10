#!/usr/bin/env python3
"""技能系统统一入口，管理所有技能相关组件"""

import logging
from typing import Dict, List, Optional, Any
from lingxi.management import workspace
from lingxi.skills.registry_memory import SkillRegistry
from lingxi.skills.skill_loader import SkillLoader
from lingxi.skills.skill_cache import SkillCache
from lingxi.core.utils.security import SecuritySandbox, SecurityError
from lingxi.core.confirmation import DangerousSkillChecker, RiskLevel


class SkillSystem:
    """技能系统统一入口（单例模式）"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls, config: Dict[str, Any]):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config: Dict[str, Any]):
        # 防止重复初始化
        if self._initialized:
            return
        
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.logger.info("初始化技能系统...")
        
        # 1. 初始化注册表
        self.logger.debug("使用纯内存注册表")
        self.registry = SkillRegistry(config)
        
        # 2. 初始化安全沙箱
        security_config = config.get("security", {})
        workspace_config=config.get('workspace',{})

        self.sandbox = SecuritySandbox(
            workspace_root=workspace_config.get("last_workspace",'./workspace'),  # 不设置默认值，等待实际工作目录
            max_file_size=security_config.get("max_file_size", 10 * 1024 * 1024),
            allowed_commands=security_config.get("allowed_commands"),
            safety_mode=security_config.get("safety_mode", True)
        )
        self.logger.debug("安全沙箱已初始化")
        
        # 3. 初始化缓存
        skills_config = config.get("skills", {})
        cache_ttl = skills_config.get("cache_ttl", 300)
        self.cache = SkillCache(ttl=cache_ttl)
        self.logger.debug(f"技能缓存已初始化，TTL={cache_ttl}秒")
        
        # 4. 初始化技能加载器（使用统一的注册表、缓存和沙箱）
        self.loader = SkillLoader(config, self.registry, self.cache, self.sandbox)
        
        # 5. 扫描并注册技能
        self._load_skills()
        
        self._initialized = True
        self.logger.info(f"技能系统初始化完成，已注册 {len(self.registry.list_skills())} 个技能")
    
    def _load_skills(self):
        """加载并注册所有技能"""
        self.logger.info("开始扫描和注册技能...")
        count = self.loader.scan_and_register(self.registry)
        self.logger.info(f"技能加载完成，成功注册 {count} 个技能")
    
    def update_workspace(self, workspace_path: str):
        """更新工作目录（用于动态切换工作区）
        
        Args:
            workspace_path: 新的工作目录路径
        """
        self.logger.info(f"更新技能系统的工作目录：{workspace_path}")
        
        # 更新 SecuritySandbox 的工作目录
        if self.sandbox:
            from pathlib import Path
            self.sandbox.update_workspace(Path(workspace_path))
        
        self.logger.debug(f"SecuritySandbox 工作目录已更新为：{self.sandbox.get_workspace_root()}")
        
        # 更新 SkillLoader 的用户技能目录
        if self.loader:
            self.loader.user_skills_dir = str(Path(workspace_path) / ".lingxi" / "skills")
            self.logger.debug(f"SkillLoader 用户技能目录已更新为：{self.loader.user_skills_dir}")
        
        # 清除旧技能缓存并重新加载新工作目录的技能
        self._reload_skills(reload_builtin=False)
    
    def _reload_skills(self, reload_builtin: bool = False):
        """重新加载技能（用于工作目录切换后）
        
        Args:
            reload_builtin: 是否重新加载内置技能（默认只重新加载工作目录技能）
        """
        self.logger.info("重新加载技能...")
        
        # 清除技能缓存
        if self.cache:
            self.cache.invalidate_all()
            self.logger.debug("技能缓存已清空")
        
        # 清除已加载的技能模块
        if self.loader:
            self.loader.loaded_modules.clear()
            self.logger.debug("已加载的技能模块已清空")
        
        # 重新扫描和注册技能
        if reload_builtin:
            # 重新加载所有技能（包括内置和工作目录技能）
            count = self.loader.scan_and_register(self.registry)
            self.logger.info(f"技能重新加载完成，成功注册 {count} 个技能")
        else:
            # 只重新加载工作目录下的技能（不重新加载内置技能）
            # 临时修改 loader 的扫描目录为只包含工作目录技能
            original_builtin = self.loader.builtin_skills_dir
            self.loader.builtin_skills_dir = None  # 禁用内置技能目录扫描
            
            count = self.loader.scan_and_register(self.registry)
            self.loader.builtin_skills_dir = original_builtin  # 恢复内置技能目录
            
            self.logger.info(f"工作目录技能重新加载完成，成功注册 {count} 个技能")
    
    def execute_skill(self, skill_name: str, parameters: Dict[str, Any] = None, require_confirmation: bool = False) -> Dict[str, Any]:
        """执行技能（统一入口，带安全检查）"""
        if parameters is None:
            parameters = {}
        
        self.logger.debug(f"执行技能：{skill_name}")
        
        # 1. 检查技能是否存在
        skill_info = self.registry.get_skill(skill_name)
        if not skill_info:
            error_msg = f"技能不存在: {skill_name}"
            self.logger.warning(error_msg)
            return {"success": False, "error": error_msg, "result_description": f"执行技能 {skill_name} 失败，技能不存在"}
        
        # 2. 检查技能是否启用
        if not skill_info.get("enabled", True):
            error_msg = f"技能未启用: {skill_name}"
            self.logger.warning(error_msg)
            return {"success": False, "error": error_msg, "result_description": f"执行技能 {skill_name} 失败，技能未启用"}
        
        # 3. 检查操作风险级别
        skill_risk = DangerousSkillChecker.check_skill_risk(skill_name)
        command_risk = RiskLevel.LOW
        
        # 检查命令风险（如果是 execute 操作）
        if skill_name == "execute" and isinstance(parameters.get("command"), str):
            command_risk = DangerousSkillChecker.check_command_risk(parameters["command"])
        
        # 4. 判断是否需要确认
        needs_confirmation = (
            skill_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL] or
            command_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        )
        
        if needs_confirmation and not require_confirmation:
            error_msg = (
                f"高危操作需要用户确认：{skill_name}\n"
                f"风险级别：{DangerousSkillChecker.get_risk_description(skill_risk)}\n"
                f"参数：{parameters}"
            )
            self.logger.warning(error_msg)
            raise SecurityError(error_msg, "DANGEROUS_OPERATION")
      
        # 5. 执行技能
        try:
            result = self.loader.execute_local_skill(skill_name, parameters)
            self.logger.debug(f"技能执行成功：{skill_name}")
            if result is not None and "错误" in result:
                error_msg = f"技能执行返回错误：{skill_name} - {result}"
                self.logger.warning(error_msg)
                return {"success": False, "result": error_msg, "result_description": f"执行技能 {skill_name} 失败"}
            elif result is not None:    
                return {"success": True, "result": result, "result_description": f"执行技能 {skill_name} 成功"}
            else:
                return {"success": True, "result": result, "result_description": f"执行技能 {skill_name} 成功，无返回结果"}
        except Exception as e:
            error_msg = f"技能执行失败：{skill_name} - {str(e)}"
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg, "result_description": f"执行技能 {skill_name} 失败"}
    
    def get_skill_info(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """获取技能信息"""
        return self.registry.get_skill(skill_name)
    
    def list_skills(self, enabled_only: bool = True) -> List[Dict[str, Any]]:
        """列出所有技能"""
        return self.registry.list_skills(enabled_only=enabled_only)
    
    def reload_skill(self, skill_name: str) -> bool:
        """重新加载技能（用于热重载）"""
        self.logger.info(f"重新加载技能：{skill_name}")
        self.cache.invalidate(skill_name)
        
        # 重新扫描注册
        skill_info = self.registry.get_skill(skill_name)
        if skill_info:
            self.registry.unregister_skill(skill_name)
        
        self._load_skills()
        return True
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return self.cache.get_stats()
    
    def clear_cache(self):
        """清空缓存"""
        self.cache.invalidate_all()
