"""异步 LLM 客户端模块

使用 httpx/aiohttp 实现异步 HTTP 请求，彻底解决阻塞问题
"""

import asyncio
import logging
import os
import json
from typing import Dict, Optional, Any, List, Union, AsyncGenerator
import httpx


class AsyncLLMClient:
    """异步 LLM 客户端，用于与大语言模型交互（单例模式）"""
    
    _instance = None  # 单例实例
    
    def __new__(cls, config: Dict[str, Any]):
        """单例模式：确保只创建一个实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config: Dict[str, Any]):
        # 防止重复初始化
        if hasattr(self, '_initialized'):
            return
        
        """初始化异步 LLM 客户端

        Args:
            config: 系统配置
        """
        self.config = config
        self.llm_config = config.get("llm", {})
        self.logger = logging.getLogger(__name__)

        self.provider = self.llm_config.get("provider", "openai")
        self.api_key = os.getenv("DASHSCOPE_API_KEY") or self.llm_config.get("api_key", "")
        self.model = self.llm_config.get("model", "gpt-4")
        self.temperature = self.llm_config.get("temperature", 0.7)
        self.max_tokens = self.llm_config.get("max_tokens", 2048)
        self.timeout = self.llm_config.get("timeout", 30)

        self.models_config = self.llm_config.get("models", {})
        self.default_model = self.llm_config.get("default_model", "qwen3.5-plus")
        self.retry_count = self.llm_config.get("retry_count", 2)
        self.retry_delay = self.llm_config.get("retry_delay", 1)

        # 异步 HTTP 客户端
        self.http_client: Optional[httpx.AsyncClient] = None

        # 存储最近的 Token 使用信息
        self.last_usage = None

        self.logger.debug(f"初始化异步 LLM 客户端：{self.provider}")
        self.logger.debug(f"默认模型：{self.model}")
        self._initialized = True

    async def _ensure_client(self) -> httpx.AsyncClient:
        """确保 HTTP 客户端已创建"""
        if self.http_client is None or self.http_client.is_closed:
            self.http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout, connect=10.0),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
        return self.http_client

    def select_model(self, task_level: str) -> str:
        """根据任务级别选择模型"""
        if task_level in self.models_config:
            model_config = self.models_config[task_level]
            if isinstance(model_config, dict):
                return model_config.get("model", self.default_model)
            else:
                return str(model_config)
        return self.default_model

    async def close(self):
        """关闭 HTTP 客户端"""
        if self.http_client and not self.http_client.is_closed:
            await self.http_client.aclose()

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        task_level: str = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式聊天

        Args:
            messages: 消息列表
            task_level: 任务级别
            **kwargs: 其他参数

        Yields:
            流式响应块
        """
        model = self.select_model(task_level) if task_level else self.model
        client = await self._ensure_client()

        payload = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "stream": True,
            "stream_options": {"include_usage": True,"include_thought": kwargs.get("enable_thinking", False)}
        }

        # 添加额外参数
        if "enable_thinking" in kwargs:
            payload["extra_body"] = {"enable_thinking": kwargs["enable_thinking"]}

        last_error = None
        for attempt in range(self.retry_count + 1):
            try:
                url = self._get_api_url()
                async with client.stream('POST', url, json=payload) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        raise Exception(f"API 错误：{response.status_code} - {error_text.decode()}")

                    async for line in response.aiter_lines():
                        if line.startswith('data: '):
                            data = line[6:]
                            if data.strip() == '[DONE]':
                                break
                            try:
                                chunk = json.loads(data)
                                yield chunk
                            except json.JSONDecodeError:
                                continue
                return  # 成功完成

            except httpx.HTTPError as e:
                last_error = e
                self.logger.warning(f"HTTP 请求失败 (尝试 {attempt + 1}/{self.retry_count + 1})：{e}")
                if attempt < self.retry_count:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise
            except Exception as e:
                last_error = e
                self.logger.warning(f"请求失败 (尝试 {attempt + 1}/{self.retry_count + 1})：{e}")
                if attempt < self.retry_count:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise

        raise last_error if last_error else Exception("异步 LLM 调用失败")

    def _get_api_url(self) -> str:
        """获取 API URL"""
        if self.provider in ["openai", "dashscope"]:
            base_url = self.llm_config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
            return f"{base_url}/chat/completions"
        elif self.provider == "azure":
            base_url = self.llm_config.get("base_url")
            return f"{base_url}/openai/deployments/{self.model}/chat/completions?api-version=2023-05-15"
        else:
            raise ValueError(f"不支持的提供商：{self.provider}")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        task_level: str = None,
        **kwargs
    ) -> str:
        """非流式聊天

        Args:
            messages: 消息列表
            task_level: 任务级别
            **kwargs: 其他参数

        Returns:
            生成的文本
        """
        content = ""
        async for chunk in self.stream_chat(messages, task_level, **kwargs):
            choices = chunk.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                if "content" in delta:
                    content += delta["content"]

                # 收集 usage 信息
                if "usage" in chunk:
                    self.last_usage = chunk["usage"]

        return content
