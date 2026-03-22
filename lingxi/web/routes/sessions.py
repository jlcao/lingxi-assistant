from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from lingxi.web.state import get_assistant
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class CreateSessionRequest(BaseModel):
    """创建会话请求模型"""
    userName: Optional[str] = None
    user_name: Optional[str] = None  # 兼容 snake_case 格式
    workspace_path: Optional[str] = None  # 工作目录路径
    
    class Config:
        # 允许使用别名
        populate_by_name = True


class UpdateSessionRequest(BaseModel):
    """更新会话请求模型"""
    title: str


class SessionResponse(BaseModel):
    """会话响应模型"""
    session_id: str
    first_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SessionHistoryResponse(BaseModel):
    """会话历史响应模型"""
    session_id: str
    history: List[Dict[str, Any]]


@router.get("/sessions")
async def get_sessions(workspace_path: Optional[str] = None) -> Dict[str, Any]:
    """获取所有会话列表（支持按工作目录过滤）

    Args:
        workspace_path: 工作目录路径（可选）

    Returns:
        会话列表
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        # 如果指定了工作目录路径，返回该工作目录的会话
        if workspace_path:
            sessions = assistant.session_manager.list_all_sessions(workspace_path)
        else:
            # 否则返回所有会话
            sessions = assistant.session_manager.list_all_sessions()
        
        return {"sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话列表失败：{str(e)}")


@router.post("/sessions")
async def create_session(request: CreateSessionRequest) -> Dict[str, Any]:
    """创建新会话

    Args:
        request: 创建会话请求

    Returns:
        新创建的会话信息
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        import uuid
        from lingxi.management.workspace_manager import get_workspace_manager
        
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        # 兼容 userName 和 user_name 字段
        user_name = request.userName if request.userName else (request.user_name if request.user_name else "新会话")
        
        # 优先使用前端传递的工作目录路径
        workspace_path = request.workspace_path
        if not workspace_path:
            # 如果前端没有传递，从 workspace_manager 获取
            try:
                workspace_manager = get_workspace_manager()
                current_workspace = workspace_manager.get_current_workspace()
                if current_workspace:
                    workspace_path = str(current_workspace)
                    logger.debug(f"创建会话时的工作目录：{workspace_path}")
            except Exception as e:
                logger.warning(f"获取工作目录失败，将不关联工作目录：{e}")
        
        # 使用 create_session_by_id 方法，传入 session_id、user_name 和 workspace_path
        assistant.session_manager.create_session_by_id(session_id, user_name, workspace_path=workspace_path)
        
        return {
            "sessionId": session_id,
            "firstMessage": user_name
        }
    except Exception as e:
        logger.error(f"创建会话失败：{e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建会话失败：{str(e)}")


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> Dict[str, Any]:
    """获取会话详情

    Args:
        session_id: 会话 ID

    Returns:
        会话详情
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        info = assistant.session_manager.get_session_info_for_frontend(session_id)
        if not info:
            raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")
        return info
    except HTTPException:
        logger.error(f"获取会话详情失败：{session_id}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"获取会话详情失败：{session_id}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取会话详情失败：{str(e)}")


@router.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str, max_turns: int = 20) -> Dict[str, Any]:
    """获取会话历史

    Args:
        session_id: 会话 ID
        max_turns: 最大返回轮数

    Returns:
        会话历史
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        history = assistant.session_manager.get_history(session_id)
        if history is None:
            raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")

        return {
            "session_id": session_id,
            "history": history
        }
    except HTTPException:
        logger.error(f"获取会话历史失败：{session_id}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"获取会话历史失败：{session_id}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取会话历史失败：{str(e)}")


@router.patch("/sessions/{session_id}")
async def update_session(session_id: str, request: UpdateSessionRequest) -> Dict[str, Any]:
    """更新会话（重命名）

    Args:
        session_id: 会话 ID
        request: 更新请求

    Returns:
        更新结果
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        success = assistant.session_manager.rename_session(session_id, request.title)
        if not success:
            raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")
        return {"success": True, "message": f"会话已重命名为：{request.title}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新会话失败：{str(e)}")


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> Dict[str, Any]:
    """删除会话

    Args:
        session_id: 会话 ID

    Returns:
        删除结果
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        success = assistant.session_manager.delete_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")
        return {"success": True, "message": f"会话已删除：{session_id}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除会话失败：{str(e)}")


@router.delete("/sessions/{session_id}/history")
async def clear_session_history(session_id: str) -> Dict[str, Any]:
    """清空会话历史

    Args:
        session_id: 会话 ID

    Returns:
        清空结果
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        assistant.session_manager.clear_session_history(session_id)
        return {"success": True, "message": f"会话历史已清空：{session_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清空会话历史失败：{str(e)}")
