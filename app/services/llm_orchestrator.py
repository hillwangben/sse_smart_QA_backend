"""
LLM 编排模块 - 处理多模态大模型调用。

本模块负责管理与多种 LLM 提供商（OpenAI、Anthropic、Ollama）的交互，
支持文本生成、流式响应和多模态（图片）输入。
"""
import os
import json
from typing import Any
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from app.core.llm_config import llm_config, ProviderConfig


class LLMProvider:
    """
    LLM 提供商基类。

    定义了所有 LLM 提供商必须实现的接口，包括文本生成、流式对话和多模态生成。

    Attributes:
        config (ProviderConfig): 提供商配置对象，包含 API 密钥、模型名称等参数。
    """

    def __init__(self, config: ProviderConfig):
        """
        初始化 LLM 提供商基类。

        Args:
            config (ProviderConfig): 提供商配置对象。
        """
        self.config = config

    async def generate_text(self, prompt: str, context: list[dict[str, Any]] | None = None) -> str:
        """
        生成文本响应（异步方法，由子类实现）。

        Args:
            prompt (str): 用户输入的提示文本。
            context (list[dict[str, Any]] | None): 对话历史上下文，格式为
                [{"role": "user/assistant", "content": "..."}]。

        Returns:
            str: 模型生成的文本响应。

        Raises:
            NotImplementedError: 子类必须实现此方法。
        """
        raise NotImplementedError

    async def chat_stream(self, prompt: str, context: list[dict[str, Any]] | None = None):
        """
        流式生成对话响应（异步生成器，由子类实现）。

        Args:
            prompt (str): 用户输入的提示文本。
            context (list[dict[str, Any]] | None): 对话历史上下文。

        Yields:
            流式响应块，格式因提供商而异。

        Raises:
            NotImplementedError: 子类必须实现此方法。
        """
        raise NotImplementedError

    async def generate_with_image(self, prompt: str, image_data: str) -> str:
        """
        基于图片和文本生成响应（多模态生成，由子类实现）。

        Args:
            prompt (str): 用户输入的提示文本。
            image_data (str): 图片数据，支持 base64 编码的 data URL 或图片 URL。

        Returns:
            str: 模型生成的文本响应。

        Raises:
            NotImplementedError: 子类必须实现此方法。
        """
        raise NotImplementedError


class OpenAIProvider(LLMProvider):
    """
    OpenAI API 提供商实现。

    支持 GPT-4、GPT-4o 等模型，提供文本生成、流式响应和多模态（图片理解）功能。

    Attributes:
        config (ProviderConfig): 提供商配置对象。
        client (AsyncOpenAI): OpenAI 异步客户端实例。
    """

    def __init__(self, config: ProviderConfig):
        """
        初始化 OpenAI 提供商。

        Args:
            config (ProviderConfig): 提供商配置，包含 api_key、base_url、model 等。
        """
        super().__init__(config)
        self.client = AsyncOpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url or None,
        )

    def _build_messages(self, prompt: str, context: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        """
        构建 OpenAI API 所需的消息格式。

        将历史上下文与当前用户输入合并为完整的消息列表。

        Args:
            prompt (str): 当前用户输入的提示文本。
            context (list[dict[str, Any]] | None): 对话历史上下文。

        Returns:
            list[dict[str, Any]]: OpenAI API 格式的消息列表，
                如 [{"role": "user", "content": "..."}, ...]。
        """
        messages = []
        if context:
            for msg in context:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": prompt})
        return messages

    async def generate_text(self, prompt: str, context: list[dict[str, Any]] | None = None) -> str:
        """
        异步生成文本响应。

        Args:
            prompt (str): 用户输入的提示文本。
            context (list[dict[str, Any]] | None): 对话历史上下文。

        Returns:
            str: 模型生成的文本响应，若生成失败则返回空字符串。
        """
        messages = self._build_messages(prompt, context)
        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )
        return response.choices[0].message.content or ""

    async def chat_stream(self, prompt: str, context: list[dict[str, Any]] | None = None):
        """
        异步流式生成对话响应。

        Args:
            prompt (str): 用户输入的提示文本。
            context (list[dict[str, Any]] | None): 对话历史上下文。

        Returns:
            AsyncStream: OpenAI 流式响应对象，可通过 async for 迭代获取响应块。
        """
        messages = self._build_messages(prompt, context)
        return await self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            stream=True,
        )

    async def generate_with_image(self, prompt: str, image_data: str) -> str:
        """
        基于图片和文本生成响应（多模态生成）。

        使用 GPT-4o 等视觉模型理解图片内容并生成文本响应。

        Args:
            prompt (str): 用户输入的提示文本，如"这张图片里有什么？"。
            image_data (str): 图片数据，支持格式：
                - base64 data URL: "data:image/jpeg;base64,..."
                - 图片 URL: "https://example.com/image.jpg"

        Returns:
            str: 模型生成的文本响应，若生成失败则返回空字符串。
        """
        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_data}},
                    ],
                }
            ],
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )
        return response.choices[0].message.content or ""


