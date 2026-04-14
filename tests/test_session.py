"""
会话管理器测试模块。

测试 SessionManager 类的核心功能，包括：
- 会话创建、查询、删除
- 消息添加和历史记录管理
- 历史消息自动裁剪
"""
import pytest
from app.services.session_manager import SessionManager


@pytest.fixture
def session_manager():
    """
    创建测试用的会话管理器实例。

    设置较小的 max_history（5）以便测试历史裁剪功能。

    Returns:
        SessionManager: 配置了 max_history=5 的会话管理器实例。
    """
    return SessionManager(max_history=5)


def test_create_session(session_manager):
    """
    测试创建会话。

    验证：
    - 会话 ID 不为空
    - 初始历史为空
    """
    session = session_manager.create_session()
    assert session.session_id is not None
    assert len(session.history) == 0


def test_get_session(session_manager):
    """
    测试获取已存在的会话。

    验证：
    - 能正确获取创建的会话
    - 返回的会话 ID 与创建时一致
    """
    session = session_manager.create_session()
    retrieved = session_manager.get_session(session.session_id)
    assert retrieved is not None
    assert retrieved.session_id == session.session_id


def test_get_nonexistent_session(session_manager):
    """
    测试获取不存在的会话。

    验证：
    - 获取不存在的会话返回 None
    """
    assert session_manager.get_session("nonexistent") is None


def test_delete_session(session_manager):
    """
    测试删除会话。

    验证：
    - 删除成功返回 True
    - 删除后无法再获取该会话
    """
    session = session_manager.create_session()
    assert session_manager.delete_session(session.session_id) is True
    assert session_manager.get_session(session.session_id) is None


def test_delete_nonexistent_session(session_manager):
    """
    测试删除不存在的会话。

    验证：
    - 删除不存在的会话返回 False
    """
    assert session_manager.delete_session("nonexistent") is False


def test_add_message(session_manager):
    """
    测试添加消息到会话。

    验证：
    - 消息成功添加
    - 消息的 role 和 content 正确
    """
    session = session_manager.create_session()
    message = session_manager.add_message(session.session_id, "user", "Hello")
    assert message is not None
    assert message.role == "user"
    assert message.content == "Hello"


def test_add_message_to_nonexistent_session(session_manager):
    """
    测试向不存在的会话添加消息。

    验证：
    - 向不存在的会话添加消息返回 None
    """
    result = session_manager.add_message("nonexistent", "user", "Hello")
    assert result is None


def test_history_trimming(session_manager):
    """
    测试历史消息自动裁剪。

    验证：
    - 当消息数超过 max_history 时，自动裁剪旧消息
    - 裁剪后历史长度等于 max_history
    - 裁剪保留最新的消息
    """
    session = session_manager.create_session()
    # 添加 7 条消息（max_history 为 5）
    for i in range(7):
        session_manager.add_message(session.session_id, "user", f"Message {i}")

    updated_session = session_manager.get_session(session.session_id)
    assert len(updated_session.history) == 5
    # 验证保留了最新的 5 条消息（Message 2 到 Message 6）
    assert updated_session.history[0].content == "Message 2"
    assert updated_session.history[4].content == "Message 6"


def test_get_history(session_manager):
    """
    测试获取会话历史。

    验证：
    - 返回正确的历史消息列表
    - 历史消息包含正确的 role 和 content
    """
    session = session_manager.create_session()
    session_manager.add_message(session.session_id, "user", "Hello")
    session_manager.add_message(session.session_id, "assistant", "Hi there")

    history = session_manager.get_history(session.session_id)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hello"
    assert history[1]["role"] == "assistant"
