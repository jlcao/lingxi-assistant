"""工作目录功能单元测试"""

import pytest
import tempfile
import asyncio
from pathlib import Path
from lingxi.management.workspace import WorkspaceManager, WorkspaceNotFoundError, reset_workspace_manager


class TestWorkspaceManager:
    """工作目录管理器测试"""
    
    @pytest.fixture
    def workspace_manager(self):
        """创建工作目录管理器"""
        config = {
            "security": {
                "workspace_root": "./workspace",
                "safety_mode": True
            },
            "database": {
                "assistant_db": "./data/assistant.db",
                "memory_db": "./data/long_term_memory.db"
            },
            "skills": {
                "enabled": []
            }
        }
        reset_workspace_manager()
        return WorkspaceManager(config)
    
    def test_initialize_workspace(self, workspace_manager):
        """测试初始化工作目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            lingxi_dir = workspace_manager.initialize(tmpdir)
            
            assert (lingxi_dir / "conf").exists()
            assert (lingxi_dir / "data").exists()
            assert (lingxi_dir / "skills").exists()
            assert (lingxi_dir / "conf" / "config.yml").exists()
    
    def test_initialize_existing_workspace(self, workspace_manager):
        """测试初始化已存在的工作目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 第一次初始化
            lingxi_dir1 = workspace_manager.initialize(tmpdir)
            
            # 第二次初始化（已存在）
            lingxi_dir2 = workspace_manager.initialize(tmpdir)
            
            assert lingxi_dir1 == lingxi_dir2
    
    def test_switch_workspace(self, workspace_manager):
        """测试切换工作目录"""
        import asyncio
        
        async def run_switch():
            with tempfile.TemporaryDirectory() as tmpdir1:
                with tempfile.TemporaryDirectory() as tmpdir2:
                    # 初始化第一个工作目录
                    workspace_manager.initialize(tmpdir1)
                    
                    # 切换到第二个工作目录
                    result = await workspace_manager.switch_workspace(tmpdir2)
                    
                    assert result["success"] is True
                    assert workspace_manager.get_current_workspace() == Path(tmpdir2)
        
        asyncio.run(run_switch())
    
    def test_switch_workspace_not_exists(self, workspace_manager):
        """测试切换不存在的目录"""
        import asyncio
        
        async def run_switch():
            with tempfile.TemporaryDirectory() as tmpdir:
                workspace_manager.initialize(tmpdir)
                
                with pytest.raises(WorkspaceNotFoundError):
                    await workspace_manager.switch_workspace("/non/existent/path")
        
        asyncio.run(run_switch())
    
    def test_validate_workspace_valid(self, workspace_manager):
        """测试验证有效的工作目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_manager.initialize(tmpdir)
            
            assert workspace_manager.validate_workspace(Path(tmpdir)) is True
    
    def test_validate_workspace_not_exists(self, workspace_manager):
        """测试验证不存在的工作目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            non_existent = Path(tmpdir) / "non_existent"
            assert workspace_manager.validate_workspace(non_existent) is False
    
    def test_get_current_workspace(self, workspace_manager):
        """测试获取当前工作目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_manager.initialize(tmpdir)
            
            current = workspace_manager.get_current_workspace()
            assert current is not None
            assert str(current) == tmpdir
    
    def test_get_lingxi_directory(self, workspace_manager):
        """测试获取.lingxi 目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace_manager.initialize(tmpdir)
            
            lingxi_dir = workspace_manager.get_lingxi_directory()
            assert lingxi_dir is not None
            assert lingxi_dir == Path(tmpdir) / ".lingxi"
    
    def test_config_merge(self, workspace_manager):
        """测试配置合并逻辑"""
        base_config = {
            "security": {
                "safety_mode": True,
                "max_file_size": 10485760
            },
            "database": {
                "path": "./data/db.sqlite"
            }
        }
        
        override_config = {
            "security": {
                "safety_mode": False
            }
        }
        
        merged = workspace_manager._deep_merge(base_config, override_config)
        
        assert merged['security']['safety_mode'] is False  # 被覆盖
        assert merged['security']['max_file_size'] == 10485760  # 保留
        assert merged['database']['path'] == "./data/db.sqlite"  # 保留
    
    def test_default_workspace_config(self, workspace_manager):
        """测试默认工作目录配置文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            lingxi_dir = workspace_manager.initialize(tmpdir)
            config_file = lingxi_dir / "conf" / "config.yml"
            
            assert config_file.exists()
            
            import yaml
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            assert 'workspace' in config
            assert 'skills' in config
            assert 'database' in config
            assert 'security' in config


class TestWorkspaceConfig:
    """工作目录配置测试"""
    
    @pytest.fixture
    def workspace_manager(self):
        """创建工作目录管理器"""
        config = {
            "security": {
                "workspace_root": "./workspace",
                "safety_mode": True
            }
        }
        reset_workspace_manager()
        return WorkspaceManager(config)
    
    def test_load_workspace_config(self, workspace_manager):
        """测试加载工作目录配置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            lingxi_dir = workspace_manager.initialize(tmpdir)
            
            # 修改配置文件
            config_file = lingxi_dir / "conf" / "config.yml"
            custom_config = {
                "workspace": {
                    "name": "测试工作空间",
                    "description": "单元测试测试"
                },
                "security": {
                    "safety_mode": False,
                    "max_file_size": 20971520
                }
            }
            
            import yaml
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(custom_config, f, allow_unicode=True)
            
            # 重新加载配置
            loaded_config = workspace_manager._load_workspace_config(lingxi_dir)
            
            assert loaded_config['workspace']['name'] == "测试工作空间"
            assert loaded_config['security']['safety_mode'] is False
            assert loaded_config['security']['max_file_size'] == 20971520


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