class AnthropicProvider(LLMProvider):
    """
    Anthropic API 提供商实现。

    支持 Claude 3 等模型，提供文本生成、流式响应和多模态（图片理解）功能。

    Attributes:
        config (ProviderConfig): 提供商配置对象。
        client (AsyncAnthropic): Anthropic 异步客户端实例。
    """

    def __init__(self, config: ProviderConfig):
        """
        初始化 Anthropic 提供商。

        Args:
            config (ProviderConfig): 提供商配置，包含 api_key、base_url、model 等。
        """
        super().__init__(config)
        self.client = AsyncAnthropic(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
        )

    def _build_messages(self, prompt: str, context: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        """
        构建 Anthropic API 所需的消息格式。

        将历史上下文与当前用户输入合并为完整的消息列表。

        Args:
            prompt (str): 当前用户输入的提示文本。
            context (list[dict[str, Any]] | None): 对话历史上下文。

        Returns:
            list[dict[str, Any]]: Anthropic API 格式的消息列表。
        """
        messages = []
        if context:
            for msg in context:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": prompt})
        return messages

    async def generate_text(self, prompt: str, context: list[dict[str, Any]] | None = None) -> str:
        """
        异步生成文本响应。

        Args:
            prompt (str): 用户输入的提示文本。
            context (list[dict[str, Any]] | None): 对话历史上下文。

        Returns:
            str: 模型生成的文本响应，若生成失败则返回空字符串。
        """
        messages = self._build_messages(prompt, context)
        response = await self.client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            messages=messages,
        )
        return response.content[0].text if response.content else ""

    async def chat_stream(self, prompt: str, context: list[dict[str, Any]] | None = None):
        """
        异步流式生成对话响应。

        注意：Anthropic 的流式响应格式与 OpenAI 不同，此方法会将其转换为兼容格式。

        Args:
            prompt (str): 用户输入的提示文本。
            context (list[dict[str, Any]] | None): 对话历史上下文。

        Yields:
            object: 模拟 OpenAI 格式的流式响应块，
                结构为 choices[0].delta.content。
        """
        messages = self._build_messages(prompt, context)
        async with self.client.messages.stream(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                # 将 Anthropic 流式响应转换为 OpenAI 兼容格式
                yield type('obj', (object,), {'choices': [type('obj', (object,), {'delta': type('obj', (object,), {'content': text})()})()]})()

    async def generate_with_image(self, prompt: str, image_data: str) -> str:
        """
        基于图片和文本生成响应（多模态生成）。

        使用 Claude 3 等视觉模型理解图片内容并生成文本响应。
        支持通过 base64 编码或 URL 传递图片。

        Args:
            prompt (str): 用户输入的提示文本。
            image_data (str): 图片数据，支持格式：
                - base64 data URL: "data:image/jpeg;base64,..."
                - 图片 URL: "https://example.com/image.jpg"

        Returns:
            str: 模型生成的文本响应，若生成失败则返回空字符串。
        """
        # Anthropic 支持通过 base64 或 URL 传递图片
        response = await self.client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_data.split(",")[-1]}} if image_data.startswith("data:") else {"type": "image", "source": {"type": "url", "url": image_data}},
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        return response.content[0].text if response.content else ""


