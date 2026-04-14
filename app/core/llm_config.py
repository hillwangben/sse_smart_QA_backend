"""
大模型提供商配置加载模块。

从 YAML 配置文件加载 LLM 提供商配置，支持多提供商管理、
环境变量引用和运行时热重载。
配置文件位于 config/llm_config.yaml。
"""
import os
import re
import yaml
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field


@dataclass
class ProviderConfig:
    """
    单个 LLM 提供商的配置。

    Attributes:
        enabled (bool): 是否启用此提供商。
        api_type (str): API 类型，支持 "openai"、"anthropic"、"ollama"。
        model (str): 模型名称，如 "gpt-4o"、"claude-3-sonnet-20240229"。
        api_key (str): API 密钥，支持 ${ENV_VAR} 格式引用环境变量。
        base_url (str): API 基础 URL，用于自定义端点或代理。
        max_tokens (int): 最大生成 token 数。
        temperature (float): 生成温度，控制随机性。
        timeout (int): 请求超时时间（秒）。
    """

    enabled: bool = False
    api_type: str = "openai"
    model: str = "gpt-4o"
    api_key: str = ""
    base_url: str = ""
    max_tokens: int = 1000
    temperature: float = 0.7
    timeout: int = 60

    def resolve_env_vars(self) -> None:
        """
        解析配置中的环境变量引用。

        将 ${ENV_VAR} 格式的字符串替换为对应的环境变量值。
        若环境变量不存在，则替换为空字符串。

        Example:
            配置 api_key: "${OPENAI_API_KEY}"
            若 OPENAI_API_KEY="sk-xxx"，则解析后 api_key="sk-xxx"
        """
        for attr in ["api_key", "base_url"]:
            value = getattr(self, attr)
            if isinstance(value, str):
                matches = re.findall(r'\$\{(\w+)\}', value)
                for match in matches:
                    env_value = os.getenv(match, "")
                    setattr(self, attr, value.replace(f"${{{match}}}", env_value))


@dataclass
class MultimodalConfig:
    """
    多模态功能配置。

    Attributes:
        vision_model (str): 视觉模型名称，用于图片理解。
        image_max_tokens (int): 图片理解最大 token 数。
    """

    vision_model: str = "gpt-4o"
    image_max_tokens: int = 1000


@dataclass
class ContextConfig:
    """
    上下文管理配置。

    Attributes:
        max_history_messages (int): 上下文窗口最大消息数。
        system_prompt (str): 系统提示词。
    """

    max_history_messages: int = 20
    system_prompt: str = "You are a helpful AI assistant."


class LLMConfig:
    """
    LLM 配置管理器。

    从 YAML 文件加载大模型配置，支持多提供商管理、环境变量解析
    和运行时热重载。

    Attributes:
        config_path (Path): 配置文件路径。
        _providers (dict[str, ProviderConfig]): 提供商配置字典。
        _default_provider (str): 默认提供商名称。
        _multimodal (MultimodalConfig): 多模态配置。
        _context (ContextConfig): 上下文配置。

    Example:
        >>> from app.core.llm_config import llm_config
        >>> provider = llm_config.get_enabled_provider("openai")
        >>> print(provider.model)
        'gpt-4o'
    """

    def __init__(self, config_path: str = "config/llm_config.yaml"):
        """
        初始化 LLM 配置管理器。

        Args:
            config_path (str): 配置文件路径，默认为 config/llm_config.yaml。
        """
        self.config_path = Path(config_path)
        self._providers: dict[str, ProviderConfig] = {}
        self._default_provider: str = "openai"
        self._multimodal: MultimodalConfig = MultimodalConfig()
        self._context: ContextConfig = ContextConfig()
        self._load()

    def _load(self) -> None:
        """
        从文件加载配置。

        解析 YAML 文件并初始化各配置对象，同时解析环境变量引用。
        """
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            self._default_provider = data.get("default_provider", "openai")

            # 加载提供商配置
            providers_data = data.get("providers", {})
            for name, config in providers_data.items():
                provider = ProviderConfig(**config)
                provider.resolve_env_vars()
                self._providers[name] = provider

            # 加载多模态配置
            multimodal_data = data.get("multimodal", {})
            self._multimodal = MultimodalConfig(**multimodal_data)

            # 加载上下文配置
            context_data = data.get("context", {})
            self._context = ContextConfig(**context_data)
        else:
            self._providers = {}

    def reload(self) -> None:
        """
        重新加载配置文件。

        用于运行时热更新配置，无需重启服务。
        """
        self._load()

    @property
    def default_provider(self) -> str:
        """
        获取默认提供商名称。

        Returns:
            str: 默认提供商名称，如 "openai"。
        """
        return self._default_provider

    @property
    def providers(self) -> dict[str, ProviderConfig]:
        """
        获取所有提供商配置。

        Returns:
            dict[str, ProviderConfig]: 提供商名称到配置的映射字典。
        """
        return self._providers

    @property
    def multimodal(self) -> MultimodalConfig:
        """
        获取多模态配置。

        Returns:
            MultimodalConfig: 多模态功能配置对象。
        """
        return self._multimodal

    @property
    def context(self) -> ContextConfig:
        """
        获取上下文配置。

        Returns:
            ContextConfig: 上下文管理配置对象。
        """
        return self._context

    def get_provider(self, name: str | None = None) -> ProviderConfig | None:
        """
        获取指定提供商的配置。

        Args:
            name (str | None): 提供商名称，若为 None 则返回默认提供商。

        Returns:
            ProviderConfig | None: 提供商配置对象，若未找到则返回 None。
        """
        provider_name = name or self._default_provider
        return self._providers.get(provider_name)

    def get_enabled_provider(self, name: str | None = None) -> ProviderConfig | None:
        """
        获取已启用的提供商配置。

        若指定名称，则返回该名称对应的已启用提供商；
        若不指定名称，则返回第一个已启用的提供商。

        Args:
            name (str | None): 提供商名称。

        Returns:
            ProviderConfig | None: 已启用的提供商配置，若无则返回 None。

        Example:
            >>> # 获取第一个启用的提供商
            >>> provider = llm_config.get_enabled_provider()
            >>> # 获取指定名称的启用提供商
            >>> provider = llm_config.get_enabled_provider("anthropic")
        """
        if name:
            provider = self.get_provider(name)
            if provider and provider.enabled:
                return provider
        else:
            # 查找第一个启用的提供商
            for provider in self._providers.values():
                if provider.enabled:
                    return provider
        return None


# 全局单例实例，供整个应用使用
llm_config = LLMConfig()
