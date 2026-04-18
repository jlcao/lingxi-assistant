#!/usr/bin/env python3
"""技能系统统一入口，管理所有技能相关组件"""

import logging
import time
from typing import Dict, List, Optional, Any
from concurrent.futures import Future
from lingxi.management import workspace
from lingxi.skills.registry_memory import SkillRegistry
from lingxi.skills.skill_loader import SkillLoader
from lingxi.skills.skill_cache import SkillCache
from lingxi.skills.executor_scheduler import ExecutorScheduler, ExecutorType, SkillPriority
from lingxi.skills.execution_context import ExecutionContext, TrustLevel
from lingxi.skills.skill_response import ToolResponse, ResponseCode
from lingxi.core.utils.security import SecuritySandbox, SecurityError
from lingxi.core.confirmation import DangerousSkillChecker, RiskLevel
from lingxi.skills.security_interceptor import SecurityInterceptor
from lingxi.skills.sandbox import SandboxManager


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
        
        # 3. 初始化沙盒管理器
        self.sandbox_manager = SandboxManager(config)
        self.logger.debug("沙盒管理器已初始化")
        
        # 4. 初始化安全拦截器
        self.security_interceptor = SecurityInterceptor(config)
        self.logger.debug("安全拦截器已初始化")
        
        # 5. 初始化执行调度器
        self.executor = ExecutorScheduler(config)
        self.logger.debug("执行调度器已初始化")
        
        # 6. 初始化缓存
        skills_config = config.get("skills", {})
        cache_ttl = skills_config.get("cache_ttl", 300)
        self.cache = SkillCache(ttl=cache_ttl)
        self.logger.debug(f"技能缓存已初始化，TTL={cache_ttl}秒")
        
        # 7. 初始化技能加载器（使用统一的注册表、缓存和沙箱）
        self.loader = SkillLoader(config, self.registry, self.cache, self.sandbox)
        
        # 8. 扫描并注册技能
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
        if self.loader and self.cache:
            self.cache.clear_modules()
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
    
    def execute_skill(self, skill_id: str, params: Dict[str, Any] = None) -> ToolResponse:
        """执行技能（统一入口，带安全检查）
        
        Args:
            skill_id: 技能ID
            params: 技能参数
            
        Returns:
            SkillResponse 实例
        """
        if params is None:
            params = {}
        
        self.logger.debug(f"执行技能：{skill_id}")
        
        # 1. 检查技能是否存在
        skill_info = self.registry.get_skill(skill_id)
        if not skill_info:
            error_msg = f"技能不存在: {skill_id}"
            self.logger.warning(error_msg)
            return ToolResponse.error(
                message=error_msg,
                code=ResponseCode.NOT_FOUND,
                skill_id=skill_id
            )
        
        # 2. 检查技能是否启用
        if not skill_info.get("enabled", True):
            error_msg = f"技能未启用: {skill_id}"
            self.logger.warning(error_msg)
            return ToolResponse.error(
                message=error_msg,
                code=ResponseCode.FORBIDDEN,
                skill_id=skill_id
            )
        
        # 3. 创建执行上下文
        context = ExecutionContext(
            skill_id=skill_id,
            trust_level=skill_info.get("trust_level", TrustLevel.L1),
            workspace=str(self.sandbox.get_workspace_root())
        )
        
        # 4. 渐进式披露
        stage1 = self.security_interceptor.disclose_stage1(skill_id, skill_info)
        stage2 = self.security_interceptor.disclose_stage2(skill_id, params)
        
        # 5. 检查风险级别
        skill_risk = DangerousSkillChecker.check_skill_risk(skill_id)
        command_risk = RiskLevel.LOW
        
        # 检查命令风险（如果是 execute 操作）
        if skill_id == "execute" and isinstance(params.get("command"), str):
            command_risk = DangerousSkillChecker.check_command_risk(params["command"])
        
        # 6. 高风险操作需要额外披露和确认
        needs_confirmation = (
            skill_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL] or
            command_risk in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        )
        
        if needs_confirmation:
            stage3 = self.security_interceptor.disclose_stage3(skill_id, params)
            if not self.security_interceptor.require_confirm():
                error_msg = "用户拒绝执行高风险操作"
                self.logger.warning(error_msg)
                return ToolResponse.forbidden(
                    message=error_msg,
                    skill_id=skill_id,
                    trace_id=context.trace_id
                )
        
        # 7. 确定执行方式（根据信任等级）
        trust_level = skill_info.get("trust_level", TrustLevel.L1)
        executor_type = ExecutorType.THREAD
        priority = SkillPriority.HIGH
        
        if trust_level == TrustLevel.L2 or skill_info.get("isolated_env", False):
            executor_type = ExecutorType.PROCESS
            priority = SkillPriority.LOW
        
        # 8. 执行技能
        start_time = time.time()
        
        def execute_task():
            # 根据信任等级选择执行方式
            trust_level = skill_info.get("trust_level", TrustLevel.L2)
            
            if trust_level == TrustLevel.L2:
                # 使用 L2 沙盒执行
                skill_dir = self.loader._get_skill_dir(skill_id)
                if skill_dir:
                    response = self.sandbox_manager.run(
                        skill_dir,
                        parameters=params,
                        skill_id=skill_id,
                        context=context,
                        trust_level=trust_level
                    )
                    return response
            try:
                # L1 信任等级或技能目录不存在时，使用原有方式执行
                result = self.loader.execute_local_skill(skill_id, params)
            except Exception as e:
                error_msg = f"技能执行异常: {skill_id} : {str(e)}"
                self.logger.error(error_msg)
                return ToolResponse.error(
                    message=error_msg,
                    skill_id=skill_id,
                    trace_id=context.trace_id
                )
            # 处理返回结果
            if isinstance(result, str) and "错误" in result:
                return ToolResponse.error(
                    message=result,
                    skill_id=skill_id,
                    trace_id=context.trace_id
                )
            return ToolResponse.success(
                data=result,
                skill_id=skill_id,
                trace_id=context.trace_id
            )
        
        try:
            # 提交任务到执行调度器
            future = self.executor.submit(
                execute_task,
                skill_id=skill_id,
                context=context,
                priority=priority,
                executor_type=executor_type
            )
            
            # 等待执行结果
            response = future.result()
            
            # 计算耗时
            cost_ms = (time.time() - start_time) * 1000
            response.meta["cost_ms"] = cost_ms
            
            # 写入审计日志
            self.security_interceptor.audit_log(
                skill_id=skill_id,
                params=params,
                response=response,
                context=context
            )
            
            self.logger.debug(f"技能执行成功：{skill_id}")
            return response
            
        except Exception as e:
            error_msg = f"技能执行失败：{skill_id} - {str(e)}"
            self.logger.error(error_msg)
            
            # 写入审计日志
            error_response = ToolResponse.error(
                message=error_msg,
                skill_id=skill_id,
                trace_id=context.trace_id
            )
            
            self.security_interceptor.audit_log(
                skill_id=skill_id,
                params=params,
                response=error_response,
                context=context
            )
            
            return error_response
    
    def execute_skill_async(self, skill_id: str, params: Dict[str, Any] = None) -> Future[ToolResponse]:
        """异步执行技能
        
        Args:
            skill_id: 技能ID
            params: 技能参数
            
        Returns:
            Future[SkillResponse] 实例
        """
        if params is None:
            params = {}
        
        # 1. 检查技能是否存在
        skill_info = self.registry.get_skill(skill_id)
        if not skill_info:
            error_msg = f"技能不存在: {skill_id}"
            self.logger.warning(error_msg)
            
            # 返回已完成的 Future
            from concurrent.futures import Future
            future = Future()
            future.set_result(ToolResponse.error(
                message=error_msg,
                code=ResponseCode.NOT_FOUND,
                skill_id=skill_id
            ))
            return future
        
        # 2. 创建执行上下文
        context = ExecutionContext(
            skill_id=skill_id,
            trust_level=skill_info.get("trust_level", TrustLevel.L1),
            workspace=str(self.sandbox.get_workspace_root())
        )
        
        # 3. 确定执行方式
        trust_level = skill_info.get("trust_level", TrustLevel.L1)
        executor_type = ExecutorType.THREAD
        priority = SkillPriority.HIGH
        
        if trust_level == TrustLevel.L2 or skill_info.get("isolated_env", False):
            executor_type = ExecutorType.PROCESS
            priority = SkillPriority.LOW
        
        # 4. 执行技能
        def execute_task():
            # 根据信任等级选择执行方式
            trust_level = skill_info.get("trust_level", TrustLevel.L1)
            
            if trust_level == TrustLevel.L2:
                # 使用 L2 沙盒执行
                skill_dir = self.loader._get_skill_dir(skill_id)
                if skill_dir:
                    response = self.sandbox_manager.run(
                        skill_dir,
                        parameters=params,
                        skill_id=skill_id,
                        context=context,
                        trust_level=trust_level
                    )
                    return response
            
            # L1 信任等级或技能目录不存在时，使用原有方式执行
            result = self.loader.execute_local_skill(skill_id, params)
            
            if isinstance(result, str) and "错误" in result:
                return ToolResponse.error(
                    message=result,
                    skill_id=skill_id,
                    trace_id=context.trace_id
                )
            return ToolResponse.success(
                data=result,
                skill_id=skill_id,
                trace_id=context.trace_id
            )
        
        # 提交任务到执行调度器
        return self.executor.submit(
            execute_task,
            skill_id=skill_id,
            context=context,
            priority=priority,
            executor_type=executor_type
        )
    
    def get_skill_info(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """获取技能信息"""
        return self.registry.get_skill(skill_id)
    
    def list_skills(self, enabled_only: bool = True) -> List[Dict[str, Any]]:
        """列出所有技能"""
        return self.registry.list_skills(enabled_only=enabled_only)
    
    def reload_skill(self, skill_id: str) -> bool:
        """重新加载技能（用于热重载）"""
        self.logger.info(f"重新加载技能：{skill_id}")
        
        # 1. 清理缓存
        self.cache.invalidate(skill_id)
        
        # 2. 从 sys.modules 移除模块
        self.loader.unload_module(skill_id)
        
        # 3. 强制 GC
        import gc
        gc.collect()
        
        # 4. 重新扫描注册
        skill_info = self.registry.get_skill(skill_id)
        if skill_info:
            self.registry.unregister_skill(skill_id)
        
        self._load_skills()
        return True
    
    def reload_all(self):
        """重新加载所有技能"""
        self.logger.info("重新加载所有技能")
        
        # 1. 清理所有缓存
        self.cache.invalidate_all()
        
        # 2. 卸载所有模块
        self.loader.unload_all()
        
        # 3. 强制 GC
        import gc
        gc.collect()
        
        # 4. 重新扫描注册
        self._load_skills()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return self.cache.get_stats()
    
    def get_execution_metrics(self, skill_id: Optional[str] = None) -> Dict[str, Any]:
        """获取执行指标"""
        return self.executor.get_metrics(skill_id)
    
    def clear_cache(self):
        """清空缓存"""
        self.cache.invalidate_all()
    
    def shutdown(self):
        """关闭技能系统"""
        self.logger.info("关闭技能系统...")
        
        # 关闭执行调度器
        if hasattr(self, 'executor'):
            self.executor.shutdown()
        
        # 清空缓存
        if hasattr(self, 'cache'):
            self.cache.invalidate_all()
        
        # 卸载所有模块
        if hasattr(self, 'loader'):
            self.loader.unload_all()
        
        self.logger.info("技能系统已关闭")
