#!/usr/bin/env python3
"""Phase 1 单元测试 - 核心标准类"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import unittest
from lingxi.skills import (
    SkillResponse,
    ResponseCode,
    ExecutionContext,
    TrustLevel,
    BaseSkill,
    SimpleSkill,
    wrap_execute_function,
    get_skill_id,
    get_version,
    get_description,
    get_author,
    get_trust_level,
    is_isolated_env,
    get_permissions,
    get_risks
)


class TestSkillResponse(unittest.TestCase):
    """测试 SkillResponse 类"""

    def test_success_response(self):
        """测试成功响应"""
        resp = SkillResponse.success(
            data={"result": "test"},
            message="执行成功",
            skill_id="test_skill",
            version="1.0.0",
            trace_id="trace_123",
            cost_ms=100.5
        )
        self.assertTrue(resp.success)
        self.assertEqual(resp.code, ResponseCode.SUCCESS)
        self.assertEqual(resp.data, {"result": "test"})
        self.assertEqual(resp.message, "执行成功")
        self.assertEqual(resp.meta["skill_id"], "test_skill")
        self.assertEqual(resp.meta["version"], "1.0.0")
        self.assertEqual(resp.meta["trace_id"], "trace_123")
        self.assertEqual(resp.meta["cost_ms"], 100.5)

    def test_error_response(self):
        """测试错误响应"""
        resp = SkillResponse.error(
            message="执行失败",
            code=ResponseCode.INTERNAL_ERROR,
            skill_id="test_skill",
            trace_id="trace_456"
        )
        self.assertFalse(resp.success)
        self.assertEqual(resp.code, ResponseCode.INTERNAL_ERROR)
        self.assertEqual(resp.message, "执行失败")
        self.assertEqual(resp.meta["skill_id"], "test_skill")
        self.assertEqual(resp.meta["trace_id"], "trace_456")

    def test_forbidden_response(self):
        """测试禁止响应"""
        resp = SkillResponse.forbidden(
            message="安全检查失败",
            skill_id="test_skill",
            trace_id="trace_789"
        )
        self.assertFalse(resp.success)
        self.assertEqual(resp.code, ResponseCode.FORBIDDEN)

    def test_bad_request_response(self):
        """测试参数错误响应"""
        resp = SkillResponse.bad_request(
            message="参数错误",
            skill_id="test_skill",
            trace_id="trace_012"
        )
        self.assertFalse(resp.success)
        self.assertEqual(resp.code, ResponseCode.BAD_REQUEST)

    def test_to_dict_and_from_dict(self):
        """测试字典转换"""
        resp1 = SkillResponse.success(data={"key": "value"})
        resp_dict = resp1.to_dict()
        resp2 = SkillResponse.from_dict(resp_dict)
        self.assertEqual(resp1.success, resp2.success)
        self.assertEqual(resp1.code, resp2.code)
        self.assertEqual(resp1.data, resp2.data)


class TestExecutionContext(unittest.TestCase):
    """测试 ExecutionContext 类"""

    def test_default_init(self):
        """测试默认初始化"""
        ctx = ExecutionContext()
        self.assertIsNotNone(ctx.trace_id)
        self.assertEqual(ctx.trust_level, TrustLevel.L1)
        self.assertEqual(ctx.permissions, [])
        self.assertIsNotNone(ctx.timestamp)

    def test_with_skill(self):
        """测试设置技能信息"""
        ctx = ExecutionContext()
        new_ctx = ctx.with_skill("test_skill", TrustLevel.L2)
        self.assertEqual(new_ctx.skill_id, "test_skill")
        self.assertEqual(new_ctx.trust_level, TrustLevel.L2)

    def test_with_workspace(self):
        """测试设置工作目录"""
        ctx = ExecutionContext()
        new_ctx = ctx.with_workspace("/tmp/workspace")
        self.assertEqual(new_ctx.workspace, "/tmp/workspace")

    def test_permissions(self):
        """测试权限管理"""
        ctx = ExecutionContext()
        ctx = ctx.add_permission("read_file")
        self.assertTrue(ctx.has_permission("read_file"))
        self.assertFalse(ctx.has_permission("write_file"))

    def test_extra_fields(self):
        """测试扩展字段"""
        ctx = ExecutionContext()
        ctx = ctx.set_extra("custom_key", "custom_value")
        self.assertEqual(ctx.get_extra("custom_key"), "custom_value")
        self.assertIsNone(ctx.get_extra("nonexistent"))

    def test_to_dict_and_from_dict(self):
        """测试字典转换"""
        ctx1 = ExecutionContext(user_id="user123")
        ctx_dict = ctx1.to_dict()
        ctx2 = ExecutionContext.from_dict(ctx_dict)
        self.assertEqual(ctx1.user_id, ctx2.user_id)
        self.assertEqual(ctx1.trust_level, ctx2.trust_level)


class TestManifestUtils(unittest.TestCase):
    """测试元数据工具函数"""

    def test_manifest_utils(self):
        """测试所有元数据工具函数"""
        manifest = {
            "skill_id": "test_skill",
            "name": "Test Skill",
            "version": "2.0.0",
            "description": "A test skill",
            "author": "Test Author",
            "trust_level": "L2",
            "isolated_env": True,
            "permissions": ["read", "write"],
            "risks": ["high_risk"]
        }
        self.assertEqual(get_skill_id(manifest), "test_skill")
        self.assertEqual(get_version(manifest), "2.0.0")
        self.assertEqual(get_description(manifest), "A test skill")
        self.assertEqual(get_author(manifest), "Test Author")
        self.assertEqual(get_trust_level(manifest), "L2")
        self.assertTrue(is_isolated_env(manifest))
        self.assertEqual(get_permissions(manifest), ["read", "write"])
        self.assertEqual(get_risks(manifest), ["high_risk"])


class TestSimpleSkill(unittest.TestCase):
    """测试 SimpleSkill 类"""

    def test_wrap_execute_function_string_success(self):
        """测试包装返回字符串的成功函数"""
        def execute_func(params):
            return "执行成功"
        
        skill = wrap_execute_function(execute_func)
        result = skill.sync_execute({})
        self.assertTrue(result.success)
        self.assertEqual(result.data, "执行成功")

    def test_wrap_execute_function_string_error(self):
        """测试包装返回字符串的错误函数"""
        def execute_func(params):
            return "错误: 执行失败"
        
        skill = wrap_execute_function(execute_func)
        result = skill.sync_execute({})
        self.assertFalse(result.success)
        self.assertEqual(result.message, "错误: 执行失败")

    def test_wrap_execute_function_dict(self):
        """测试包装返回字典的函数"""
        def execute_func(params):
            return {"key": "value"}
        
        skill = wrap_execute_function(execute_func)
        result = skill.sync_execute({})
        self.assertTrue(result.success)
        self.assertEqual(result.data, {"key": "value"})

    def test_wrap_execute_function_skill_response(self):
        """测试包装返回 SkillResponse 的函数"""
        def execute_func(params):
            return SkillResponse.success(data="test")
        
        skill = wrap_execute_function(execute_func)
        result = skill.sync_execute({})
        self.assertTrue(result.success)
        self.assertEqual(result.data, "test")

    def test_with_manifest(self):
        """测试带 manifest 的包装"""
        manifest = {"name": "test_skill"}
        
        def execute_func(params):
            return "ok"
        
        skill = wrap_execute_function(execute_func, manifest=manifest)
        self.assertEqual(skill.manifest["name"], "test_skill")


class TestSkillImpl(BaseSkill):
    """测试用的具体技能实现"""
    async def execute(self, params: dict):
        return SkillResponse.success(data="test")


class TestBaseSkill(unittest.TestCase):
    """测试 BaseSkill 类"""

    def test_manifest_access(self):
        """测试清单访问"""
        manifest = {
            "skill_id": "test_skill",
            "name": "Test Skill",
            "version": "2.0.0",
            "description": "A test skill",
            "author": "Test Author",
            "trust_level": "L2",
            "isolated_env": True,
            "permissions": ["read", "write"],
            "risks": ["high_risk"]
        }
        skill = TestSkillImpl(manifest=manifest)
        self.assertEqual(skill.manifest.get("skill_id"), "test_skill")
        self.assertEqual(skill.manifest.get("version"), "2.0.0")

    def test_context_access(self):
        """测试上下文访问"""
        ctx = ExecutionContext(user_id="test_user")
        skill = TestSkillImpl(context=ctx)
        self.assertEqual(skill.context.user_id, "test_user")


if __name__ == "__main__":
    unittest.main()

