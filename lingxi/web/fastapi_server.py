import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from lingxi.__main__ import LingxiAssistant
from lingxi.utils.config import load_config
from lingxi.utils.logging import setup_logging
from lingxi.web.websocket import WebSocketManager
from lingxi.web.routes import chat, health, tasks, checkpoints, skills, resources, config as config_router
from lingxi.web.state import set_assistant, set_websocket_manager, get_assistant, get_websocket_manager
from lingxi.core.event.websocket_subscriber import WebSocketSubscriber

logger = logging.getLogger(__name__)

app = FastAPI(
    title="灵犀智能助手",
    description="基于FastAPI和WebSocket的智能助手服务",
    version="0.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def init_app(config=None):
    """初始化FastAPI应用

    Args:
        config: 系统配置
    """
    if not config:
        config = get_config()

    setup_logging(config)

    assistant = LingxiAssistant(config)
    websocket_manager = WebSocketManager(assistant)
    
    # 初始化WebSocket事件订阅者
    websocket_subscriber = WebSocketSubscriber(websocket_manager)

    set_assistant(assistant)
    set_websocket_manager(websocket_manager)

    app.include_router(chat.router, prefix="/api", tags=["chat"])
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(tasks.router, prefix="/api", tags=["tasks"])
    app.include_router(checkpoints.router, prefix="/api", tags=["checkpoints"])
    app.include_router(skills.router, prefix="/api", tags=["skills"])
    app.include_router(resources.router, prefix="/api", tags=["resources"])
    app.include_router(config_router.router, prefix="/api", tags=["config"])

    try:
        app.mount("/static", StaticFiles(directory="lingxi/web/static"), name="static")
    except RuntimeError:
        logger.warning("静态文件目录不存在，跳过静态文件服务")

    logger.info("初始化FastAPI服务器")
    logger.info(f"服务器配置: host={config.get('web', {}).get('host')}, port={config.get('web', {}).get('port')}")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点"""
    websocket_manager = get_websocket_manager()
    if not websocket_manager:
        await websocket.close(code=1011, reason="服务器未初始化")
        return

    connection_id = await websocket_manager.connect(websocket)
    logger.info(f"WebSocket连接建立: {connection_id}")

    try:
        while True:
            try:
                data = await websocket.receive_json()
                await websocket_manager.handle_message(connection_id, data)
            except WebSocketDisconnect as e:
                logger.info(f"WebSocket连接断开: {connection_id}, code: {e.code}")
                break
            except Exception as e:
                logger.error(f"处理消息时出错: {e}", exc_info=True)
                try:
                    error_msg = {
                        "type": "error",
                        "success": False,
                        "error": str(e)
                    }
                    await websocket.send_json(error_msg)
                except:
                    break
    except Exception as e:
        logger.error(f"WebSocket连接异常: {e}", exc_info=True)
    finally:
        await websocket_manager.disconnect(connection_id)


@app.get("/api/status")
async def get_status():
    """获取服务器状态"""
    assistant = get_assistant()
    websocket_manager = get_websocket_manager()

    return {
        "status": "running",
        "assistant": assistant.config.get('system', {}).get('name', '灵犀') if assistant else None,
        "version": assistant.config.get('system', {}).get('version', '0.2.0') if assistant else None,
        "connections": websocket_manager.get_connection_count() if websocket_manager else 0,
        "sessions": websocket_manager.get_session_count() if websocket_manager else 0
    }


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
    logger.info(f"WebSocket端点: ws://{host}:{port}/ws")
    logger.info(f"Web界面: http://{host}:{port}/static/index.html")

    uvicorn.run(
        "lingxi.web.fastapi_server:app",
        host=host,
        port=port,
        reload=web_config.get('debug', False)
    )


if __name__ == '__main__':
    run_server()