class OllamaProvider(LLMProvider):
    """
    Ollama 本地 LLM 提供商实现。

    Ollama 是本地部署的大模型服务，支持 Llama 3、LLaVA 等模型。
    使用 OpenAI 兼容 API 接口进行调用，无需 API 密钥。

    Attributes:
        config (ProviderConfig): 提供商配置对象。
        client (AsyncOpenAI): OpenAI 兼容的异步客户端实例。
    """

    def __init__(self, config: ProviderConfig):
        """
        初始化 Ollama 提供商。

        Args:
            config (ProviderConfig): 提供商配置，包含 base_url（如 http://localhost:11434/v1）、model 等。
        """
        super().__init__(config)
        self.client = AsyncOpenAI(
            api_key="ollama",  # Ollama 不需要真实的 API 密钥
            base_url=self.config.base_url,
        )

    def _build_messages(self, prompt: str, context: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        """
        构建 Ollama API 所需的消息格式。

        将历史上下文与当前用户输入合并为完整的消息列表。

        Args:
            prompt (str): 当前用户输入的提示文本。
            context (list[dict[str, Any]] | None): 对话历史上下文。

        Returns:
            list[dict[str, Any]]: OpenAI 兼容格式的消息列表。
        """
        messages = []
        if context:
            for msg in context:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": prompt})
        return messages

    async def generate_text(self, prompt: str, context: list[dict[str, Any]] | None = None) -> str:
        """
        异步生成文本响应。

        Args:
            prompt (str): 用户输入的提示文本。
            context (list[dict[str, Any]] | None): 对话历史上下文。

        Returns:
            str: 模型生成的文本响应，若生成失败则返回空字符串。
        """
        messages = self._build_messages(prompt, context)
        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )
        return response.choices[0].message.content or ""

    async def chat_stream(self, prompt: str, context: list[dict[str, Any]] | None = None):
        """
        异步流式生成对话响应。

        Args:
            prompt (str): 用户输入的提示文本。
            context (list[dict[str, Any]] | None): 对话历史上下文。

        Returns:
            AsyncStream: OpenAI 兼容的流式响应对象。
        """
        messages = self._build_messages(prompt, context)
        return await self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            stream=True,
        )

    async def generate_with_image(self, prompt: str, image_data: str) -> str:
        """
        基于图片和文本生成响应（多模态生成）。

        使用 LLaVA 等视觉模型理解图片内容并生成文本响应。
        需要 Ollama 服务支持视觉模型（如 llava、bakllava 等）。

        Args:
            prompt (str): 用户输入的提示文本。
            image_data (str): 图片数据，支持 base64 data URL 或图片 URL。

        Returns:
            str: 模型生成的文本响应，若生成失败则返回空字符串。
        """
        # Ollama 视觉模型支持（如 llava）
        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_data}},
                    ],
                }
            ],
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )
        return response.choices[0].message.content or ""


