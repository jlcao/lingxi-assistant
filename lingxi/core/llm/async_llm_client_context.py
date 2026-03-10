"""异步 LLM 客户端上下文管理器模块"""

from typing import Dict, Any
from .async_llm_client import AsyncLLMClient


class AsyncLLMClientContext:
    """异步 LLM 客户端上下文管理器"""

    def __init__(self, config: Dict[str, Any]):
        self.client = AsyncLLMClient(config)

    async def __aenter__(self) -> AsyncLLMClient:
        return self.client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.close()
