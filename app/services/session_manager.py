"""
会话管理服务模块。

提供聊天会话的生命周期管理，包括创建、查询、删除会话，
以及对话历史的存储和检索。支持历史消息自动裁剪以控制上下文窗口大小。
"""
import uuid
from datetime import datetime, timezone
from typing import Any
from app.models.schemas import Session, Message


class SessionManager:
    """
    会话管理器。

    管理聊天会话的完整生命周期，使用内存字典存储会话数据。
    支持会话创建、查询、删除，以及对话历史的添加和检索。

    Attributes:
        max_history (int): 单个会话最大历史消息数，超出后自动裁剪旧消息。
        _sessions (dict[str, Session]): 会话 ID 到会话对象的映射。

    Example:
        >>> manager = SessionManager(max_history=50)
        >>> session = manager.create_session()
        >>> manager.add_message(session.session_id, "user", "你好")
        >>> history = manager.get_history(session.session_id)

    Note:
        当前使用内存存储，服务重启后会话数据将丢失。
        生产环境建议使用 Redis 等持久化存储。
    """

    def __init__(self, max_history: int = 50):
        """
        初始化会话管理器。

        Args:
            max_history (int): 单个会话最大历史消息数，默认为 50。
                超出后自动删除最早的消息，保持上下文窗口大小可控。
        """
        self.max_history = max_history
        self._sessions: dict[str, Session] = {}

    def create_session(self) -> Session:
        """
        创建新会话。

        生成唯一会话 ID 并创建会话对象，存储在内存字典中。

        Returns:
            Session: 新创建的会话对象，包含 session_id、时间戳和空的历史列表。

        Example:
            >>> session = manager.create_session()
            >>> print(session.session_id)
            '550e8400-e29b-41d4-a716-446655440000'
        """
        session_id = str(uuid.uuid4())
        session = Session(session_id=session_id)
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Session | None:
        """
        根据会话 ID 获取会话。

        Args:
            session_id (str): 会话唯一标识符（UUID）。

        Returns:
            Session | None: 会话对象，若不存在则返回 None。

        Example:
            >>> session = manager.get_session("uuid-string")
            >>> if session:
            ...     print(len(session.history))
        """
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        """
        删除会话。

        Args:
            session_id (str): 会话唯一标识符（UUID）。

        Returns:
            bool: 删除成功返回 True，会话不存在返回 False。

        Example:
            >>> success = manager.delete_session("uuid-string")
            >>> print("删除成功" if success else "会话不存在")
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def add_message(self, session_id: str, role: str, content: str) -> Message | None:
        """
        向会话添加消息。

        将新消息添加到会话历史，并更新会话的 updated_at 时间戳。
        若历史消息数超过 max_history，自动裁剪最早的消息。

        Args:
            session_id (str): 会话唯一标识符（UUID）。
            role (str): 消息角色，"user" 或 "assistant"。
            content (str): 消息文本内容。

        Returns:
            Message | None: 新添加的消息对象，若会话不存在则返回 None。

        Example:
            >>> msg = manager.add_message(session_id, "user", "你好")
            >>> print(msg.role, msg.content)
            'user' '你好'
        """
        session = self._sessions.get(session_id)
        if not session:
            return None

        message = Message(role=role, content=content)
        session.history.append(message)
        session.updated_at = datetime.now(timezone.utc)

        # 裁剪历史消息，保持不超过 max_history
        if len(session.history) > self.max_history:
            session.history = session.history[-self.max_history:]

        return message

    def get_history(self, session_id: str) -> list[dict[str, Any]] | None:
        """
        获取会话历史消息列表。

        将会话历史转换为字典列表格式，便于 JSON 序列化和传递给 LLM。

        Args:
            session_id (str): 会话唯一标识符（UUID）。

        Returns:
            list[dict[str, Any]] | None: 历史消息列表，每条消息包含 role、
                content 和 timestamp 字段；若会话不存在则返回 None。

        Example:
            >>> history = manager.get_history(session_id)
            >>> for msg in history:
            ...     print(f"{msg['role']}: {msg['content']}")
            'user: 你好'
            'assistant: 你好！有什么可以帮助你的？'
        """
        session = self._sessions.get(session_id)
        if not session:
            return None
        return [
            {"role": m.role, "content": m.content, "timestamp": m.timestamp.isoformat()}
            for m in session.history
        ]


# 全局单例实例，供整个应用使用
session_manager = SessionManager()
