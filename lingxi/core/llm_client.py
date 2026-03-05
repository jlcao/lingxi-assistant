import logging
import os
import re
import json
from typing import Dict, Optional, Any, List, Union, Generator, Tuple

class LLMClient:
    """LLM客户端，用于与大语言模型交互，支持上下文缓存"""

    def __init__(self, config: Dict[str, Any]):
        """初始化LLM客户端

        Args:
            config: 系统配置
        """
        self.config = config
        self.llm_config = config.get("llm", {})
        self.logger = logging.getLogger(__name__)

        self.provider = self.llm_config.get("provider", "openai")
        self.api_key = self.llm_config.get("api_key", "")
        self.model = self.llm_config.get("model", "gpt-4")
        self.temperature = self.llm_config.get("temperature", 0.7)
        self.max_tokens = self.llm_config.get("max_tokens", 2048)
        self.timeout = self.llm_config.get("timeout", 30)

        self.models_config = self.llm_config.get("models", {})
        self.default_model = self.llm_config.get("default_model", "qwen-plus")
        self.retry_count = self.llm_config.get("retry_count", 2)
        self.retry_delay = self.llm_config.get("retry_delay", 1)

        # 存储最近的 Token 使用信息
        self.last_usage = None

        self._init_client()

        self.logger.debug(f"初始化LLM客户端: {self.provider}")
        self.logger.debug(f"默认模型: {self.model}")
        self.logger.debug(f"模型分级配置: {list(self.models_config.keys())}")

    def _init_client(self):
        """初始化客户端"""
        if self.provider == "openai":
            from openai import OpenAI
            api_key = self.api_key
            base_url = self.llm_config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
            self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=self.timeout)

        elif self.provider == "dashscope":
            from openai import OpenAI
            api_key = self.api_key
            base_url = self.llm_config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
            self.client = OpenAI(api_key=api_key, base_url=base_url, timeout=self.timeout)

        elif self.provider == "azure":
            import openai
            openai.api_key = self.api_key
            openai.api_base = self.llm_config.get("base_url")
            self.client = openai

        elif self.provider == "google":
            self.client = None

        else:
            self.client = None

    def select_model(self, task_level: str) -> str:
        """根据任务级别选择模型

        Args:
            task_level: 任务级别（trivial/simple/complex）

        Returns:
            模型名称
        """
        if task_level in self.models_config:
            model_config = self.models_config[task_level]
            if isinstance(model_config, dict):
                model_name = model_config.get("model", self.default_model)
                self.logger.debug(f"任务级别: {task_level}, 选择模型: {model_name}")
                return model_name
            else:
                model_name = str(model_config)
                self.logger.debug(f"任务级别: {task_level}, 选择模型: {model_name}")
                return model_name
        self.logger.debug(f"任务级别: {task_level}, 使用默认模型: {self.default_model}")
        return self.default_model

    def get_model_config(self, task_level: str) -> Dict[str, Any]:
        """获取任务级别对应的模型配置

        Args:
            task_level: 任务级别

        Returns:
            模型配置字典
        """
        if task_level in self.models_config:
            config = self.models_config[task_level]
            if isinstance(config, dict):
                config = config.copy()
                config["model"] = config.get("model", self.default_model)
                return config
            else:
                return {"model": str(config)}
        return {"model": self.default_model}

    def complete(self, prompt: str, task_level: str = None, stream: bool = False, **kwargs) -> Union[str, Any]:
        """生成文本完成

        Args:
            prompt: 提示文本
            task_level: 任务级别（可选，用于选择模型）
            stream: 是否启用流式输出
            **kwargs: 其他参数

        Returns:
            生成的文本（非流式）或流式响应对象（流式）

        Raises:
            Exception: 当API调用失败时
        """
        self.logger.debug(f"生成完成: {prompt[:100]}... (stream={stream})")

        try:
            if self.provider == "openai":
                return self._openai_complete(prompt, task_level, stream=stream, **kwargs)
            elif self.provider == "dashscope":
                return self._dashscope_complete(prompt, task_level, stream=stream, **kwargs)
            elif self.provider == "azure":
                return self._azure_complete(prompt, task_level, stream=stream, **kwargs)
            elif self.provider == "google":
                return self._google_complete(prompt, task_level, stream=stream, **kwargs)
            else:
                return self._mock_complete(prompt, task_level, stream=stream, **kwargs)

        except Exception as e:
            self.logger.error(f"生成失败: {e}")
            # 直接抛出异常，让调用者处理
            raise

    def stream_complete(self, prompt: str, task_level: str = None, **kwargs) -> Any:
        """流式生成文本完成

        Args:
            prompt: 提示文本
            task_level: 任务级别（可选，用于选择模型）
            **kwargs: 其他参数

        Returns:
            流式响应对象

        Raises:
            Exception: 当API调用失败时
        """
        return self.complete(prompt, task_level, stream=True, **kwargs)

    def chat_complete(self, messages: List[Dict[str, str]], task_level: str = None, stream: bool = False, **kwargs) -> Union[str, Any]:
        """聊天完成

        Args:
            messages: 消息列表
            task_level: 任务级别（可选，用于选择模型）
            stream: 是否启用流式输出
            **kwargs: 其他参数

        Returns:
            生成的文本（非流式）或流式响应对象（流式）

        Raises:
            Exception: 当API调用失败时
        """
        self.logger.debug(f"聊天完成，消息数: {len(messages)} (stream={stream})")

        try:
            if self.provider == "openai":
                return self._openai_chat_complete(messages, task_level, stream=stream, **kwargs)
            elif self.provider == "dashscope":
                return self._dashscope_chat_complete(messages, task_level, stream=stream, **kwargs)
            elif self.provider == "azure":
                return self._azure_chat_complete(messages, task_level, stream=stream, **kwargs)
            elif self.provider == "google":
                return self._google_chat_complete(messages, task_level, stream=stream, **kwargs)
            else:
                return self._mock_chat_complete(messages, task_level, stream=stream, **kwargs)

        except Exception as e:
            self.logger.error(f"聊天完成失败: {e}")
            raise

    def stream_chat_complete(self, messages: List[Dict[str, str]], task_level: str = None, **kwargs) -> Any:
        """流式聊天完成

        Args:
            messages: 消息列表
            task_level: 任务级别（可选，用于选择模型）
            **kwargs: 其他参数

        Returns:
            流式响应对象

        Raises:
            Exception: 当API调用失败时
        """
        return self.chat_complete(messages, task_level, stream=True, **kwargs)

    def chat_complete_with_cache(self, messages: List[Union[Dict[str, str], Dict[str, Any]]], task_level: str = None, stream: bool = False, **kwargs) -> Union[str, Any, tuple]:
        """聊天完成（支持上下文缓存）

        Args:
            messages: 消息列表，支持带 cache_control 的结构化消息
            task_level: 任务级别（可选，用于选择模型）
            stream: 是否启用流式输出
            **kwargs: 其他参数

        Returns:
            生成的文本（非流式）或流式响应对象（流式）
            如果 stream=False，返回 (content, usage) 元组
            如果 stream=True，返回流式响应对象

        Raises:
            Exception: 当API调用失败时
        """
        self.logger.debug(f"聊天完成（带缓存），消息数: {len(messages)} (stream={stream})")

        try:
            if self.provider == "openai":
                result = self._openai_chat_complete_with_cache(messages, task_level, stream=stream, **kwargs)
            elif self.provider == "dashscope":
                result = self._dashscope_chat_complete_with_cache(messages, task_level, stream=stream, **kwargs)
            elif self.provider == "azure":
                result = self._azure_chat_complete_with_cache(messages, task_level, stream=stream, **kwargs)
            elif self.provider == "google":
                result = self._google_chat_complete_with_cache(messages, task_level, stream=stream, **kwargs)
            else:
                result = self._mock_chat_complete_with_cache(messages, task_level, stream=stream, **kwargs)

            # 如果不是流式模式，且返回的是元组，则提取 usage
            if not stream and isinstance(result, tuple):
                content, usage = result
                self.last_usage = usage
                return content

            return result

        except Exception as e:
            self.logger.error(f"聊天完成（带缓存）失败: {e}")
            raise

    def stream_chat_complete_with_cache(self, messages: List[Union[Dict[str, str], Dict[str, Any]]], task_level: str = None, **kwargs) -> Any:
        """流式聊天完成（支持上下文缓存）

        Args:
            messages: 消息列表，支持带 cache_control 的结构化消息
            task_level: 任务级别（可选，用于选择模型）
            **kwargs: 其他参数

        Returns:
            流式响应对象

        Raises:
            Exception: 当API调用失败时
        """
        return self.chat_complete_with_cache(messages, task_level, stream=True, **kwargs)
    
    def _openai_complete(self, prompt: str, task_level: str = None, stream: bool = False, **kwargs) -> Union[str, Any]:
        """使用OpenAI API生成完成

        Args:
            prompt: 提示文本
            task_level: 任务级别
            stream: 是否启用流式输出
            **kwargs: 其他参数

        Returns:
            生成的文本（非流式）或流式响应对象（流式）
        """
        import time
        from openai import APIError

        model = self.select_model(task_level) if task_level else self.model
        model_config = self.get_model_config(task_level) if task_level else {}

        # 构造消息
        messages = [
            {"role": "system", "content": "你是灵犀智能助手，一个聪明、友好的AI助手。"},
            {"role": "user", "content": prompt}
        ]
        
        # 打印提示词内容
        self.logger.debug(f"发送提示词到模型 {model}: \n" + "\n".join([f"{msg['role']}: {msg['content'][:500]}{'...' if len(msg['content']) > 500 else ''}" for msg in messages]))

        # 检查是否需要JSON格式输出
        response_format = kwargs.get("response_format")
        
        last_error = None
        for attempt in range(self.retry_count + 1):
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=model_config.get("temperature", self.temperature),
                    max_tokens=model_config.get("max_tokens", self.max_tokens),
                    timeout=self.timeout,
                    stream=stream,
                    extra_body={
                        "enable_thinking": kwargs.get("enable_thinking", False)
                    },
                    stream_options=kwargs.get("stream_options", {"include_usage": True}) if stream else None,
                    response_format=response_format
                )

                if not stream:
                    return response.choices[0].message.content
                return response
            except APIError as e:
                last_error = e
                self.logger.warning(f"OpenAI API调用尝试 {attempt + 1}/{self.retry_count + 1} 失败: {e}")
                if attempt < self.retry_count:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise
            except Exception as e:
                last_error = e
                self.logger.warning(f"OpenAI API调用尝试 {attempt + 1}/{self.retry_count + 1} 失败: {e}")
                if attempt < self.retry_count:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise

        raise last_error if last_error else Exception("OpenAI API调用失败")

    def _dashscope_complete(self, prompt: str, task_level: str = None, stream: bool = False, **kwargs) -> Union[str, Any]:
        """使用阿里云百炼API生成完成

        Args:
            prompt: 提示文本
            task_level: 任务级别
            stream: 是否启用流式输出
            **kwargs: 其他参数

        Returns:
            生成的文本（非流式）或流式响应对象（流式）
        """
        import time
        from openai import APIError

        model = self.select_model(task_level) if task_level else self.model
        model_config = self.get_model_config(task_level) if task_level else {}

        # 构造消息
        messages = [
            {"role": "system", "content": "你是灵犀智能助手，一个聪明、友好的AI助手。"},
            {"role": "user", "content": prompt}
        ]
        
        # 打印提示词内容
        self.logger.debug(f"发送提示词到模型 {model}: \n" + "\n".join([f"{msg['role']}: {msg['content'][:500]}{'...' if len(msg['content']) > 500 else ''}" for msg in messages]))

        # 检查是否需要JSON格式输出
        response_format = kwargs.get("response_format")
        
        last_error = None
        for attempt in range(self.retry_count + 1):
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=model_config.get("temperature", self.temperature),
                    max_tokens=model_config.get("max_tokens", self.max_tokens),
                    timeout=self.timeout,
                    stream=stream,
                    extra_body={
                        "enable_thinking": kwargs.get("enable_thinking", False)
                    },
                    stream_options=kwargs.get("stream_options", {"include_usage": True}) if stream else None,
                    response_format=response_format
                )

                if not stream:
                    return response.choices[0].message.content
                return response
            except APIError as e:
                last_error = e
                self.logger.warning(f"Dashscope API调用尝试 {attempt + 1}/{self.retry_count + 1} 失败: {e}")
                if attempt < self.retry_count:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise
            except Exception as e:
                last_error = e
                self.logger.warning(f"Dashscope API调用尝试 {attempt + 1}/{self.retry_count + 1} 失败: {e}")
                if attempt < self.retry_count:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise

        raise last_error if last_error else Exception("Dashscope API调用失败")

    def _azure_complete(self, prompt: str, task_level: str = None, stream: bool = False, **kwargs) -> Union[str, Any]:
        """使用Azure OpenAI API生成完成

        Args:
            prompt: 提示文本
            task_level: 任务级别
            stream: 是否启用流式输出
            **kwargs: 其他参数

        Returns:
            生成的文本（非流式）或流式响应对象（流式）
        """
        import time
        from openai import APIError

        model = self.select_model(task_level) if task_level else self.model
        model_config = self.get_model_config(task_level) if task_level else {}

        # 构造消息
        messages = [
            {"role": "system", "content": "你是灵犀智能助手，一个聪明、友好的AI助手。"},
            {"role": "user", "content": prompt}
        ]
        
        # 打印提示词内容
        self.logger.debug(f"发送提示词到模型 {model}: \n" + "\n".join([f"{msg['role']}: {msg['content'][:500]}{'...' if len(msg['content']) > 500 else ''}" for msg in messages]))

        # 检查是否需要JSON格式输出
        response_format = kwargs.get("response_format")
        
        last_error = None
        for attempt in range(self.retry_count + 1):
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=model_config.get("temperature", self.temperature),
                    max_tokens=model_config.get("max_tokens", self.max_tokens),
                    timeout=self.timeout,
                    stream=stream,
                    stream_options=kwargs.get("stream_options", {"include_usage": True}) if stream else None,
                    response_format=response_format
                )

                if not stream:
                    return response.choices[0].message.content
                return response
            except APIError as e:
                last_error = e
                self.logger.warning(f"Azure API调用尝试 {attempt + 1}/{self.retry_count + 1} 失败: {e}")
                if attempt < self.retry_count:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise
            except Exception as e:
                last_error = e
                self.logger.warning(f"Azure API调用尝试 {attempt + 1}/{self.retry_count + 1} 失败: {e}")
                if attempt < self.retry_count:
                    time.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise

        raise last_error if last_error else Exception("Azure API调用失败")

    def _google_complete(self, prompt: str, task_level: str = None, stream: bool = False, **kwargs) -> Union[str, Any]:
        """使用Google Gemini API生成完成

        Args:
            prompt: 提示文本
            task_level: 任务级别
            stream: 是否启用流式输出
            **kwargs: 其他参数

        Returns:
            生成的文本（非流式）或流式响应对象（流式）
        """
        model = self.select_model(task_level) if task_level else self.model
        response = f"Google Gemini 响应 ({model}): " + prompt[:50]
        
        if not stream:
            return response
        # 模拟流式响应
        class MockStreamResponse:
            def __iter__(self):
                chunks = response.split(' ')
                for i, chunk in enumerate(chunks):
                    yield type('MockChunk', (), {
                        'choices': [type('MockChoice', (), {
                            'delta': type('MockDelta', (), {
                                'content': chunk + (' ' if i < len(chunks)-1 else ''),
                                'reasoning_content': None
                            })()
                        })()]
                    })()
        return MockStreamResponse()

    def _mock_complete(self, prompt: str, task_level: str = None, stream: bool = False, **kwargs) -> Union[str, Any]:
        """模拟LLM响应，用于测试

        Args:
            prompt: 提示文本
            task_level: 任务级别
            stream: 是否启用流式输出
            **kwargs: 其他参数

        Returns:
            模拟的响应（非流式）或流式响应对象（流式）
        """
        self.logger.warning("使用模拟LLM响应")

        model = self.select_model(task_level) if task_level else self.model

        if "分类" in prompt:
            response = f'''
            {{
                "task_type": "信息查询",
                "confidence": 0.9,
                "description": "用户查询信息",
                "model": "{model}"
            }}
            '''
        else:
            response = f"这是一个模拟的LLM响应（使用模型：{model}）。在实际使用中，这里会调用真实的LLM API。"
        
        if not stream:
            return response
        # 模拟流式响应
        class MockStreamResponse:
            def __iter__(self):
                chunks = response.split(' ')
                for i, chunk in enumerate(chunks):
                    yield type('MockChunk', (), {
                        'choices': [type('MockChoice', (), {
                            'delta': type('MockDelta', (), {
                                'content': chunk + (' ' if i < len(chunks)-1 else ''),
                                'reasoning_content': None
                            })()
                        })()]
                    })()
        return MockStreamResponse()

    def _openai_chat_complete(self, messages: List[Dict[str, str]], task_level: str = None, stream: bool = False, **kwargs) -> Union[str, Any]:
        """使用OpenAI API聊天完成

        Args:
            messages: 消息列表
            task_level: 任务级别
            stream: 是否启用流式输出
            **kwargs: 其他参数

        Returns:
            生成的文本（非流式）或流式响应对象（流式）
        """
        model = self.select_model(task_level) if task_level else self.model
        model_config = self.get_model_config(task_level) if task_level else {}

        # 打印提示词内容
        self.logger.debug(f"发送提示词到模型 {model}: \n" + "\n".join([f"{msg['role']}: {msg['content'][:500]}{'...' if len(msg['content']) > 500 else ''}" for msg in messages]))

        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=model_config.get("temperature", kwargs.get("temperature", self.temperature)),
            max_tokens=model_config.get("max_tokens", kwargs.get("max_tokens", self.max_tokens)),
            timeout=kwargs.get("timeout", self.timeout),
            stream=stream,
            extra_body={
                "enable_thinking": kwargs.get("enable_thinking", False)
            },
            stream_options=kwargs.get("stream_options", {"include_usage": True}) if stream else None
        )

        if not stream:
            return response.choices[0].message.content
        return response

    def _openai_chat_complete_with_cache(self, messages: List[Union[Dict[str, str], Dict[str, Any]]], task_level: str = None, stream: bool = False, **kwargs) -> Union[str, Any, tuple]:
        """使用OpenAI API聊天完成（支持上下文缓存）

        Args:
            messages: 消息列表，支持带 cache_control 的结构化消息
            task_level: 任务级别
            stream: 是否启用流式输出
            **kwargs: 其他参数

        Returns:
            生成的文本（非流式）或流式响应对象（流式）
            如果 stream=False，返回 (content, usage) 元组
            如果 stream=True，返回流式响应对象
        """
        model = self.select_model(task_level) if task_level else self.model
        model_config = self.get_model_config(task_level) if task_level else {}

        # 打印提示词内容
        self.logger.debug(f"发送提示词到模型 {model}: \n" + "\n".join([f"{msg['role']}: {msg['content'][:500]}{'...' if len(msg['content']) > 500 else ''}" for msg in messages]))

        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=model_config.get("temperature", kwargs.get("temperature", self.temperature)),
            max_tokens=model_config.get("max_tokens", kwargs.get("max_tokens", self.max_tokens)),
            timeout=kwargs.get("timeout", self.timeout),
            stream=stream,
            extra_body={
                "enable_thinking": kwargs.get("enable_thinking", False)
            },
            stream_options=kwargs.get("stream_options", {"include_usage": True}) if stream else None

        )

        if not stream:
            content = response.choices[0].message.content
            usage = response.usage if hasattr(response, 'usage') else None
            if usage:
                self.logger.debug(f"Token 使用: input={usage.prompt_tokens}, output={usage.completion_tokens}, total={usage.total_tokens}")
            return (content, usage)
        return response

    def _dashscope_chat_complete(self, messages: List[Dict[str, str]], task_level: str = None, stream: bool = False, **kwargs) -> Union[str, Any]:
        """使用阿里云百炼API聊天完成

        Args:
            messages: 消息列表
            task_level: 任务级别
            stream: 是否启用流式输出
            **kwargs: 其他参数

        Returns:
            生成的文本（非流式）或流式响应对象（流式）
        """
        model = self.select_model(task_level) if task_level else self.model
        model_config = self.get_model_config(task_level) if task_level else {}

        # 打印提示词内容
        self.logger.debug(f"发送提示词到模型 {model}: \n" + "\n".join([f"{msg['role']}: {msg['content'][:500]}{'...' if len(msg['content']) > 500 else ''}" for msg in messages]))

        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=model_config.get("temperature", kwargs.get("temperature", self.temperature)),
            max_tokens=model_config.get("max_tokens", kwargs.get("max_tokens", self.max_tokens)),
            timeout=kwargs.get("timeout", self.timeout),
            stream=stream,
            extra_body={
                "enable_thinking": kwargs.get("enable_thinking", False)
            },
            stream_options=kwargs.get("stream_options", {"include_usage": True}) if stream else None
        )

        if not stream:
            return response.choices[0].message.content
        return response

    def _dashscope_chat_complete_with_cache(self, messages: List[Union[Dict[str, str], Dict[str, Any]]], task_level: str = None, stream: bool = False, **kwargs) -> Union[str, Any]:
        """使用阿里云百炼API聊天完成（支持上下文缓存）

        Args:
            messages: 消息列表，支持带 cache_control 的结构化消息
            task_level: 任务级别
            stream: 是否启用流式输出
            **kwargs: 其他参数

        Returns:
            生成的文本（非流式）或流式响应对象（流式）
        """
        model = self.select_model(task_level) if task_level else self.model
        model_config = self.get_model_config(task_level) if task_level else {}

        # 打印提示词内容
        self.logger.debug(f"发送提示词到模型 {model}: \n" + "\n".join([f"{msg['role']}: {msg['content'][:500]}{'...' if len(msg['content']) > 500 else ''}" for msg in messages]))

        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=model_config.get("temperature", kwargs.get("temperature", self.temperature)),
            max_tokens=model_config.get("max_tokens", kwargs.get("max_tokens", self.max_tokens)),
            timeout=kwargs.get("timeout", self.timeout),
            stream=stream,
            extra_body={
                "enable_thinking": kwargs.get("enable_thinking", False)
            },
            stream_options=kwargs.get("stream_options", {"include_usage": True}) if stream else None
        )

        if not stream:
            return response.choices[0].message.content
        return response

    def _azure_chat_complete(self, messages: List[Dict[str, str]], task_level: str = None, stream: bool = False, **kwargs) -> Union[str, Any]:
        """使用Azure OpenAI API聊天完成

        Args:
            messages: 消息列表
            task_level: 任务级别
            stream: 是否启用流式输出
            **kwargs: 其他参数

        Returns:
            生成的文本（非流式）或流式响应对象（流式）
        """
        model = self.select_model(task_level) if task_level else self.model
        model_config = self.get_model_config(task_level) if task_level else {}

        # 打印提示词内容
        self.logger.debug(f"发送提示词到模型 {model}: \n" + "\n".join([f"{msg['role']}: {msg['content'][:500]}{'...' if len(msg['content']) > 500 else ''}" for msg in messages]))

        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=model_config.get("temperature", kwargs.get("temperature", self.temperature)),
            max_tokens=model_config.get("max_tokens", kwargs.get("max_tokens", self.max_tokens)),
            timeout=kwargs.get("timeout", self.timeout),
            stream=stream,
            extra_body={
                "enable_thinking": kwargs.get("enable_thinking", False)
            },
            stream_options=kwargs.get("stream_options", {"include_usage": True}) if stream else None
        )

        if not stream:
            return response.choices[0].message.content
        return response

    def _azure_chat_complete_with_cache(self, messages: List[Union[Dict[str, str], Dict[str, Any]]], task_level: str = None, stream: bool = False, **kwargs) -> Union[str, Any]:
        """使用Azure OpenAI API聊天完成（支持上下文缓存）

        Args:
            messages: 消息列表，支持带 cache_control 的结构化消息
            task_level: 任务级别
            stream: 是否启用流式输出
            **kwargs: 其他参数

        Returns:
            生成的文本（非流式）或流式响应对象（流式）
        """
        model = self.select_model(task_level) if task_level else self.model
        model_config = self.get_model_config(task_level) if task_level else {}

        # 打印提示词内容
        self.logger.debug(f"发送提示词到模型 {model}: \n" + "\n".join([f"{msg['role']}: {msg['content'][:500]}{'...' if len(msg['content']) > 500 else ''}" for msg in messages]))

        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=model_config.get("temperature", kwargs.get("temperature", self.temperature)),
            max_tokens=model_config.get("max_tokens", kwargs.get("max_tokens", self.max_tokens)),
            timeout=kwargs.get("timeout", self.timeout),
            stream=stream,
            extra_body={
                "enable_thinking": kwargs.get("enable_thinking", False)
            },
            stream_options=kwargs.get("stream_options", {"include_usage": True}) if stream else None
        )

        if not stream:
            return response.choices[0].message.content
        return response

    def _google_chat_complete(self, messages: List[Dict[str, str]], task_level: str = None, stream: bool = False, **kwargs) -> Union[str, Any]:
        """使用Google Gemini API聊天完成

        Args:
            messages: 消息列表
            task_level: 任务级别
            stream: 是否启用流式输出
            **kwargs: 其他参数

        Returns:
            生成的文本（非流式）或流式响应对象（流式）
        """
        model = self.select_model(task_level) if task_level else self.model
        response = f"Google Gemini 聊天响应 ({model}): " + str(len(messages)) + " 条消息"
        
        if not stream:
            return response
        # 模拟流式响应
        class MockStreamResponse:
            def __iter__(self):
                chunks = response.split(' ')
                for i, chunk in enumerate(chunks):
                    yield type('MockChunk', (), {
                        'choices': [type('MockChoice', (), {
                            'delta': type('MockDelta', (), {
                                'content': chunk + (' ' if i < len(chunks)-1 else ''),
                                'reasoning_content': None
                            })()
                        })()]
                    })()
        return MockStreamResponse()

    def _google_chat_complete_with_cache(self, messages: List[Union[Dict[str, str], Dict[str, Any]]], task_level: str = None, stream: bool = False, **kwargs) -> Union[str, Any]:
        """使用Google Gemini API聊天完成（支持上下文缓存）

        Args:
            messages: 消息列表，支持带 cache_control 的结构化消息
            task_level: 任务级别
            stream: 是否启用流式输出
            **kwargs: 其他参数

        Returns:
            生成的文本（非流式）或流式响应对象（流式）
        """
        model = self.select_model(task_level) if task_level else self.model
        response = f"Google Gemini 聊天响应（带缓存） ({model}): " + str(len(messages)) + " 条消息"
        
        if not stream:
            return response
        # 模拟流式响应
        class MockStreamResponse:
            def __iter__(self):
                chunks = response.split(' ')
                for i, chunk in enumerate(chunks):
                    yield type('MockChunk', (), {
                        'choices': [type('MockChoice', (), {
                            'delta': type('MockDelta', (), {
                                'content': chunk + (' ' if i < len(chunks)-1 else ''),
                                'reasoning_content': None
                            })()
                        })()]
                    })()
        return MockStreamResponse()

    def _mock_chat_complete(self, messages: List[Dict[str, str]], task_level: str = None, stream: bool = False, **kwargs) -> Union[str, Any]:
        """模拟聊天完成，用于测试

        Args:
            messages: 消息列表
            task_level: 任务级别
            stream: 是否启用流式输出
            **kwargs: 其他参数

        Returns:
            模拟的响应（非流式）或流式响应对象（流式）
        """
        self.logger.warning("使用模拟聊天响应")

        model = self.select_model(task_level) if task_level else self.model

        last_message = messages[-1].get("content", "") if messages else ""

        if "分类" in last_message:
            response = f'''
            {{
                "task_type": "信息查询",
                "confidence": 0.9,
                "description": "用户查询信息",
                "model": "{model}"
            }}
            '''
        else:
            response = f"这是一个模拟的聊天响应（使用模型：{model}）。在实际使用中，这里会调用真实的LLM API。"
        
        if not stream:
            return response
        # 模拟流式响应
        class MockStreamResponse:
            def __iter__(self):
                chunks = response.split(' ')
                for i, chunk in enumerate(chunks):
                    yield type('MockChunk', (), {
                        'choices': [type('MockChoice', (), {
                            'delta': type('MockDelta', (), {
                                'content': chunk + (' ' if i < len(chunks)-1 else ''),
                                'reasoning_content': None
                            })()
                        })()]
                    })()
        return MockStreamResponse()

    def _mock_chat_complete_with_cache(self, messages: List[Union[Dict[str, str], Dict[str, Any]]], task_level: str = None, stream: bool = False, **kwargs) -> Union[str, Any]:
        """模拟聊天完成（带缓存），用于测试

        Args:
            messages: 消息列表，支持带 cache_control 的结构化消息
            task_level: 任务级别
            stream: 是否启用流式输出
            **kwargs: 其他参数

        Returns:
            模拟的响应（非流式）或流式响应对象（流式）
        """
        self.logger.warning("使用模拟聊天响应（带缓存）")

        model = self.select_model(task_level) if task_level else self.model

        last_message = messages[-1]
        if isinstance(last_message, dict):
            content = last_message.get("content", "")
            if isinstance(content, list) and len(content) > 0:
                content = content[0].get("text", "")
        else:
            content = ""

        if "分类" in content:
            response = f'''
            {{
                "task_type": "信息查询",
                "confidence": 0.9,
                "description": "用户查询信息",
                "model": "{model}"
            }}
            '''
        else:
            response = f"这是一个模拟的聊天响应（带缓存）（使用模型：{model}）。在实际使用中，这里会调用真实的LLM API。"
        
        if not stream:
            return response
        # 模拟流式响应
        class MockStreamResponse:
            def __iter__(self):
                chunks = response.split(' ')
                for i, chunk in enumerate(chunks):
                    yield type('MockChunk', (), {
                        'choices': [type('MockChoice', (), {
                            'delta': type('MockDelta', (), {
                                'content': chunk + (' ' if i < len(chunks)-1 else ''),
                                'reasoning_content': None
                            })()
                        })()]
                    })()
        return MockStreamResponse()