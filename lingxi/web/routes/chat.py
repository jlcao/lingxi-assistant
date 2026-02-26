from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from lingxi.web.state import get_assistant
import uuid

router = APIRouter()


class CreateSessionRequest(BaseModel):
    """创建会话请求模型"""
    user_name: str = "default"


class SessionInfo(BaseModel):
    """会话信息模型"""
    session_id: str
    user_name: str
    created_at: str
    updated_at: str


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    """聊天响应模型"""
    response: str
    session_id: str


class RenameSessionRequest(BaseModel):
    """重命名会话请求模型"""
    name: str


@router.post("/sessions", response_model=SessionInfo)
async def create_session(request: CreateSessionRequest) -> Dict[str, Any]:
    """创建会话

    Args:
        request: 创建会话请求数据

    Returns:
        会话信息
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        session_id = assistant.session_manager.create_session(request.user_name)
        session_info = assistant.session_manager.get_session_info(session_id)

        return {
            "session_id": session_id,
            "user_name": session_info.get("user_name", request.user_name),
            "created_at": session_info.get("created_at", ""),
            "updated_at": session_info.get("updated_at", "")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}")


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> Dict[str, Any]:
    """获取会话详情

    Args:
        session_id: 会话ID

    Returns:
        会话详情
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        session_info = assistant.session_manager.get_session_info(session_id)
        if not session_info:
            raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")

        return session_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话详情失败: {str(e)}")


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> Dict[str, Any]:
    """聊天API

    Args:
        request: 聊天请求数据

    Returns:
        聊天响应数据
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        if not request.message:
            raise HTTPException(status_code=400, detail="消息内容不能为空")

        response = assistant.process_input(request.message, request.session_id)

        return {
            "response": response,
            "session_id": request.session_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理消息失败: {str(e)}")


@router.get("/sessions/{session_id}/history")
async def get_history(session_id: str, max_turns: int = 20) -> Dict[str, Any]:
    """获取会话历史

    Args:
        session_id: 会话ID
        max_turns: 最大返回轮次

    Returns:
        会话历史
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        history = assistant.session_manager.get_history(session_id, max_turns)
        return {
            "session_id": session_id,
            "history": history,
            "count": len(history)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史失败: {str(e)}")


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> Dict[str, Any]:
    """删除会话

    Args:
        session_id: 会话ID

    Returns:
        操作结果
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        success = assistant.session_manager.delete_session(session_id)
        if success:
            return {
                "success": True,
                "message": f"会话 {session_id} 已删除"
            }
        else:
            raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}")


@router.patch("/sessions/{session_id}")
async def rename_session(session_id: str, request: RenameSessionRequest) -> Dict[str, Any]:
    """重命名会话

    Args:
        session_id: 会话ID
        request: 重命名会话请求数据

    Returns:
        操作结果
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        new_title = request.name
        if not new_title or not new_title.strip():
            raise HTTPException(status_code=400, detail="标题不能为空")

        success = assistant.session_manager.rename_session(session_id, new_title.strip())
        if success:
            return {
                "success": True,
                "message": f"会话已重命名为: {new_title}"
            }
        else:
            raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重命名会话失败: {str(e)}")


@router.get("/sessions")
async def list_sessions() -> Dict[str, Any]:
    """获取所有会话列表

    Returns:
        会话列表
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        sessions = assistant.session_manager.list_all_sessions()
        return {
            "success": True,
            "sessions": sessions,
            "count": len(sessions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取会话列表失败: {str(e)}")


@router.delete("/sessions/{session_id}/history")
async def clear_session_history(session_id: str) -> Dict[str, Any]:
    """清除会话历史记录

    Args:
        session_id: 会话ID

    Returns:
        操作结果
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        assistant.session_manager.clear_session_history(session_id)
        return {
            "success": True,
            "message": f"会话 {session_id} 的历史记录已清除"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清除历史记录失败: {str(e)}")
