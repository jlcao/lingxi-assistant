from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from lingxi.web.state import get_assistant
from lingxi.core.utils.exceptions import map_exception_to_error_code
import uuid
import time
import traceback

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



class ConfirmationResponseRequest(BaseModel):
    """确认响应请求模型"""
    request_id: str
    confirmed: bool
    reason: Optional[str] = None


class ApiResponse(BaseModel):
    """统一 API 响应格式"""
    code: int
    message: str
    data: Optional[Any] = None
    error: Optional[Dict[str, str]] = None


@router.post("/tasks/execute", response_model=ApiResponse)
async def execute_task(request: ExecuteTaskRequest) -> Dict[str, Any]:
    """执行任务

    Args:
        request: 执行任务请求数据

    Returns:
        任务执行信息
    """
    try:
        assistant = get_assistant()
        if not assistant:
            return ApiResponse(
                code=503,
                message="助手服务未初始化",
                error={"error_code": "SERVICE_UNAVAILABLE", "error_detail": "助手服务未初始化"}
            )

        execution_id = str(uuid.uuid4())

        if not request.task:
            return ApiResponse(
                code=400,
                message="任务内容不能为空",
                error={"error_code": "INVALID_PARAMETER", "error_detail": "任务内容不能为空"}
            )

        # 移除任务分级，统一使用 simple 级别
        # task_level = assistant.classifier.classify(request.task).get("level", "simple")
        task_level = "simple"  # 默认级别
        model = request.model_override or assistant.config.get("llm", {}).get("model", "qwen3.5-plus")

        task_info = {
            "execution_id": execution_id,
            "task": request.task,
            "task_level": task_level,
            "model": model,
            "status": "running",
            "created_at": time.time(),
            "updated_at": time.time()
        }

        response = await assistant.process_input(request.task, request.session_id)

        task_info.update({
            "status": "completed",
            "result": {"content": response},
            "updated_at": time.time()
        })

        return ApiResponse(code=0, message="success", data=task_info)
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"执行任务失败 - 错误类型: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
        print(f"错误堆栈:\n{error_trace}")
        return ApiResponse(
            code=500,
            message="执行任务失败",
            error={"error_code": "INTERNAL_ERROR", "error_detail": f"{str(e)}\n{error_trace}"}
        )


@router.get("/tasks/{execution_id}/status", response_model=ApiResponse)
async def get_task_status(execution_id: str) -> Dict[str, Any]:
    """获取任务状态

    Args:
        execution_id: 执行ID

    Returns:
        任务状态信息
    """
    try:
        assistant = get_assistant()
        if not assistant:
            return ApiResponse(
                code=503,
                message="助手服务未初始化",
                error={"error_code": "SERVICE_UNAVAILABLE", "error_detail": "助手服务未初始化"}
            )

        checkpoint = assistant.session_manager.restore_checkpoint(execution_id)
        if not checkpoint:
            return ApiResponse(
                code=404,
                message="任务不存在",
                error={"error_code": "NOT_FOUND", "error_detail": f"任务 {execution_id} 不存在"}
            )

        return ApiResponse(
            code=0,
            message="success",
            data={
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
        )
    except Exception as e:
        return ApiResponse(
            code=500,
            message="获取任务状态失败",
            error={"error_code": "INTERNAL_ERROR", "error_detail": str(e)}
        )


@router.post("/tasks/{execution_id}/retry", response_model=ApiResponse)
async def retry_task(execution_id: str, request: RetryTaskRequest) -> Dict[str, Any]:
    """重试任务

    Args:
        execution_id: 执行ID
        request: 重试请求参数

    Returns:
        重试结果
    """
    try:
        assistant = get_assistant()
        if not assistant:
            return ApiResponse(
                code=503,
                message="助手服务未初始化",
                error={"error_code": "SERVICE_UNAVAILABLE", "error_detail": "助手服务未初始化"}
            )

        checkpoint = assistant.session_manager.restore_checkpoint(execution_id)
        if not checkpoint:
            return ApiResponse(
                code=404,
                message="任务不存在",
                error={"error_code": "NOT_FOUND", "error_detail": f"任务 {execution_id} 不存在"}
            )

        if request.user_input:
            checkpoint["user_input"] = request.user_input

        assistant.session_manager.save_checkpoint(execution_id, checkpoint)

        return ApiResponse(
            code=0,
            message="success",
            data={
                "success": True,
                "message": "重试已开始",
                "execution_id": execution_id
            }
        )
    except Exception as e:
        return ApiResponse(
            code=500,
            message="重试任务失败",
            error={"error_code": "INTERNAL_ERROR", "error_detail": str(e)}
        )


@router.post("/tasks/{execution_id}/cancel", response_model=ApiResponse)
async def cancel_task(execution_id: str) -> Dict[str, Any]:
    """取消任务

    Args:
        execution_id: 执行ID

    Returns:
        取消结果
    """
    try:
        assistant = get_assistant()
        if not assistant:
            return ApiResponse(
                code=503,
                message="助手服务未初始化",
                error={"error_code": "SERVICE_UNAVAILABLE", "error_detail": "助手服务未初始化"}
            )

        checkpoint = assistant.session_manager.restore_checkpoint(execution_id)
        if not checkpoint:
            return ApiResponse(
                code=404,
                message="任务不存在",
                error={"error_code": "NOT_FOUND", "error_detail": f"任务 {execution_id} 不存在"}
            )

        checkpoint["execution_status"] = "cancelled"
        assistant.session_manager.save_checkpoint(execution_id, checkpoint)

        return ApiResponse(
            code=0,
            message="success",
            data={
                "success": True,
                "message": "任务已取消",
                "execution_id": execution_id
            }
        )
    except Exception as e:
        return ApiResponse(
            code=500,
            message="取消任务失败",
            error={"error_code": "INTERNAL_ERROR", "error_detail": str(e)}
        )


@router.post("/tasks/confirm", response_model=ApiResponse)
async def respond_confirmation(request: ConfirmationResponseRequest) -> Dict[str, Any]:
    """响应对确认请求（V4.0新增）

    Args:
        request: 确认响应请求数据

    Returns:
        响应结果
    """
    try:
        assistant = get_assistant()
        if not assistant:
            return ApiResponse(
                code=503,
                message="助手服务未初始化",
                error={"error_code": "SERVICE_UNAVAILABLE", "error_detail": "助手服务未初始化"}
            )

        # 获取当前引擎
        engine = assistant.mode_selector.get_engine(mode="plan_react", session_manager=assistant.session_manager)
        
        # 处理确认响应
        success = engine.handle_confirmation_response(
            request.request_id,
            request.confirmed,
            request.reason
        )
        
        if success:
            return ApiResponse(
                code=0,
                message="success",
                data={
                    "success": True,
                    "message": "确认响应处理成功",
                    "request_id": request.request_id,
                    "confirmed": request.confirmed
                }
            )
        else:
            return ApiResponse(
                code=400,
                message="确认响应处理失败",
                data={
                    "success": False,
                    "message": "确认响应处理失败",
                    "request_id": request.request_id
                }
            )
            
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        return ApiResponse(
            code=500,
            message="处理确认响应失败",
            error={"error_code": "INTERNAL_ERROR", "error_detail": f"{str(e)}\n{error_trace}"}
        )
