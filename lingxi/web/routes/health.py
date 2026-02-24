from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter()

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """健康检查API
    
    Returns:
        健康状态信息
    """
    return {
        "status": "healthy",
        "service": "lingxi-web",
        "version": "0.1.0"
    }
