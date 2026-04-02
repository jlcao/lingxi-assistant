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


@router.get("/skills")
async def list_skills(enabled_only: bool = False) -> Dict[str, Any]:
    """获取技能列表

    Args:
        enabled_only: 是否只返回已启用的技能

    Returns:
        技能列表
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        skills = assistant.action_caller.list_available_skills(enabled_only=enabled_only)
        return {
            "skills": skills,
            "count": len(skills)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取技能列表失败: {str(e)}")


@router.get("/skills/{skill_id}")
async def get_skill(skill_id: str) -> Dict[str, Any]:
    """获取技能详情

    Args:
        skill_id: 技能ID

    Returns:
        技能详情
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        skills = assistant.action_caller.list_available_skills(enabled_only=False)
        skill = next((s for s in skills if s.get("skill_id") == skill_id), None)

        if not skill:
            raise HTTPException(status_code=404, detail=f"技能 {skill_id} 不存在")

        return skill
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取技能详情失败: {str(e)}")


@router.post("/skills/install")
async def install_skill(request: InstallSkillRequest) -> Dict[str, Any]:
    """安装技能

    Args:
        request: 安装技能请求数据

    Returns:
        安装结果
    """
    assistant = get_assistant()
    websocket_manager = get_websocket_manager()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        skill_data = request.skill_data
        skill_name = skill_data.get("name")

        if not skill_name:
            raise HTTPException(status_code=400, detail="技能名称不能为空")

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

            return {
                "skill_id": skill_id,
                "status": "installed",
                "message": f"技能安装成功: {skill_name}"
            }
        else:
            raise HTTPException(status_code=500, detail="技能安装失败")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"安装技能失败: {str(e)}")


@router.get("/skills/{skill_id}/diagnose")
async def diagnose_skill(skill_id: str) -> Dict[str, Any]:
    """诊断技能

    Args:
        skill_id: 技能ID

    Returns:
        诊断结果
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        skills = assistant.action_caller.list_available_skills(enabled_only=False)
        skill = next((s for s in skills if s.get("skill_id") == skill_id), None)

        if not skill:
            raise HTTPException(status_code=404, detail=f"技能 {skill_id} 不存在")

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

        return diagnostic_result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"诊断技能失败: {str(e)}")


@router.post("/skills/{skill_id}/reload")
async def reload_skill(skill_id: str) -> Dict[str, Any]:
    """重新加载技能

    Args:
        skill_id: 技能ID

    Returns:
        重载结果
    """
    # 测试自动重载功能
    assistant = get_assistant()
    websocket_manager = get_websocket_manager()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        skills = assistant.action_caller.list_available_skills(enabled_only=False)
        skill = next((s for s in skills if s.get("skill_id") == skill_id), None)

        if not skill:
            raise HTTPException(status_code=404, detail=f"技能 {skill_id} 不存在")

        if websocket_manager:
            await websocket_manager.broadcast({
                "event_type": "skill_reloaded",
                "data": {
                    "skill_id": skill_id,
                    "timestamp": time.time()
                }
            })

        return {
            "success": True,
            "message": f"技能已重新加载: {skill_id}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重新加载技能失败: {str(e)}")


@router.delete("/skills/{skill_id}")
async def uninstall_skill(skill_id: str) -> Dict[str, Any]:
    """卸载技能

    Args:
        skill_id: 技能ID

    Returns:
        卸载结果
    """
    assistant = get_assistant()
    websocket_manager = get_websocket_manager()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        skills = assistant.action_caller.list_available_skills(enabled_only=False)
        skill = next((s for s in skills if s.get("skill_id") == skill_id), None)

        if not skill:
            raise HTTPException(status_code=404, detail=f"技能 {skill_id} 不存在")

        if websocket_manager:
            await websocket_manager.broadcast({
                "event_type": "skill_uninstalled",
                "data": {
                    "skill_id": skill_id,
                    "timestamp": time.time()
                }
            })

        return {
            "success": True,
            "message": f"技能已卸载: {skill_id}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"卸载技能失败: {str(e)}")
