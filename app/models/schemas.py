"""
Pydantic 数据模型定义模块。

定义 API 请求和响应的数据结构，用于数据验证和序列化。
所有模型使用 Pydantic V2 实现，支持类型检查和 JSON Schema 生成。
"""
from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field


class Message(BaseModel):
    """
    聊天消息模型。

    表示对话历史中的一条消息，可以是用户消息或助手回复。

    Attributes:
        role (str): 消息角色，"user" 或 "assistant"。
        content (str): 消息文本内容。
        timestamp (datetime): 消息时间戳，默认为当前 UTC 时间。

    Example:
        >>> msg = Message(role="user", content="你好")
        >>> print(msg.timestamp)
        2024-01-15 10:30:00+00:00
    """

    role: str  # "user" 或 "assistant"
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MultiMediaItem(BaseModel):
    """
    多媒体附件模型。

    表示聊天请求中附带的多媒体内容（图片、音频、视频）。

    Attributes:
        type (str): 媒体类型，支持 "image"、"audio"、"video"。
        url (str): 媒体资源 URL，支持 data URL（base64）或外部链接。

    Example:
        >>> item = MultiMediaItem(type="image", url="data:image/jpeg;base64,...")
    """

    type: str  # "image", "audio", "video"
    url: str


class ChatRequest(BaseModel):
    """
    SSE 聊天请求模型。

    发送到 /api/v1/chat/stream 接口的请求数据结构。

    Attributes:
        session_id (str | None): 会话 ID，首次对话时为 None，后续对话需提供。
        content (str): 用户输入的文本内容。
        multi_media (list[MultiMediaItem]): 多媒体附件列表，默认为空列表。

    Example:
        >>> request = ChatRequest(
        ...     session_id="uuid-string",
        ...     content="这张图片是什么？",
        ...     multi_media=[MultiMediaItem(type="image", url="...")]
        ... )
    """

    session_id: str | None = None
    content: str
    multi_media: list[MultiMediaItem] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """
    聊天响应数据模型。

    SSE 流式响应中每条消息的数据结构。

    Attributes:
        type (str): 响应类型，支持 "intent"（意图识别结果）、
            "llm"（大模型回复）、"error"（错误信息）。
        data (dict[str, Any]): 响应数据，根据 type 不同而变化。
    """

    type: str  # "intent", "llm", "error"
    data: dict[str, Any]


class Session(BaseModel):
    """
    会话模型。

    表示一个完整的聊天会话，包含会话元数据和对话历史。

    Attributes:
        session_id (str): 会话唯一标识符（UUID）。
        created_at (datetime): 会话创建时间。
        updated_at (datetime): 会话最后更新时间。
        history (list[Message]): 对话历史消息列表。

    Example:
        >>> session = Session(session_id=str(uuid.uuid4()))
        >>> session.history.append(Message(role="user", content="Hello"))
    """

    session_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    history: list[Message] = Field(default_factory=list)


class SessionCreate(BaseModel):
    """
    创建会话请求模型。

    当前无额外参数，预留用于未来扩展。
    """

    pass


class SessionResponse(BaseModel):
    """
    会话响应模型。

    创建会话或获取会话时返回的数据结构。

    Attributes:
        session_id (str): 会话唯一标识符。
        created_at (datetime): 会话创建时间。
        updated_at (datetime): 会话最后更新时间。
        history (list[Message]): 对话历史消息列表。
    """

    session_id: str
    created_at: datetime
    updated_at: datetime
    history: list[Message]
