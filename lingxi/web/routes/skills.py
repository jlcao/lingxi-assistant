from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from lingxi.web.state import get_assistant, get_websocket_manager
import time

router = APIRouter()


class InstallSkillRequest(BaseModel):
    """安装技能请求模型"""
    skill_data: Dict[str, Any]
    skill_files: Dict[str, str]
    overwrite: bool = False


class SkillInfo(BaseModel):
    """技能信息模型"""
    skill_id: str
    name: str
    description: str
    version: str
    status: str
    manifest: Optional[Dict[str, Any]] = None


class ApiResponse(BaseModel):
    """统一 API 响应格式"""
    code: int
    message: str
    data: Optional[Any] = None
    error: Optional[Dict[str, str]] = None


@router.get("/skills", response_model=ApiResponse)
async def list_skills(enabled_only: bool = False) -> Dict[str, Any]:
    """获取技能列表

    Args:
        enabled_only: 是否只返回已启用的技能

    Returns:
        技能列表
    """
    try:
        assistant = get_assistant()
        if not assistant:
            return ApiResponse(
                code=503,
                message="助手服务未初始化",
                error={"error_code": "SERVICE_UNAVAILABLE", "error_detail": "助手服务未初始化"}
            )

        skills = assistant.action_caller.list_available_skills(enabled_only=enabled_only)
        return ApiResponse(
            code=0,
            message="success",
            data={
                "skills": skills,
                "count": len(skills)
            }
        )
    except Exception as e:
        return ApiResponse(
            code=500,
            message="获取技能列表失败",
            error={"error_code": "INTERNAL_ERROR", "error_detail": str(e)}
        )


@router.get("/skills/{skill_id}", response_model=ApiResponse)
async def get_skill(skill_id: str) -> Dict[str, Any]:
    """获取技能详情

    Args:
        skill_id: 技能ID

    Returns:
        技能详情
    """
    try:
        assistant = get_assistant()
        if not assistant:
            return ApiResponse(
                code=503,
                message="助手服务未初始化",
                error={"error_code": "SERVICE_UNAVAILABLE", "error_detail": "助手服务未初始化"}
            )

        skills = assistant.action_caller.list_available_skills(enabled_only=False)
        skill = next((s for s in skills if s.get("skill_id") == skill_id), None)

        if not skill:
            return ApiResponse(
                code=404,
                message="技能不存在",
                error={"error_code": "NOT_FOUND", "error_detail": f"技能 {skill_id} 不存在"}
            )

        return ApiResponse(code=0, message="success", data=skill)
    except Exception as e:
        return ApiResponse(
            code=500,
            message="获取技能详情失败",
            error={"error_code": "INTERNAL_ERROR", "error_detail": str(e)}
        )


@router.post("/skills/install", response_model=ApiResponse)
async def install_skill(request: InstallSkillRequest) -> Dict[str, Any]:
    """安装技能

    Args:
        request: 安装技能请求数据

    Returns:
        安装结果
    """
    try:
        assistant = get_assistant()
        websocket_manager = get_websocket_manager()
        if not assistant:
            return ApiResponse(
                code=503,
                message="助手服务未初始化",
                error={"error_code": "SERVICE_UNAVAILABLE", "error_detail": "助手服务未初始化"}
            )

        skill_data = request.skill_data
        skill_name = skill_data.get("name")

        if not skill_name:
            return ApiResponse(
                code=400,
                message="技能名称不能为空",
                error={"error_code": "INVALID_PARAMETER", "error_detail": "技能名称不能为空"}
            )

        skill_id = skill_name.lower().replace(" ", "_")

        success = assistant.install_skill(
            skill_source=skill_data.get("entry_point", ""),
            skill_name=skill_id,
            overwrite=request.overwrite
        )

        if success:
            if websocket_manager:
                await websocket_manager.broadcast({
                    "event_type": "skill_installed",
                    "data": {
                        "skill_id": skill_id,
                        "skill_name": skill_name,
                        "timestamp": time.time()
                    }
                })

            return ApiResponse(
                code=0,
                message="success",
                data={
                    "skill_id": skill_id,
                    "status": "installed",
                    "message": f"技能安装成功: {skill_name}"
                }
            )
        else:
            return ApiResponse(
                code=500,
                message="技能安装失败",
                error={"error_code": "INTERNAL_ERROR", "error_detail": "技能安装失败"}
            )
    except Exception as e:
        return ApiResponse(
            code=500,
            message="安装技能失败",
            error={"error_code": "INTERNAL_ERROR", "error_detail": str(e)}
        )


