"""
意图检测器测试模块。

测试 IntentDetector 类的核心功能，包括：
- 意图匹配（天气查询、新闻查询等）
- 参数提取
- 兜底意图回退
- 空输入处理
"""
import pytest
from app.services.intent_detector import IntentDetector


@pytest.fixture
def intent_detector():
    """
    创建测试用的意图检测器实例。

    Returns:
        IntentDetector: 意图检测器实例，使用全局配置。
    """
    return IntentDetector()


def test_detect_weather_query(intent_detector):
    """
    测试天气查询意图检测。

    验证：
    - "北京天气怎么样" 能正确匹配到 weather_query 意图
    - 返回类型为 "intent"
    """
    result = intent_detector.detect("北京天气怎么样")
    assert result["type"] == "intent"
    assert result["intent_key"] == "weather_query"


def test_detect_news_query(intent_detector):
    """
    测试新闻查询意图检测。

    验证：
    - "有什么最新新闻" 能正确匹配到 news_query 意图
    """
    result = intent_detector.detect("有什么最新新闻")
    assert result["type"] == "intent"
    assert result["intent_key"] == "news_query"


def test_detect_fallback(intent_detector):
    """
    测试兜底意图回退。

    验证：
    - 无法匹配任何意图的输入回退到 llm_fallback
    - "你好，今天天气真不错" 没有精确匹配天气查询模式
    """
    result = intent_detector.detect("你好，今天天气真不错")
    # 应回退到 llm_fallback，因为没有精确匹配
    assert result["type"] == "intent"
    assert result["action"]["type"] == "llm_fallback"


def test_detect_empty_input(intent_detector):
    """
    测试空输入处理。

    验证：
    - 空字符串输入回退到 llm_fallback
    """
    result = intent_detector.detect("")
    assert result["type"] == "intent"
    assert result["action"]["type"] == "llm_fallback"


def test_params_extraction(intent_detector):
    """
    测试参数提取。

    验证：
    - 从 "上海天气" 中正确提取 city 参数为 "上海"
    - 参数提取规则匹配 (.+)天气 模式
    """
    result = intent_detector.detect("上海天气")
    assert result["params"]["city"] == "上海"
