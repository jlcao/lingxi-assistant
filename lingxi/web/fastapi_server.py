import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from lingxi.utils.config import load_config
from lingxi.utils.logging import setup_logging
from lingxi.web.routes import tasks, checkpoints, skills, config as config_router, sessions, workspace
from lingxi.web.state import set_assistant, get_assistant, get_websocket_manager
from lingxi.core.event.SessionStore_subscriber import SessionStoreSubscriber
from lingxi.core.assistant.async_main import AsyncLingxiAssistant

def get_config():
    """获取配置
    
    Returns:
        系统配置
    """
    return load_config()

logger = logging.getLogger(__name__)

app = FastAPI(
    title="灵犀智能助手",
    description="基于FastAPI和流式响应的智能助手服务（V4.0）",
    version="4.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 确保路由在模块加载时就注册
app.include_router(tasks.router, prefix="/api", tags=["tasks"])
app.include_router(checkpoints.router, prefix="/api", tags=["checkpoints"])
app.include_router(skills.router, prefix="/api", tags=["skills"])
app.include_router(config_router.router, prefix="/api", tags=["config"])
app.include_router(sessions.router, prefix="/api", tags=["sessions"])
app.include_router(workspace.router, prefix="/api", tags=["workspace"])

# 可选的 resources 路由（如果 psutil 可用）
try:
    from lingxi.web.routes import resources
    if resources is not None:
        app.include_router(resources.router, prefix="/api", tags=["resources"])
except ImportError:
    logger.warning("psutil 模块未安装，resources 路由将不可用")


@app.on_event("startup")
async def startup_event():
    """FastAPI 启动事件"""
    config = get_config()
    setup_logging(config)

    # 检查助手是否已初始化（由 start_web_server.py 创建）
    assistant = get_assistant()
    if assistant is None:
        # 如果未初始化，则创建异步助手实例
        assistant = AsyncLingxiAssistant(config)
        set_assistant(assistant)
        
        # 初始化会话存储事件订阅者（延迟初始化）
        assistant.init_session_store_subscriber()
        logger.info("创建新的异步助手实例")
    else:
        logger.info("使用已初始化的助手实例")
        # 修复：确保现有实例的资源引用已完整设置
        if hasattr(assistant, 'skill_caller') and hasattr(assistant.skill_caller, 'workspace_manager'):
            workspace_manager = assistant.skill_caller.workspace_manager
            if workspace_manager:
                workspace_manager.set_resources(
                    sandbox=assistant.skill_caller.sandbox,
                    skill_caller=assistant.skill_caller,
                    session_store=assistant.session_manager if hasattr(assistant, 'session_manager') else None
                )
                logger.info("已修复现有实例的 workspace_manager 资源引用（sandbox、skill_caller、session_store）")
        
        # 确保会话存储订阅者已初始化
        assistant.init_session_store_subscriber()

    logger.info("初始化 FastAPI 服务器")
    logger.info(f"服务器配置：host={config.get('web', {}).get('host')}, port={config.get('web', {}).get('port')}")


def init_app(config=None):
    """初始化FastAPI应用

    Args:
        config: 系统配置
    """
    # 这个函数现在主要用于向后兼容
    pass


@app.get("/api/status")
async def get_status():
    """获取服务器状态"""
    assistant = get_assistant()

    return {
        "status": "running",
        "assistant": assistant.config.get('system', {}).get('name', '灵犀') if assistant else None,
        "version": assistant.config.get('system', {}).get('version', '0.2.0') if assistant else None
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, sessionId: str = None):
    """WebSocket 端点
    
    Args:
        websocket: WebSocket 连接
        sessionId: 会话 ID（从查询参数获取）
    """
    websocket_manager = get_websocket_manager()
    if not websocket_manager:
        await websocket.close(code=1011, reason="WebSocket 管理器未初始化")
        return

    # 接受连接
    await websocket.accept()
    
    # 创建连接并传递 sessionId
    connection_id = await websocket_manager.connect(websocket, sessionId)

    try:
        while True:
            data = await websocket.receive_json()
            await websocket_manager.handle_message(connection_id, data)
    except WebSocketDisconnect:
        await websocket_manager.disconnect(connection_id)
    except Exception as e:
        logger.error(f"WebSocket 连接错误：{e}", exc_info=True)
        await websocket_manager.disconnect(connection_id)


def run_server(config=None):
    """启动FastAPI服务器

    Args:
        config: 系统配置或配置文件路径
    """
    import uvicorn

    if not config:
        config = load_config()
    elif isinstance(config, str):
        config = load_config(config)

    init_app(config)

    web_config = config.get('web', {})
    host = web_config.get('host', 'localhost')
    port = web_config.get('port', 5000)

    logger.info(f"启动FastAPI服务器: http://{host}:{port}")

    uvicorn.run(
        "lingxi.web.fastapi_server:app",
        host=host,
        port=port,
        reload=web_config.get('debug', False)
    )


if __name__ == '__main__':
    run_server()
