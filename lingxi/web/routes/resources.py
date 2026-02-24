from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from lingxi.web.state import get_assistant
import psutil
import time

router = APIRouter()


class ResourceInfo(BaseModel):
    """资源信息模型"""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    token_usage: Optional[Dict[str, Any]] = None


@router.get("/resources")
async def get_resources() -> Dict[str, Any]:
    """获取资源使用情况

    Returns:
        资源使用信息
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        token_usage = None
        if hasattr(assistant, 'llm_client') and hasattr(assistant.llm_client, 'get_token_usage'):
            token_usage = assistant.llm_client.get_token_usage()

        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "disk_percent": disk.percent,
            "memory_used_mb": memory.used / (1024 * 1024),
            "memory_total_mb": memory.total / (1024 * 1024),
            "disk_used_gb": disk.used / (1024 * 1024 * 1024),
            "disk_total_gb": disk.total / (1024 * 1024 * 1024),
            "token_usage": token_usage or {
                "current": 0,
                "limit": 100000,
                "percent": 0.0
            },
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取资源信息失败: {str(e)}")


@router.get("/resources/stats")
async def get_resource_stats() -> Dict[str, Any]:
    """获取资源统计信息

    Returns:
        资源统计信息
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        cpu_count = psutil.cpu_count()
        cpu_count_logical = psutil.cpu_count(logical=True)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            "cpu": {
                "count_physical": cpu_count,
                "count_logical": cpu_count_logical,
                "percent": psutil.cpu_percent(interval=1)
            },
            "memory": {
                "total_gb": memory.total / (1024 * 1024 * 1024),
                "available_gb": memory.available / (1024 * 1024 * 1024),
                "used_gb": memory.used / (1024 * 1024 * 1024),
                "percent": memory.percent
            },
            "disk": {
                "total_gb": disk.total / (1024 * 1024 * 1024),
                "used_gb": disk.used / (1024 * 1024 * 1024),
                "free_gb": disk.free / (1024 * 1024 * 1024),
                "percent": disk.percent
            },
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取资源统计失败: {str(e)}")
