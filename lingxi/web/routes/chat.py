from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from lingxi.web.state import get_assistant
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    session_id: Optional[str] = "default"


class ChatResponse(BaseModel):
    """聊天响应模型"""
    response: str
    session_id: str


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> Dict[str, Any]:
    """聊天API
    
    Args:
        request: 聊天请求数据
    
    Returns:
        聊天响应
    """
    assistant = get_assistant()
    if not assistant:
        raise HTTPException(status_code=503, detail="助手服务未初始化")

    try:
        message = request.message
        session_id = request.session_id
        
        if not message:
            raise HTTPException(status_code=400, detail="缺少消息内容")
        
        # 处理消息
        response = assistant.process_input(message, session_id)
        
        return {
            "response": response,
            "session_id": session_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health() -> Dict[str, Any]:
    """健康检查
    
    Returns:
        健康状态
    """
    return {
        "status": "healthy",
        "service": "lingxi-web"
    }
