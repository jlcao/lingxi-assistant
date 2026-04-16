#!/usr/bin/env python3
"""Phase 3 单元测试 - 分级安全沙盒"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import unittest
import tempfile
from pathlib import Path

from lingxi.skills import (
    SkillResponse,
    ExecutionContext,
    TrustLevel,
    SecurityInterceptor,
    RiskLevel,
    DisclosureStage,
    L1Sandbox,
    L2Sandbox,
    SandboxManager
)


def sample_func(params):
    return f"result: {params.get('value', 'default')}"


def sample_error_func(params):
    raise ValueError("test error")


class TestSecurityInterceptor(unittest.TestCase):
    """测试安全拦截器"""

    def setUp(self):
        self.interceptor = SecurityInterceptor({
            "high_risk_skills": ["danger_skill"]
        })
        self.interceptor.clear_audit_logs()
        self.context = ExecutionContext()

    def test_disclose_stage1(self):
        """测试 Stage 1 披露"""
        info = self.interceptor.disclose_stage1("test_skill", {
            "name": "Test Skill",
            "description": "A test skill"
        })
        self.assertEqual(info.stage, DisclosureStage.STAGE1)
        self.assertEqual(info.skill_id, "test_skill")
        self.assertEqual(info.skill_name, "Test Skill")

    def test_disclose_stage2(self):
        """测试 Stage 2 披露"""
        info = self.interceptor.disclose_stage2("test_skill", {"param": "value"})
        self.assertEqual(info.stage, DisclosureStage.STAGE2)
        self.assertEqual(info.parameters, {"param": "value"})

    def test_disclose_stage3(self):
        """测试 Stage 3 披露"""
        info = self.interceptor.disclose_stage3("test_skill", {})
        self.assertEqual(info.stage, DisclosureStage.STAGE3)

    def test_require_confirm_low_risk(self):
        """测试低风险不需要确认"""
        result = self.interceptor.require_confirm("safe_skill", {})
        self.assertFalse(result)

    def test_require_confirm_high_risk(self):
        """测试高风险需要确认"""
        result = self.interceptor.require_confirm("danger_skill", {})
        self.assertTrue(result)

    def test_audit_success(self):
        """测试成功审计"""
        self.interceptor.audit_success(
            self.context,
            "execute",
            {"param": "value"},
            "result"
        )
        logs = self.interceptor.get_audit_logs()
        self.assertEqual(len(logs), 1)
        self.assertTrue(logs[0]["success"])

    def test_audit_failure(self):
        """测试失败审计"""
        self.interceptor.audit_failure(
            self.context,
            "execute",
            {"param": "value"},
            "error"
        )
        logs = self.interceptor.get_audit_logs()
        self.assertEqual(len(logs), 1)
        self.assertFalse(logs[0]["success"])

    def test_get_audit_logs_by_skill(self):
        """测试按技能获取审计日志"""
        ctx1 = self.context.with_skill("skill_a")
        ctx2 = self.context.with_skill("skill_b")

        self.interceptor.audit_success(ctx1, "execute", {}, "ok")
        self.interceptor.audit_success(ctx2, "execute", {}, "ok")

        logs_a = self.interceptor.get_audit_logs(skill_id="skill_a")
        self.assertEqual(len(logs_a), 1)
        self.assertEqual(logs_a[0]["skill_id"], "skill_a")

    def test_clear_audit_logs(self):
        """测试清空审计日志"""
        self.interceptor.audit_success(self.context, "execute", {}, "ok")
        self.interceptor.clear_audit_logs()
        logs = self.interceptor.get_audit_logs()
        self.assertEqual(len(logs), 0)


class TestL1Sandbox(unittest.TestCase):
    """测试 L1 沙盒"""

    def setUp(self):
        self.sandbox = L1Sandbox()
        self.context = ExecutionContext()

    def tearDown(self):
        self.sandbox.shutdown(wait=False)

    def test_run_success(self):
        """测试成功执行"""
        resp = self.sandbox.run(
            sample_func,
            {"value": "test"},
            skill_id="test_skill",
            context=self.context
        )
        self.assertTrue(resp.success)
        self.assertEqual(resp.data, "result: test")

    def test_run_error(self):
        """测试错误执行"""
        resp = self.sandbox.run(
            sample_error_func,
            {},
            skill_id="error_skill",
            context=self.context
        )
        self.assertFalse(resp.success)

    def test_run_returns_skill_response(self):
        """测试返回 SkillResponse"""
        def func_returns_response(params):
            return SkillResponse.success(data="direct_response")

        resp = self.sandbox.run(
            func_returns_response,
            {},
            skill_id="test_skill",
            context=self.context
        )
        self.assertTrue(resp.success)
        self.assertEqual(resp.data, "direct_response")


class TestSandboxManager(unittest.TestCase):
    """测试沙盒管理器"""

    def setUp(self):
        self.manager = SandboxManager()
        self.context = ExecutionContext()

    def tearDown(self):
        self.manager.shutdown(wait=False)

    def test_run_l1(self):
        """测试 L1 模式运行"""
        resp = self.manager.run(
            sample_func,
            {"value": "l1"},
            skill_id="test_skill",
            context=self.context,
            trust_level=TrustLevel.L1
        )
        self.assertTrue(resp.success)
        self.assertEqual(resp.data, "result: l1")


if __name__ == "__main__":
    unittest.main()