class VLLMProvider(LLMProvider):
    """
    vLLM 高性能 LLM 服务提供商实现。

    vLLM 是高性能的大模型推理服务，支持多种开源模型（如 Llama、Qwen、Mistral 等）。
    使用 OpenAI 兼容 API 接口进行调用，支持流式响应和多模态输入。

    特性:
    - 高吞吐量、低延迟的推理服务
    - 支持多种开源模型
    - OpenAI 兼容 API
    - 支持流式响应
    - 支持 vLLM 特有参数（top_k, repetition_penalty 等）

    Attributes:
        config (ProviderConfig): 提供商配置对象。
        client (AsyncOpenAI): OpenAI 兼容的异步客户端实例。
    """

    def __init__(self, config: ProviderConfig):
        """
        初始化 vLLM 提供商。

        Args:
            config (ProviderConfig): 提供商配置，包含 base_url（如 http://localhost:8000/v1）、model 等。
        """
        super().__init__(config)
        self.client = AsyncOpenAI(
            api_key=self.config.api_key or "EMPTY",  # vLLM 本地部署通常不需要 API key
            base_url=self.config.base_url,
        )

    def _build_messages(self, prompt: str, context: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        """
        构建 vLLM API 所需的消息格式。

        将历史上下文与当前用户输入合并为完整的消息列表。

        Args:
            prompt (str): 当前用户输入的提示文本。
            context (list[dict[str, Any]] | None): 对话历史上下文。

        Returns:
            list[dict[str, Any]]: OpenAI 兼容格式的消息列表。
        """
        messages = []
        if context:
            for msg in context:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _get_extra_params(self) -> dict[str, Any]:
        """
        获取 vLLM 特有的额外参数。

        从配置中提取 top_k、repetition_penalty 等参数。

        Returns:
            dict[str, Any]: vLLM 特有的参数字典。
        """
        extra = {}
        # vLLM 支持额外的采样参数
        if hasattr(self.config, 'top_k') and self.config.top_k:
            extra['top_k'] = self.config.top_k
        if hasattr(self.config, 'repetition_penalty') and self.config.repetition_penalty:
            extra['repetition_penalty'] = self.config.repetition_penalty
        if hasattr(self.config, 'top_p') and self.config.top_p:
            extra['top_p'] = self.config.top_p
        return extra

    async def generate_text(self, prompt: str, context: list[dict[str, Any]] | None = None) -> str:
        """
        异步生成文本响应。

        Args:
            prompt (str): 用户输入的提示文本。
            context (list[dict[str, Any]] | None): 对话历史上下文。

        Returns:
            str: 模型生成的文本响应，若生成失败则返回空字符串。
        """
        messages = self._build_messages(prompt, context)
        extra_params = self._get_extra_params()
        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            **extra_params,
        )
        return response.choices[0].message.content or ""

    async def chat_stream(self, prompt: str, context: list[dict[str, Any]] | None = None):
        """
        异步流式生成对话响应。

        Args:
            prompt (str): 用户输入的提示文本。
            context (list[dict[str, Any]] | None): 对话历史上下文。

        Returns:
            AsyncStream: OpenAI 兼容的流式响应对象。
        """
        messages = self._build_messages(prompt, context)
        extra_params = self._get_extra_params()
        return await self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            stream=True,
            **extra_params,
        )

    async def generate_with_image(self, prompt: str, image_data: str) -> str:
        """
        基于图片和文本生成响应（多模态生成）。

        使用 vLLM 支持的视觉模型（如 LLaVA、Qwen-VL）理解图片内容。

        Args:
            prompt (str): 用户输入的提示文本。
            image_data (str): 图片数据，支持 base64 data URL 或图片 URL。

        Returns:
            str: 模型生成的文本响应，若生成失败则返回空字符串。
        """
        extra_params = self._get_extra_params()
        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_data}},
                    ],
                }
            ],
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            **extra_params,
        )
        return response.choices[0].message.content or ""

    def _build_messages(self, prompt: str, context: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        """
        构建 Ollama API 所需的消息格式。

        将历史上下文与当前用户输入合并为完整的消息列表。

        Args:
            prompt (str): 当前用户输入的提示文本。
            context (list[dict[str, Any]] | None): 对话历史上下文。

        Returns:
            list[dict[str, Any]]: OpenAI 兼容格式的消息列表。
        """
        messages = []
        if context:
            for msg in context:
                messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": prompt})
        return messages

    async def generate_text(self, prompt: str, context: list[dict[str, Any]] | None = None) -> str:
        """
        异步生成文本响应。

        Args:
            prompt (str): 用户输入的提示文本。
            context (list[dict[str, Any]] | None): 对话历史上下文。

        Returns:
            str: 模型生成的文本响应，若生成失败则返回空字符串。
        """
        messages = self._build_messages(prompt, context)
        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )
        return response.choices[0].message.content or ""

    async def chat_stream(self, prompt: str, context: list[dict[str, Any]] | None = None):
        """
        异步流式生成对话响应。

        Args:
            prompt (str): 用户输入的提示文本。
            context (list[dict[str, Any]] | None): 对话历史上下文。

        Returns:
            AsyncStream: OpenAI 兼容的流式响应对象。
        """
        messages = self._build_messages(prompt, context)
        return await self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            stream=True,
        )

    async def generate_with_image(self, prompt: str, image_data: str) -> str:
        """
        基于图片和文本生成响应（多模态生成）。

        使用 LLaVA 等视觉模型理解图片内容并生成文本响应。
        需要 Ollama 服务支持视觉模型（如 llava、bakllava 等）。

        Args:
            prompt (str): 用户输入的提示文本。
            image_data (str): 图片数据，支持 base64 data URL 或图片 URL。

        Returns:
            str: 模型生成的文本响应，若生成失败则返回空字符串。
        """
        # Ollama 视觉模型支持（如 llava）
        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_data}},
                    ],
                }
            ],
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
        )
        return response.choices[0].message.content or ""


