"""
意图检测服务模块。

基于可配置的规则对用户输入进行意图分类，支持正则表达式匹配、
关键词匹配和参数提取。未匹配的输入会回退到大语言模型处理。
"""
import re
from typing import Any
from app.core.config import intent_config


class IntentDetector:
    """
    意图检测器。

    根据配置的规则检测用户输入的意图，提取相关参数，
    并返回对应的动作类型。

    Attributes:
        无实例属性，依赖全局 intent_config 获取意图配置。

    Example:
        >>> from app.services.intent_detector import intent_detector
        >>> result = intent_detector.detect("北京天气怎么样")
        >>> print(result["intent_key"])
        'weather_query'
        >>> print(result["params"])
        {'city': '北京'}
    """

    def detect(self, text: str) -> dict[str, Any]:
        """
        检测用户输入的意图。

        遍历所有配置的意图规则，按顺序匹配用户输入。
        匹配成功则返回意图信息和提取的参数，
        匹配失败则返回兜底意图（llm_fallback）。

        Args:
            text (str): 用户输入的文本内容。

        Returns:
            dict[str, Any]: 意图检测结果，格式如下：
                ```python
                {
                    "type": "intent",
                    "intent_key": "weather_query",  # 意图标识
                    "params": {"city": "北京"},      # 提取的参数
                    "action": {                      # 动作配置
                        "type": "api_call",
                        "api_endpoint": "/internal/weather"
                    }
                }
                ```

        Example:
            >>> result = intent_detector.detect("上海天气")
            >>> result["intent_key"]
            'weather_query'
            >>> result["params"]["city"]
            '上海'
        """
        if not text:
            return self._fallback_result()

        text = text.strip()

        for intent in intent_config.intents:
            patterns = intent.get("patterns", [])
            if not patterns:
                continue

            for pattern in patterns:
                if self._match_pattern(text, pattern):
                    params = self._extract_params(text, intent)
                    return {
                        "type": "intent",
                        "intent_key": intent.get("key"),
                        "params": params,
                        "action": intent.get("action", {}),
                    }

        return self._fallback_result()

    def _match_pattern(self, text: str, pattern: str) -> bool:
        """
        匹配文本与模式。

        支持两种匹配方式：
        - 正则表达式：模式以 ^ 开头或 $ 结尾时使用正则匹配
        - 字符串包含：其他情况使用简单的字符串包含匹配

        Args:
            text (str): 待匹配的用户输入文本。
            pattern (str): 匹配模式，可以是正则表达式或普通字符串。

        Returns:
            bool: 匹配成功返回 True，否则返回 False。
        """
        try:
            if pattern.startswith("^") or pattern.endswith("$"):
                return bool(re.search(pattern, text))
            return pattern in text
        except re.error:
            # 正则表达式语法错误时回退到字符串匹配
            return pattern in text

    def _extract_params(self, text: str, intent: dict[str, Any]) -> dict[str, Any]:
        """
        从文本中提取参数。

        根据意图配置中的 params_extract 规则，使用正则表达式
        从用户输入中提取命名参数。

        Args:
            text (str): 用户输入文本。
            intent (dict[str, Any]): 意图配置，包含 params_extract 规则。

        Returns:
            dict[str, Any]: 提取的参数字典，key 为参数名，value 为参数值。

        Example:
            配置：
            ```yaml
            params_extract:
              - pattern: "(.+)天气"
                group: 1
                param_name: "city"
            ```
            输入: "上海天气"
            输出: {"city": "上海"}
        """
        params = {}
        for extract_rule in intent.get("params_extract", []):
            pattern = extract_rule.get("pattern")
            group = extract_rule.get("group", 0)
            param_name = extract_rule.get("param_name")

            if pattern and param_name:
                try:
                    match = re.search(pattern, text)
                    if match and group < len(match.groups()):
                        params[param_name] = match.group(group) if group > 0 else match.group()
                except re.error:
                    pass
        return params

    def _fallback_result(self) -> dict[str, Any]:
        """
        返回兜底意图结果。

        当用户输入无法匹配任何配置的意图时，返回此结果，
        指示系统使用大语言模型处理用户输入。

        Returns:
            dict[str, Any]: 兜底意图结果，action.type 为 "llm_fallback"。
        """
        fallback = intent_config.get_fallback_intent()
        return {
            "type": "intent",
            "intent_key": fallback.get("key", "general_chat"),
            "params": {},
            "action": fallback.get("action", {"type": "llm_fallback"}),
        }


# 全局单例实例，供整个应用使用
intent_detector = IntentDetector()
