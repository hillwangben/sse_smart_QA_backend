"""
API 路由模块 - 意图文档查询和测试接口。

提供意图配置的查询和测试功能：
- GET /api/v1/intents/: 获取所有意图列表
- GET /api/v1/intents/schema: 获取意图配置 JSON Schema
- GET /api/v1/intents/fallback: 获取兜底意图配置
- GET /api/v1/intents/{key}: 获取指定意图详情
- POST /api/v1/intents/query: 测试文本意图匹配
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any

from app.core.config import intent_config
from app.services.intent_detector import intent_detector


router = APIRouter(prefix="/api/v1/intents", tags=["intents"])


class IntentQueryRequest(BaseModel):
    """
    意图测试请求模型。

    用于测试文本会匹配到哪个意图。

    Attributes:
        text (str): 待测试的文本内容，不能为空。
    """

    text: str = Field(..., min_length=1, description="Text to test against intent patterns")


class IntentInfo(BaseModel):
    """
    意图信息模型。

    用于返回意图的详细信息。

    Attributes:
        key (str): 意图唯一标识符。
        patterns (list[str]): 匹配模式列表。
        params_extract (list[dict[str, Any]]): 参数提取规则列表。
        action (dict[str, Any]): 动作配置。
    """

    key: str
    patterns: list[str]
    params_extract: list[dict[str, Any]]
    action: dict[str, Any]


class IntentQueryResponse(BaseModel):
    """
    意图测试响应模型。

    返回文本匹配意图的结果。

    Attributes:
        matched (bool): 是否匹配到非兜底意图。
        intent_key (str | None): 匹配到的意图 key。
        params (dict[str, Any]): 提取的参数。
        action (dict[str, Any] | None): 意图对应的动作配置。
        confidence (str): 置信度，"high" 或 "low"。
    """

    matched: bool
    intent_key: str | None = None
    params: dict[str, Any] = {}
    action: dict[str, Any] | None = None
    confidence: str = "high"  # high | low


@router.get("/", summary="List all intents")
async def list_intents():
    """
    获取所有已配置的意图列表。

    返回每个意图的 key、匹配模式、参数提取规则和动作类型。

    Returns:
        dict: 包含 intents 列表的字典，每个意图包含 key、patterns、
            params_extract 和 action 字段。

    Example:
        请求：GET /api/v1/intents/
        响应：
        ```json
        {
            "intents": [
                {
                    "key": "weather_query",
                    "patterns": ["天气怎么样", "今天下雨吗"],
                    "params_extract": [{"pattern": "(.+)天气", "group": 1, "param_name": "city"}],
                    "action": {"type": "api_call", "api_endpoint": "/internal/weather"}
                }
            ]
        }
        ```
    """
    intents = []
    for intent in intent_config.intents:
        intents.append(IntentInfo(
            key=intent.get("key", ""),
            patterns=intent.get("patterns", []),
            params_extract=intent.get("params_extract", []),
            action=intent.get("action", {}),
        ))
    return {"intents": intents}


@router.get("/schema", summary="Get intent schema")
async def get_intent_schema():
    """
    获取意图配置的 JSON Schema。

    返回意图配置的结构定义，便于前端进行表单构建和验证。

    Returns:
        dict: 包含 schema 和 action_types 的字典。
            - schema: JSON Schema 定义
            - action_types: 动作类型说明

    Example:
        请求：GET /api/v1/intents/schema
        响应：包含完整 JSON Schema 的字典
    """
    return {
        "schema": {
            "type": "object",
            "properties": {
                "intents": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "key": {"type": "string", "description": "意图唯一标识"},
                            "patterns": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "匹配模式列表，支持正则表达式和字符串包含匹配"
                            },
                            "params_extract": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "pattern": {"type": "string"},
                                        "group": {"type": "integer"},
                                        "param_name": {"type": "string"}
                                    }
                                },
                                "description": "参数提取规则"
                            },
                            "action": {
                                "type": "object",
                                "properties": {
                                    "type": {
                                        "type": "string",
                                        "enum": ["api_call", "key_return", "llm_fallback"]
                                    },
                                    "api_endpoint": {"type": "string"},
                                    "method": {"type": "string"}
                                }
                            }
                        },
                        "required": ["key", "action"]
                    }
                }
            }
        },
        "action_types": {
            "api_call": "前端需调用指定的 API 端点",
            "key_return": "直接返回 intent_key 给前端",
            "llm_fallback": "回退到大语言模型处理"
        }
    }


@router.get("/fallback", summary="Get fallback intent")
async def get_fallback_intent():
    """
    获取兜底意图配置。

    当用户输入无法匹配任何意图时使用此配置。
    通常 action.type 为 "llm_fallback"。

    Returns:
        dict: 兜底意图配置，包含 key 和 action。

    Example:
        请求：GET /api/v1/intents/fallback
        响应：
        ```json
        {
            "key": "general_chat",
            "action": {"type": "llm_fallback"}
        }
        ```
    """
    fallback = intent_config.get_fallback_intent()
    return {
        "key": fallback.get("key", "general_chat"),
        "action": fallback.get("action", {"type": "llm_fallback"})
    }


@router.get("/{intent_key}", summary="Get intent by key")
async def get_intent(intent_key: str):
    """
    根据 key 获取特定意图的详细信息。

    Args:
        intent_key (str): 意图的唯一标识符，如 "weather_query"。

    Returns:
        IntentInfo: 意图详细信息，包含 key、patterns、params_extract 和 action。

    Raises:
        HTTPException: 404 - 意图不存在。

    Example:
        请求：GET /api/v1/intents/weather_query
        响应：
        ```json
        {
            "key": "weather_query",
            "patterns": ["天气怎么样"],
            "params_extract": [...],
            "action": {"type": "api_call", ...}
        }
        ```
    """
    intent = intent_config.get_intent_by_key(intent_key)
    if not intent:
        raise HTTPException(status_code=404, detail=f"Intent '{intent_key}' not found")

    return IntentInfo(
        key=intent.get("key", ""),
        patterns=intent.get("patterns", []),
        params_extract=intent.get("params_extract", []),
        action=intent.get("action", {}),
    )


@router.post("/query", response_model=IntentQueryResponse, summary="Test intent detection")
async def query_intent(request: IntentQueryRequest):
    """
    测试文本会匹配到哪个意图。

    用于前端在发送实际请求前预览意图检测结果，
    方便调试和验证意图配置是否正确。

    Args:
        request (IntentQueryRequest): 测试请求，包含 text 字段。

    Returns:
        IntentQueryResponse: 匹配结果，包含 matched、intent_key、params、
            action 和 confidence 字段。

    Example:
        请求：
        ```json
        {"text": "北京天气怎么样"}
        ```

        响应：
        ```json
        {
            "matched": true,
            "intent_key": "weather_query",
            "params": {"city": "北京"},
            "action": {"type": "api_call", "api_endpoint": "/internal/weather"},
            "confidence": "high"
        }
        ```
    """
    result = intent_detector.detect(request.text)

    # 判断是否匹配到特定意图（非兜底意图）
    matched = result.get("intent_key") != intent_config.get_fallback_intent().get("key") or \
              len(result.get("params", {})) > 0

    return IntentQueryResponse(
        matched=matched,
        intent_key=result.get("intent_key"),
        params=result.get("params", {}),
        action=result.get("action"),
        confidence="high" if matched else "low"
    )
