"""工作目录 API 路由"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workspace", tags=["workspace"])


class WorkspaceSwitchRequest(BaseModel):
    """切换工作目录请求"""
    workspace_path: str
    force: bool = False


class WorkspaceSwitchResponse(BaseModel):
    """切换工作目录响应"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class WorkspaceInfoResponse(BaseModel):
    """工作目录信息响应"""
    workspace: Optional[str]
    lingxi_dir: Optional[str]
    is_initialized: bool


@router.post("/switch", response_model=WorkspaceSwitchResponse)
async def switch_workspace(request: WorkspaceSwitchRequest):
    """切换工作目录
    
    请求示例:
    ```json
    {
        "workspace_path": "D:/projects/my-project",
        "force": false
    }
    ```
    
    返回示例:
    ```json
    {
        "success": true,
        "data": {
            "previous_workspace": "D:/projects/old-project",
            "current_workspace": "D:/projects/my-project",
            "lingxi_dir": "D:/projects/my-project/.lingxi",
            "switched_at": "2026-03-07T10:00:00"
        }
    }
    ```
    """
    try:
        from lingxi.management.workspace import get_workspace_manager
        
        workspace_manager = get_workspace_manager()
        result = await workspace_manager.switch_workspace(
            request.workspace_path,
            force=request.force
        )
        
        return WorkspaceSwitchResponse(success=True, data=result)
    except Exception as e:
        logger.error(f"切换工作目录失败：{e}")
        raise HTTPException(status_code=500, detail=f"切换失败：{str(e)}")


@router.get("/current", response_model=WorkspaceInfoResponse)
async def get_current_workspace():
    """获取当前工作目录
    
    返回示例:
    ```json
    {
        "workspace": "D:/projects/my-project",
        "lingxi_dir": "D:/projects/my-project/.lingxi",
        "is_initialized": true
    }
    ```
    """
    from lingxi.management.workspace import get_workspace_manager
    
    workspace_manager = get_workspace_manager()
    workspace = workspace_manager.get_current_workspace()
    
    if workspace is None:
        return WorkspaceInfoResponse(
            workspace=None,
            lingxi_dir=None,
            is_initialized=False
        )
    
    return WorkspaceInfoResponse(
        workspace=str(workspace),
        lingxi_dir=str(workspace_manager.get_lingxi_directory()),
        is_initialized=True
    )


@router.post("/initialize")
async def initialize_workspace(workspace_path: Optional[str] = None):
    """初始化工作目录
    
    请求示例:
    ```json
    {
        "workspace_path": "D:/projects/new-project"
    }
    ```
    
    返回示例:
    ```json
    {
        "success": true,
        "data": {
            "workspace": "D:/projects/new-project",
            "lingxi_dir": "D:/projects/new-project/.lingxi"
        }
    }
    ```
    """
    try:
        from lingxi.management.workspace import get_workspace_manager
        
        workspace_manager = get_workspace_manager()
        lingxi_dir = workspace_manager.initialize(workspace_path)
        
        return {
            "success": True,
            "data": {
                "workspace": str(workspace_manager.get_current_workspace()),
                "lingxi_dir": str(lingxi_dir)
            }
        }
    except Exception as e:
        logger.error(f"初始化工作目录失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/validate")
async def validate_workspace(workspace_path: str):
    """验证工作目录是否有效
    
    查询参数:
    - workspace_path: 工作目录路径
    
    返回示例:
    ```json
    {
        "valid": true,
        "exists": true,
        "has_lingxi_dir": true,
        "message": "工作目录有效"
    }
    ```
    """
    from pathlib import Path
    from lingxi.management.workspace import get_workspace_manager
    
    workspace_manager = get_workspace_manager()
    path = Path(workspace_path).resolve()
    
    exists = path.exists()
    has_lingxi_dir = (path / ".lingxi").exists() if exists else False
    valid = workspace_manager.validate_workspace(path)
    
    return {
        "valid": valid,
        "exists": exists,
        "has_lingxi_dir": has_lingxi_dir,
        "message": "工作目录有效" if valid else "工作目录无效"
    }
