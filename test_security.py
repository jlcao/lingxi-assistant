"""安全功能测试用例

测试安全沙箱和高危操作确认机制
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from lingxi.core.security import SecuritySandbox, SecurityError, ExecutionError
from lingxi.core.confirmation import (
    ConfirmationManager,
    DangerousSkillChecker,
    RiskLevel,
    ConfirmationRequest
)


class TestSecuritySandbox:
    """安全沙箱测试"""

    def test_validate_path_success(self):
        """测试路径验证成功"""
        with tempfile.TemporaryDirectory() as tmpdir:
            sandbox = SecuritySandbox(workspace_root=tmpdir)
            
            valid_path = os.path.join(tmpdir, "test.txt")
            result = sandbox.validate_path(valid_path)
            
            assert result == Path(valid_path).resolve()

    def test_validate_path_outside_workspace(self):
        """测试路径超出工作空间"""
        with tempfile.TemporaryDirectory() as tmpdir:
            sandbox = SecuritySandbox(workspace_root=tmpdir)
            
            outside_path = "/etc/passwd"
            
            with pytest.raises(SecurityError) as exc_info:
                sandbox.validate_path(outside_path)
            
            assert exc_info.value.error_code == "PATH_OUTSIDE_WORKSPACE"

    def test_safe_read_success(self):
        """测试安全读取文件成功"""
        with tempfile.TemporaryDirectory() as tmpdir:
            sandbox = SecuritySandbox(workspace_root=tmpdir)
            
            test_file = os.path.join(tmpdir, "test.txt")
            test_content = "Hello, World!"
            
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(test_content)
            
            content = sandbox.safe_read(test_file)
            
            assert content == test_content

    def test_safe_read_file_too_large(self):
        """测试读取过大文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            sandbox = SecuritySandbox(workspace_root=tmpdir, max_file_size=1024)
            
            test_file = os.path.join(tmpdir, "large.txt")
            large_content = "x" * 2048
            
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(large_content)
            
            with pytest.raises(SecurityError) as exc_info:
                sandbox.safe_read(test_file)
            
            assert exc_info.value.error_code == "FILE_TOO_LARGE"

    def test_safe_write_success(self):
        """测试安全写入文件成功"""
        with tempfile.TemporaryDirectory() as tmpdir:
            sandbox = SecuritySandbox(workspace_root=tmpdir)
            
            test_file = os.path.join(tmpdir, "test.txt")
            test_content = "Hello, World!"
            
            sandbox.safe_write(test_file, test_content)
            
            assert os.path.exists(test_file)
            with open(test_file, 'r', encoding='utf-8') as f:
                assert f.read() == test_content

    def test_safe_write_file_exists(self):
        """测试写入已存在的文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            sandbox = SecuritySandbox(workspace_root=tmpdir)
            
            test_file = os.path.join(tmpdir, "test.txt")
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write("existing content")
            
            with pytest.raises(SecurityError) as exc_info:
                sandbox.safe_write(test_file, "new content")
            
            assert exc_info.value.error_code == "FILE_EXISTS"

    def test_safe_write_overwrite(self):
        """测试覆盖写入文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            sandbox = SecuritySandbox(workspace_root=tmpdir)
            
            test_file = os.path.join(tmpdir, "test.txt")
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write("existing content")
            
            sandbox.safe_write(test_file, "new content", overwrite=True)
            
            with open(test_file, 'r', encoding='utf-8') as f:
                assert f.read() == "new content"

    def test_safe_exec_allowed_command(self):
        """测试执行允许的命令"""
        with tempfile.TemporaryDirectory() as tmpdir:
            sandbox = SecuritySandbox(workspace_root=tmpdir)
            
            result = sandbox.safe_exec("echo hello")
            
            assert "hello" in result

    def test_safe_exec_command_not_allowed(self):
        """测试执行不允许的命令"""
        with tempfile.TemporaryDirectory() as tmpdir:
            sandbox = SecuritySandbox(workspace_root=tmpdir)
            
            with pytest.raises(SecurityError) as exc_info:
                sandbox.safe_exec("rm -rf /")
            
            assert exc_info.value.error_code == "COMMAND_NOT_ALLOWED"

    def test_safe_exec_dangerous_command(self):
        """测试执行高危命令"""
        with tempfile.TemporaryDirectory() as tmpdir:
            sandbox = SecuritySandbox(workspace_root=tmpdir, safety_mode=True)
            
            with pytest.raises(SecurityError) as exc_info:
                sandbox.safe_exec("format c:")
            
            assert exc_info.value.error_code == "DANGEROUS_OPERATION"

    def test_safe_exec_dangerous_command_safety_off(self):
        """测试安全模式关闭时执行高危命令"""
        with tempfile.TemporaryDirectory() as tmpdir:
            sandbox = SecuritySandbox(workspace_root=tmpdir, safety_mode=False)
            
            result = sandbox.safe_exec("echo test")
            
            assert "test" in result