class LLMOrchestrator:
    """
    LLM 编排器 - 统一管理多模态 LLM 调用。

    负责协调不同 LLM 提供商（OpenAI、Anthropic、Ollama）的调用，
    支持动态切换提供商、文本生成、流式响应和多模态（图片、音频、视频）输入。

    Attributes:
        PROVIDER_CLASSES (dict): API 类型到提供商类的映射。
        _provider (LLMProvider | None): 当前活跃的提供商实例。
        _config: LLM 配置管理器实例。

    Example:
        >>> orchestrator = LLMOrchestrator()
        >>> orchestrator.set_provider("anthropic")  # 切换到 Anthropic
        >>> response = await orchestrator.generate_text("你好")
    """

    PROVIDER_CLASSES = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "ollama": OllamaProvider,
        "vllm": VLLMProvider,
    }

    def __init__(self):
        """
        初始化 LLM 编排器。

        自动加载配置并初始化默认启用（enabled: true）的提供商。
        """
        self._provider: LLMProvider | None = None
        self._config = llm_config
        self._init_provider()

    def _init_provider(self) -> None:
        """
        初始化默认启用的提供商。

        从配置中获取第一个 enabled: true 的提供商并创建实例。
        若无可用提供商，则 _provider 保持为 None。
        """
        default_provider = self._config.get_enabled_provider()
        if default_provider:
            self._provider = self._create_provider(default_provider)

    def _create_provider(self, config: ProviderConfig) -> LLMProvider | None:
        """
        根据配置创建提供商实例。

        Args:
            config (ProviderConfig): 提供商配置对象，包含 api_type 等信息。

        Returns:
            LLMProvider | None: 提供商实例，若 api_type 不支持则返回 None。
        """
        provider_class = self.PROVIDER_CLASSES.get(config.api_type)
        if provider_class:
            return provider_class(config)
        return None

    def set_provider(self, provider_name: str) -> bool:
        """
        动态切换 LLM 提供商。

        Args:
            provider_name (str): 提供商名称，如 "openai"、"anthropic"、"ollama"。

        Returns:
            bool: 切换成功返回 True，若提供商未启用或不存在则返回 False。
        """
        provider_config = self._config.get_enabled_provider(provider_name)
        if provider_config:
            self._provider = self._create_provider(provider_config)
            return True
        return False

    @property
    def current_provider(self) -> str | None:
        """
        获取当前活跃的提供商名称。

        Returns:
            str | None: 当前提供商的 api_type，如 "openai"；若未配置则返回 None。
        """
        if self._provider:
            return self._provider.config.api_type
        return None

    async def generate_text(self, prompt: str, context: list[dict[str, Any]] | None = None) -> str:
        """
        异步生成文本响应。

        使用当前配置的提供商生成文本。若提供商未初始化，会尝试自动选择
        第一个可用的提供商。

        Args:
            prompt (str): 用户输入的提示文本。
            context (list[dict[str, Any]] | None): 对话历史上下文，
                格式为 [{"role": "user/assistant", "content": "..."}]。

        Returns:
            str: 模型生成的文本响应；若配置错误则返回错误提示信息。
        """
        if not self._provider:
            default_provider = self._config.get_enabled_provider()
            if default_provider:
                self._provider = self._create_provider(default_provider)
            else:
                return "LLM not configured. Please check llm_config.yaml and set appropriate API keys."

        try:
            return await self._provider.generate_text(prompt, context)
        except Exception as e:
            return f"Error generating text: {str(e)}"

    async def generate_with_image(self, prompt: str, image_data: str) -> str:
        """
        基于图片和文本生成响应（多模态生成）。

        使用当前配置的视觉模型（如 GPT-4o、Claude 3、LLaVA）理解图片
        内容并生成文本响应。

        Args:
            prompt (str): 用户输入的提示文本，如"描述这张图片"。
            image_data (str): 图片数据，支持格式：
                - base64 data URL: "data:image/jpeg;base64,..."
                - 图片 URL: "https://example.com/image.jpg"

        Returns:
            str: 模型生成的文本响应；若配置错误则返回错误提示信息。
        """
        if not self._provider:
            default_provider = self._config.get_enabled_provider()
            if default_provider:
                self._provider = self._create_provider(default_provider)
            else:
                return "LLM not configured. Please check llm_config.yaml and set appropriate API keys."

        try:
            return await self._provider.generate_with_image(prompt, image_data)
        except Exception as e:
            return f"Error generating text with image: {str(e)}"

    async def chat_stream(self, prompt: str, context: list[dict[str, Any]] | None = None):
        """
        异步流式生成对话响应。

        通过 SSE 方式实时返回生成内容，适用于需要流式输出到前端的场景。
        若提供商未初始化，会尝试自动选择第一个可用的提供商。

        Args:
            prompt (str): 用户输入的提示文本。
            context (list[dict[str, Any]] | None): 对话历史上下文。

        Yields:
            object: 流式响应块，格式为 choices[0].delta.content，
                与 OpenAI 流式响应格式兼容。

        Example:
            >>> async for chunk in orchestrator.chat_stream("你好"):
            ...     print(chunk.choices[0].delta.content, end="")
        """
        if not self._provider:
            # 自动选择第一个启用的提供商
            default_provider = self._config.get_enabled_provider()
            if default_provider:
                self._provider = self._create_provider(default_provider)
            else:
                error_response = type('obj', (object,), {
                    'choices': [type('obj', (object,), {
                        'delta': type('obj', (object,), {'content': 'No LLM provider enabled. Please check llm_config.yaml'})()
                    })]
                })()
                yield error_response
                return

        try:
            stream = await self._provider.chat_stream(prompt, context)
            async for chunk in stream:
                yield chunk
        except Exception as e:
            error_response = type('obj', (object,), {
                'choices': [type('obj', (object,), {
                    'delta': type('obj', (object,), {'content': f"Error: {str(e)}"})()
                })]
            })()
            yield error_response


# 全局单例实例，供整个应用使用
llm_orchestrator = LLMOrchestrator()
