from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from lingxi.web.state import get_assistant
import time

router = APIRouter()


class ConfigUpdateRequest(BaseModel):
    """配置更新请求模型"""
    llm: Optional[Dict[str, Any]] = None
    task_classification: Optional[Dict[str, Any]] = None
    execution_mode: Optional[Dict[str, Any]] = None
    skill_call: Optional[Dict[str, Any]] = None
    session: Optional[Dict[str, Any]] = None
    logging: Optional[Dict[str, Any]] = None


@router.get("/config")
async def get_config() -> Dict[str, Any]:
    """获取配置

    Returns:
        配置信息
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        config = assistant.config

        safe_config = {
            "llm": {
                "provider": config.get("llm", {}).get("provider"),
                "base_url": config.get("llm", {}).get("base_url"),
                "max_tokens": config.get("llm", {}).get("max_tokens"),
                "temperature": config.get("llm", {}).get("temperature"),
                "timeout": config.get("llm", {}).get("timeout"),
                "models": config.get("llm", {}).get("models", {}),
                "default_model": config.get("llm", {}).get("default_model")
            },
            "task_classification": config.get("task_classification", {}),
            "execution_mode": config.get("execution_mode", {}),
            "skill_call": config.get("skill_call", {}),
            "session": config.get("session", {}),
            "logging": config.get("logging", {}),
            "system": config.get("system", {}),
            "web": config.get("web", {})
        }

        return safe_config
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.put("/config")
async def update_config(request: ConfigUpdateRequest) -> Dict[str, Any]:
    """更新配置

    Args:
        request: 配置更新请求数据

    Returns:
        更新结果
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        config = assistant.config
        updated_sections = []

        if request.llm:
            for key, value in request.llm.items():
                if key != "api_key":
                    config["llm"][key] = value
            updated_sections.append("llm")

        if request.task_classification:
            config["task_classification"].update(request.task_classification)
            updated_sections.append("task_classification")

        if request.execution_mode:
            config["execution_mode"].update(request.execution_mode)
            updated_sections.append("execution_mode")

        if request.skill_call:
            config["skill_call"].update(request.skill_call)
            updated_sections.append("skill_call")

        if request.session:
            config["session"].update(request.session)
            updated_sections.append("session")

        if request.logging:
            config["logging"].update(request.logging)
            updated_sections.append("logging")

        return {
            "success": True,
            "message": "配置已更新，部分配置需要重启服务生效",
            "updated_sections": updated_sections
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@router.get("/config/sections")
async def get_config_sections() -> Dict[str, Any]:
    """获取配置区块列表

    Returns:
        配置区块列表
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        config = assistant.config

        sections = {
            "llm": {
                "description": "LLM配置",
                "keys": list(config.get("llm", {}).keys())
            },
            "task_classification": {
                "description": "任务分类配置",
                "keys": list(config.get("task_classification", {}).keys())
            },
            "execution_mode": {
                "description": "执行模式配置",
                "keys": list(config.get("execution_mode", {}).keys())
            },
            "skill_call": {
                "description": "技能调用配置",
                "keys": list(config.get("skill_call", {}).keys())
            },
            "session": {
                "description": "会话配置",
                "keys": list(config.get("session", {}).keys())
            },
            "logging": {
                "description": "日志配置",
                "keys": list(config.get("logging", {}).keys())
            },
            "system": {
                "description": "系统配置",
                "keys": list(config.get("system", {}).keys())
            },
            "web": {
                "description": "Web服务配置",
                "keys": list(config.get("web", {}).keys())
            }
        }

        return {
            "sections": sections
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取配置区块失败: {str(e)}")


@router.get("/config/validate")
async def validate_config() -> Dict[str, Any]:
    """验证配置

    Returns:
        验证结果
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        config = assistant.config
        validation_results = []

        llm_config = config.get("llm", {})
        if not llm_config.get("provider"):
            validation_results.append({
                "section": "llm",
                "field": "provider",
                "status": "error",
                "message": "LLM提供商未配置"
            })
        else:
            validation_results.append({
                "section": "llm",
                "field": "provider",
                "status": "ok",
                "message": f"LLM提供商: {llm_config.get('provider')}"
            })

        if not llm_config.get("api_key"):
            validation_results.append({
                "section": "llm",
                "field": "api_key",
                "status": "warning",
                "message": "API密钥未配置，请设置环境变量或配置文件"
            })
        else:
            validation_results.append({
                "section": "llm",
                "field": "api_key",
                "status": "ok",
                "message": "API密钥已配置"
            })

        session_config = config.get("session", {})
        db_path = session_config.get("db_path")
        if db_path:
            validation_results.append({
                "section": "session",
                "field": "db_path",
                "status": "ok",
                "message": f"数据库路径: {db_path}"
            })
        else:
            validation_results.append({
                "section": "session",
                "field": "db_path",
                "status": "warning",
                "message": "数据库路径未配置，将使用默认路径"
            })

        error_count = sum(1 for r in validation_results if r["status"] == "error")
        warning_count = sum(1 for r in validation_results if r["status"] == "warning")

        return {
            "valid": error_count == 0,
            "error_count": error_count,
            "warning_count": warning_count,
            "results": validation_results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"验证配置失败: {str(e)}")
