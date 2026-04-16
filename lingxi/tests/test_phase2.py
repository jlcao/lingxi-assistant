#!/usr/bin/env python3
"""Phase 2 单元测试 - 执行调度器"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import unittest
from concurrent.futures import TimeoutError
from lingxi.skills import (
    SkillResponse,
    ExecutionContext,
    ExecutorScheduler,
    ExecutorType,
    SkillPriority,
    ExceptionTranslator
)


def sample_success_func(params):
    return f"success: {params.get('value', 'default')}"


def sample_error_func(params):
    raise ValueError("test error")


def sample_timeout_func(params):
    time.sleep(2)
    return "timeout"


class TestExceptionTranslator(unittest.TestCase):
    """测试异常转译器"""

    def test_translate_generic_error(self):
        """测试通用异常转译"""
        try:
            raise ValueError("test error")
        except Exception as e:
            msg = ExceptionTranslator.translate(e, "test_skill")
            self.assertIn("技能执行失败", msg)

    def test_translate_timeout_error(self):
        """测试超时异常转译"""
        try:
            raise TimeoutError()
        except Exception as e:
            msg = ExceptionTranslator.translate(e)
            self.assertEqual(msg, "技能执行超时，请稍后重试")

    def test_translate_io_error(self):
        """测试 IO 异常转译"""
        try:
            raise IOError("file not found")
        except Exception as e:
            msg = ExceptionTranslator.translate(e)
            self.assertIn("文件操作失败", msg)

    def test_to_response(self):
        """测试转译为 SkillResponse"""
        try:
            raise ValueError("test error")
        except Exception as e:
            resp = ExceptionTranslator.to_response(e, "test_skill", "trace_123")
            self.assertFalse(resp.success)
            self.assertEqual(resp.meta["skill_id"], "test_skill")
            self.assertEqual(resp.meta["trace_id"], "trace_123")


class TestExecutorScheduler(unittest.TestCase):
    """测试执行调度器"""

    def setUp(self):
        """测试前初始化"""
        self.scheduler = ExecutorScheduler()
        self.context = ExecutionContext()

    def tearDown(self):
        """测试后清理"""
        self.scheduler.shutdown(wait=False)

    def test_submit_thread_pool_high(self):
        """测试高优线程池提交"""
        future = self.scheduler.submit(
            sample_success_func,
            {"value": "test"},
            skill_id="test_skill",
            context=self.context,
            priority=SkillPriority.HIGH,
            executor_type=ExecutorType.THREAD
        )
        result = future.result()
        self.assertTrue(result.success)
        self.assertEqual(result.data, "success: test")

    def test_submit_thread_pool_low(self):
        """测试低优线程池提交"""
        future = self.scheduler.submit(
            sample_success_func,
            {"value": "low"},
            priority=SkillPriority.LOW,
            executor_type=ExecutorType.THREAD
        )
        result = future.result()
        self.assertTrue(result.success)
        self.assertEqual(result.data, "success: low")

    def test_submit_with_error(self):
        """测试提交出错的函数"""
        future = self.scheduler.submit(
            sample_error_func,
            {},
            skill_id="error_skill",
            context=self.context
        )
        result = future.result()
        self.assertFalse(result.success)

    def test_metrics_recording(self):
        """测试指标记录"""
        for i in range(3):
            future = self.scheduler.submit(
                sample_success_func,
                {"value": str(i)},
                skill_id="metric_skill"
            )
            future.result()

        metrics = self.scheduler.get_metrics("metric_skill")
        self.assertEqual(metrics["total_calls"], 3)
        self.assertEqual(metrics["success_count"], 3)
        self.assertEqual(metrics["failure_count"], 0)

    def test_global_metrics(self):
        """测试全局指标"""
        self.scheduler.submit(sample_success_func, {}).result()
        self.scheduler.submit(sample_success_func, {}).result()

        metrics = self.scheduler.get_metrics()
        self.assertEqual(metrics["total_calls"], 2)
        self.assertEqual(metrics["success_count"], 2)

    def test_get_all_metrics(self):
        """测试获取所有指标"""
        self.scheduler.submit(
            sample_success_func,
            {},
            skill_id="skill_a"
        ).result()

        all_metrics = self.scheduler.get_all_metrics()
        self.assertIn("global", all_metrics)
        self.assertIn("skills", all_metrics)
        self.assertIn("skill_a", all_metrics["skills"])

    def test_returns_skill_response(self):
        """测试返回 SkillResponse 的函数"""
        def func_returns_response(params):
            return SkillResponse.success(data="direct_response")

        future = self.scheduler.submit(func_returns_response, {})
        result = future.result()
        self.assertTrue(result.success)
        self.assertEqual(result.data, "direct_response")

    def test_cost_ms_recorded(self):
        """测试耗时记录"""
        future = self.scheduler.submit(sample_success_func, {})
        result = future.result()
        self.assertIn("cost_ms", result.meta)
        self.assertIsInstance(result.meta["cost_ms"], float)


class TestAsyncSubmit(unittest.TestCase):
    """测试异步提交"""

    def setUp(self):
        self.scheduler = ExecutorScheduler()

    def tearDown(self):
        self.scheduler.shutdown(wait=False)

    def test_submit_async(self):
        """测试异步提交"""
        import asyncio

        async def run():
            result = await self.scheduler.submit_async(
                sample_success_func,
                {"value": "async"}
            )
            self.assertTrue(result.success)
            self.assertEqual(result.data, "success: async")

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()