class TestConfirmationManager:
    """确认管理器测试"""

    @pytest.mark.asyncio
    async def test_create_and_wait_confirmation(self):
        """测试创建和等待确认"""
        manager = ConfirmationManager(timeout=10)
        
        request = manager.create_request(
            operation="test_operation",
            description="测试操作",
            risk_level=RiskLevel.MEDIUM
        )
        
        assert isinstance(request, ConfirmationRequest)
        assert request.operation == "test_operation"
        assert request.risk_level == RiskLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_respond_confirmation(self):
        """测试响应确认"""
        manager = ConfirmationManager(timeout=10)
        
        request = manager.create_request(
            operation="test_operation",
            description="测试操作",
            risk_level=RiskLevel.MEDIUM
        )
        
        confirmed = await manager.wait_for_confirmation(request.request_id)
        
        assert confirmed is False

        success = manager.respond_confirmation(request.request_id, True)
        
        assert success is True

    @pytest.mark.asyncio
    async def test_confirmation_timeout(self):
        """测试确认超时"""
        manager = ConfirmationManager(timeout=1, auto_reject_timeout=True)
        
        request = manager.create_request(
            operation="test_operation",
            description="测试操作",
            risk_level=RiskLevel.MEDIUM
        )
        
        confirmed = await manager.wait_for_confirmation(request.request_id)
        
        assert confirmed is False

    @pytest.mark.asyncio
    async def test_cancel_request(self):
        """测试取消确认请求"""
        manager = ConfirmationManager(timeout=10)
        
        request = manager.create_request(
            operation="test_operation",
            description="测试操作",
            risk_level=RiskLevel.MEDIUM
        )
        
        success = manager.cancel_request(request.request_id)
        
        assert success is True

    def test_get_pending_requests(self):
        """测试获取待确认请求"""
        manager = ConfirmationManager(timeout=10)
        
        request1 = manager.create_request(
            operation="operation1",
            description="操作1",
            risk_level=RiskLevel.LOW
        )
        
        request2 = manager.create_request(
            operation="operation2",
            description="操作2",
            risk_level=RiskLevel.HIGH
        )
        
        pending = manager.get_pending_requests()
        
        assert len(pending) == 2
        assert request1.request_id in pending
        assert request2.request_id in pending


class TestDangerousSkillChecker:
    """高危技能检查器测试"""

    def test_check_skill_risk_low(self):
        """测试低风险技能"""
        risk = DangerousSkillChecker.check_skill_risk("file.create")
        
        assert risk == RiskLevel.LOW

    def test_check_skill_risk_high(self):
        """测试高风险技能"""
        risk = DangerousSkillChecker.check_skill_risk("system.exec")
        
        assert risk == RiskLevel.HIGH

    def test_check_skill_risk_critical(self):
        """测试严重风险技能"""
        risk = DangerousSkillChecker.check_skill_risk("shell.exec")
        
        assert risk == RiskLevel.CRITICAL

    def test_check_command_risk_low(self):
        """测试低风险命令"""
        risk = DangerousSkillChecker.check_command_risk("ls -la")
        
        assert risk == RiskLevel.LOW

    def test_check_command_risk_high(self):
        """测试高风险命令"""
        risk = DangerousSkillChecker.check_command_risk("rm -rf /tmp")
        
        assert risk == RiskLevel.HIGH

    def test_check_command_risk_critical(self):
        """测试严重风险命令"""
        risk = DangerousSkillChecker.check_command_risk("shutdown -h now")
        
        assert risk == RiskLevel.CRITICAL

    def test_is_dangerous_true(self):
        """测试判断为高危操作"""
        is_dangerous = DangerousSkillChecker.is_dangerous(
            skill_id="system.exec",
            command="rm -rf /"
        )
        
        assert is_dangerous is True

    def test_is_dangerous_false(self):
        """测试判断为非高危操作"""
        is_dangerous = DangerousSkillChecker.is_dangerous(
            skill_id="file.read",
            command="cat test.txt"
        )
        
        assert is_dangerous is False

    def test_get_risk_description(self):
        """测试获取风险描述"""
        assert DangerousSkillChecker.get_risk_description(RiskLevel.LOW) == "低风险"
        assert DangerousSkillChecker.get_risk_description(RiskLevel.MEDIUM) == "中等风险"
        assert DangerousSkillChecker.get_risk_description(RiskLevel.HIGH) == "高风险"
        assert DangerousSkillChecker.get_risk_description(RiskLevel.CRITICAL) == "严重风险"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