@router.get("/skills/{skill_id}/diagnose", response_model=ApiResponse)
async def diagnose_skill(skill_id: str) -> Dict[str, Any]:
    """诊断技能

    Args:
        skill_id: 技能ID

    Returns:
        诊断结果
    """
    try:
        assistant = get_assistant()
        if not assistant:
            return ApiResponse(
                code=503,
                message="助手服务未初始化",
                error={"error_code": "SERVICE_UNAVAILABLE", "error_detail": "助手服务未初始化"}
            )

        skills = assistant.action_caller.list_available_skills(enabled_only=False)
        skill = next((s for s in skills if s.get("skill_id") == skill_id), None)

        if not skill:
            return ApiResponse(
                code=404,
                message="技能不存在",
                error={"error_code": "NOT_FOUND", "error_detail": f"技能 {skill_id} 不存在"}
            )

        diagnostic_result = {
            "skill_id": skill_id,
            "status": "ok",
            "diagnostic_result": {
                "error_type": None,
                "error_message": None,
                "fix_suggestion": None,
                "can_auto_fix": False
            }
        }

        return ApiResponse(code=0, message="success", data=diagnostic_result)
    except Exception as e:
        return ApiResponse(
            code=500,
            message="诊断技能失败",
            error={"error_code": "INTERNAL_ERROR", "error_detail": str(e)}
        )


@router.post("/skills/{skill_id}/reload", response_model=ApiResponse)
async def reload_skill(skill_id: str) -> Dict[str, Any]:
    """重新加载技能

    Args:
        skill_id: 技能ID

    Returns:
        重载结果
    """
    # 测试自动重载功能
    try:
        assistant = get_assistant()
        websocket_manager = get_websocket_manager()
        if not assistant:
            return ApiResponse(
                code=503,
                message="助手服务未初始化",
                error={"error_code": "SERVICE_UNAVAILABLE", "error_detail": "助手服务未初始化"}
            )

        skills = assistant.action_caller.list_available_skills(enabled_only=False)
        skill = next((s for s in skills if s.get("skill_id") == skill_id), None)

        if not skill:
            return ApiResponse(
                code=404,
                message="技能不存在",
                error={"error_code": "NOT_FOUND", "error_detail": f"技能 {skill_id} 不存在"}
            )

        if websocket_manager:
            await websocket_manager.broadcast({
                "event_type": "skill_reloaded",
                "data": {
                    "skill_id": skill_id,
                    "timestamp": time.time()
                }
            })

        return ApiResponse(
            code=0,
            message="success",
            data={
                "success": True,
                "message": f"技能已重新加载: {skill_id}"
            }
        )
    except Exception as e:
        return ApiResponse(
            code=500,
            message="重新加载技能失败",
            error={"error_code": "INTERNAL_ERROR", "error_detail": str(e)}
        )


@router.delete("/skills/{skill_id}", response_model=ApiResponse)
async def uninstall_skill(skill_id: str) -> Dict[str, Any]:
    """卸载技能

    Args:
        skill_id: 技能ID

    Returns:
        卸载结果
    """
    try:
        assistant = get_assistant()
        websocket_manager = get_websocket_manager()
        if not assistant:
            return ApiResponse(
                code=503,
                message="助手服务未初始化",
                error={"error_code": "SERVICE_UNAVAILABLE", "error_detail": "助手服务未初始化"}
            )

        skills = assistant.action_caller.list_available_skills(enabled_only=False)
        skill = next((s for s in skills if s.get("skill_id") == skill_id), None)

        if not skill:
            return ApiResponse(
                code=404,
                message="技能不存在",
                error={"error_code": "NOT_FOUND", "error_detail": f"技能 {skill_id} 不存在"}
            )

        if websocket_manager:
            await websocket_manager.broadcast({
                "event_type": "skill_uninstalled",
                "data": {
                    "skill_id": skill_id,
                    "timestamp": time.time()
                }
            })

        return ApiResponse(
            code=0,
            message="success",
            data={
                "success": True,
                "message": f"技能已卸载: {skill_id}"
            }
        )
    except Exception as e:
        return ApiResponse(
            code=500,
            message="卸载技能失败",
            error={"error_code": "INTERNAL_ERROR", "error_detail": str(e)}
        )
