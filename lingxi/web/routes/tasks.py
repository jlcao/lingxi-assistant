from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from lingxi.web.state import get_assistant, get_websocket_manager
import uuid
import time

router = APIRouter()


class ExecuteTaskRequest(BaseModel):
    """执行任务请求模型"""
    task: str
    session_id: str = "default"
    model_override: Optional[str] = None


class RetryTaskRequest(BaseModel):
    """重试任务请求模型"""
    step_index: Optional[int] = None
    user_input: Optional[str] = None


class TaskStatusResponse(BaseModel):
    """任务状态响应模型"""
    execution_id: str
    task: str
    task_level: str
    model: str
    status: str
    current_step: int
    total_steps: int
    result: Optional[Dict[str, Any]] = None
    created_at: float
    updated_at: float


@router.post("/tasks/execute")
async def execute_task(request: ExecuteTaskRequest) -> Dict[str, Any]:
    """执行任务

    Args:
        request: 执行任务请求数据

    Returns:
        任务执行信息
    """
    assistant = get_assistant()
    websocket_manager = get_websocket_manager()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        if not request.task:
            raise HTTPException(status_code=400, detail="任务内容不能为空")

        execution_id = str(uuid.uuid4())

        task_level = assistant.task_classifier.classify(request.task).get("level", "simple")
        model = request.model_override or assistant.execution_mode_selector.select_model(task_level)

        task_info = {
            "execution_id": execution_id,
            "task": request.task,
            "task_level": task_level,
            "model": model,
            "status": "running",
            "created_at": time.time(),
            "updated_at": time.time()
        }

        if websocket_manager:
            await websocket_manager.send_model_route_event(
                request.session_id,
                task_level,
                model,
                f"任务级别: {task_level}"
            )

        response = assistant.process_input(request.task, request.session_id)

        task_info.update({
            "status": "completed",
            "result": {"content": response},
            "updated_at": time.time()
        })

        if websocket_manager:
            await websocket_manager.send_task_completed_event(
                request.session_id,
                execution_id,
                request.task,
                {"content": response}
            )

        return task_info
    except Exception as e:
        if websocket_manager:
            await websocket_manager.send_task_failed_event(
                request.session_id,
                execution_id,
                request.task,
                {
                    "type": "execution_error",
                    "message": str(e)
                }
            )
        raise HTTPException(status_code=500, detail=f"执行任务失败: {str(e)}")


@router.get("/tasks/{execution_id}/status")
async def get_task_status(execution_id: str) -> Dict[str, Any]:
    """获取任务状态

    Args:
        execution_id: 执行ID

    Returns:
        任务状态信息
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        checkpoint = assistant.session_manager.restore_checkpoint(execution_id)
        if not checkpoint:
            raise HTTPException(status_code=404, detail=f"任务 {execution_id} 不存在")

        return {
            "execution_id": execution_id,
            "task": checkpoint.get("task", ""),
            "task_level": checkpoint.get("task_level", "unknown"),
            "model": checkpoint.get("model", "unknown"),
            "status": checkpoint.get("execution_status", "unknown"),
            "current_step": checkpoint.get("current_step_idx", 0),
            "total_steps": len(checkpoint.get("plan", [])),
            "result": checkpoint.get("result"),
            "created_at": checkpoint.get("timestamp", 0),
            "updated_at": checkpoint.get("updated_at", 0)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务状态失败: {str(e)}")


@router.post("/tasks/{execution_id}/retry")
async def retry_task(execution_id: str, request: RetryTaskRequest) -> Dict[str, Any]:
    """重试任务

    Args:
        execution_id: 执行ID
        request: 重试请求参数

    Returns:
        重试结果
    """
    assistant = get_assistant()
    websocket_manager = get_websocket_manager()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        checkpoint = assistant.session_manager.restore_checkpoint(execution_id)
        if not checkpoint:
            raise HTTPException(status_code=404, detail=f"任务 {execution_id} 不存在")

        if request.user_input:
            checkpoint["user_input"] = request.user_input

        assistant.session_manager.save_checkpoint(execution_id, checkpoint)

        if websocket_manager:
            await websocket_manager.broadcast({
                "event_type": "task_retried",
                "data": {
                    "execution_id": execution_id,
                    "step_index": request.step_index,
                    "timestamp": time.time()
                }
            })

        return {
            "success": True,
            "message": "重试已开始",
            "execution_id": execution_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重试任务失败: {str(e)}")


@router.post("/tasks/{execution_id}/cancel")
async def cancel_task(execution_id: str) -> Dict[str, Any]:
    """取消任务

    Args:
        execution_id: 执行ID

    Returns:
        取消结果
    """
    assistant = get_assistant()
    websocket_manager = get_websocket_manager()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        checkpoint = assistant.session_manager.restore_checkpoint(execution_id)
        if not checkpoint:
            raise HTTPException(status_code=404, detail=f"任务 {execution_id} 不存在")

        checkpoint["execution_status"] = "cancelled"
        assistant.session_manager.save_checkpoint(execution_id, checkpoint)

        if websocket_manager:
            await websocket_manager.broadcast({
                "event_type": "task_cancelled",
                "data": {
                    "execution_id": execution_id,
                    "timestamp": time.time()
                }
            })

        return {
            "success": True,
            "message": "任务已取消",
            "execution_id": execution_id
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取消任务失败: {str(e)}")
