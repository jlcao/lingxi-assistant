from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
from lingxi.web.state import get_assistant, get_websocket_manager
import time

router = APIRouter()


class CheckpointInfo(BaseModel):
    """断点信息模型"""
    session_id: str
    task: str
    current_step: int
    total_steps: int
    execution_status: str
    updated_at: float


@router.get("/checkpoints")
async def get_checkpoints() -> Dict[str, Any]:
    """获取断点列表

    Returns:
        断点列表
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        checkpoints = assistant.session_manager.list_active_checkpoints()
        return {
            "checkpoints": checkpoints,
            "count": len(checkpoints)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取断点列表失败: {str(e)}")


@router.get("/checkpoints/{session_id}/status")
async def get_checkpoint_status(session_id: str) -> Dict[str, Any]:
    """获取指定会话的断点状态

    Args:
        session_id: 会话ID

    Returns:
        断点状态信息
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        status = assistant.session_manager.get_checkpoint_status(session_id)
        return {
            "session_id": session_id,
            "checkpoint_status": status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取断点状态失败: {str(e)}")


@router.post("/checkpoints/{session_id}/resume")
async def resume_checkpoint(session_id: str) -> Dict[str, Any]:
    """恢复断点

    Args:
        session_id: 会话ID

    Returns:
        恢复结果
    """
    assistant = get_assistant()
    websocket_manager = get_websocket_manager()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        checkpoint = assistant.session_manager.restore_checkpoint(session_id)
        if not checkpoint:
            raise HTTPException(status_code=404, detail=f"会话 {session_id} 没有断点")

        execution_id = session_id
        task = checkpoint.get("task", "")

        checkpoint["execution_status"] = "running"
        assistant.session_manager.save_checkpoint(session_id, checkpoint)

        if websocket_manager:
            await websocket_manager.broadcast({
                "event_type": "checkpoint_resumed",
                "data": {
                    "execution_id": execution_id,
                    "session_id": session_id,
                    "task": task,
                    "timestamp": time.time()
                }
            })

        return {
            "execution_id": execution_id,
            "task": task,
            "status": "running",
            "message": "断点已恢复"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"恢复断点失败: {str(e)}")


@router.delete("/checkpoints/{session_id}")
async def delete_checkpoint(session_id: str) -> Dict[str, Any]:
    """删除断点

    Args:
        session_id: 会话ID

    Returns:
        删除结果
    """
    assistant = get_assistant()
    websocket_manager = get_websocket_manager()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        checkpoint = assistant.session_manager.restore_checkpoint(session_id)
        if not checkpoint:
            raise HTTPException(status_code=404, detail=f"会话 {session_id} 没有断点")

        assistant.session_manager.clear_checkpoint(session_id)

        if websocket_manager:
            await websocket_manager.broadcast({
                "event_type": "checkpoint_deleted",
                "data": {
                    "session_id": session_id,
                    "timestamp": time.time()
                }
            })

        return {
            "success": True,
            "message": f"断点已删除: {session_id}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除断点失败: {str(e)}")


@router.post("/checkpoints/cleanup")
async def cleanup_checkpoints(ttl_hours: int = 24) -> Dict[str, Any]:
    """清理过期断点

    Args:
        ttl_hours: 生存时间（小时）

    Returns:
        清理结果
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        cleaned_count = assistant.session_manager.cleanup_expired_checkpoints(ttl_hours)
        return {
            "success": True,
            "cleaned_count": cleaned_count,
            "message": f"清理了 {cleaned_count} 个过期断点"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理过期断点失败: {str(e)}")
