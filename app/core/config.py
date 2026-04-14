"""
意图规则配置加载模块。

从 YAML 配置文件加载意图定义，支持运行时热重载。
配置文件位于 config/intent_rules.yaml。
"""
import yaml
from pathlib import Path
from typing import Any


class IntentConfig:
    """
    意图配置管理器。

    从 YAML 文件加载意图定义，提供意图查询和兜底意图获取功能。

    Attributes:
        config_path (Path): 配置文件路径，默认为 config/intent_rules.yaml。
        _intents (list[dict[str, Any]]): 已加载的意图列表。

    Example:
        >>> from app.core.config import intent_config
        >>> intent = intent_config.get_intent_by_key("weather_query")
        >>> print(intent["action"]["type"])
        'api_call'
    """

    def __init__(self, config_path: str = "config/intent_rules.yaml"):
        """
        初始化意图配置管理器。

        Args:
            config_path (str): 配置文件路径，默认为 config/intent_rules.yaml。
        """
        self.config_path = Path(config_path)
        self._intents: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        """
        从文件加载配置。

        若配置文件不存在，则初始化为空列表。
        """
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                self._intents = data.get("intents", [])
        else:
            self._intents = []

    def reload(self) -> None:
        """
        重新加载配置文件。

        用于运行时热更新配置，无需重启服务。

        Example:
            >>> intent_config.reload()  # 重新加载配置
        """
        self._load()

    @property
    def intents(self) -> list[dict[str, Any]]:
        """
        获取所有已加载的意图列表。

        Returns:
            list[dict[str, Any]]: 意图配置列表，每个意图包含 key、patterns、
                params_extract、action 等字段。
        """
        return self._intents

    def get_intent_by_key(self, key: str) -> dict[str, Any] | None:
        """
        根据 key 获取意图配置。

        Args:
            key (str): 意图的唯一标识符，如 "weather_query"。

        Returns:
            dict[str, Any] | None: 意图配置字典，若未找到则返回 None。
        """
        for intent in self._intents:
            if intent.get("key") == key:
                return intent
        return None

    def get_fallback_intent(self) -> dict[str, Any]:
        """
        获取兜底意图配置。

        兜底意图是 action.type 为 "llm_fallback" 的意图，
        当用户输入无法匹配任何意图时使用。

        Returns:
            dict[str, Any]: 兜底意图配置，若配置中无定义则返回默认值。
        """
        for intent in self._intents:
            if intent.get("action", {}).get("type") == "llm_fallback":
                return intent
        return {"key": "general_chat", "action": {"type": "llm_fallback"}}


# 全局单例实例，供整个应用使用
intent_config = IntentConfig()
