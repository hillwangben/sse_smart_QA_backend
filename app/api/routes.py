"""
API 路由模块 - 聊天、会话管理和健康检查。

提供核心 REST API 和 SSE 流式接口：
- POST /api/v1/chat/stream: SSE 流式聊天接口
- POST /api/v1/session: 创建新会话
- GET /api/v1/session/{id}: 获取会话及历史
- DELETE /api/v1/session/{id}: 删除会话
- GET /health: 健康检查
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
import json
import asyncio
from app.models.schemas import ChatRequest, SessionCreate, SessionResponse
from app.services.session_manager import session_manager
from app.services.intent_detector import intent_detector
from app.services.llm_orchestrator import llm_orchestrator


router = APIRouter()


@router.post("/api/v1/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    SSE 流式聊天接口。

    接收用户消息，执行意图检测，根据意图类型返回不同响应：
    - api_call: 返回意图信息，由前端调用对应 API
    - key_return: 直接返回意图 key 给前端
    - llm_fallback: 调用大模型流式生成回复

    Args:
        request (ChatRequest): 聊天请求，包含 session_id、content 和可选的 multi_media。

    Returns:
        EventSourceResponse: SSE 流式响应，每条消息格式为：
            {"type": "intent|llm|error", "data": {...}}

    Raises:
        HTTPException:
            - 400: 缺少 session_id
            - 404: 会话不存在

    Example:
        请求：
        ```json
        {"session_id": "uuid", "content": "北京天气怎么样"}
        ```

        响应（SSE 流）：
        ```
        event: message
        data: {"type": "intent", "intent_key": "weather_query", ...}

        event: close
        data: {"type": "close"}
        ```
    """
    if not request.session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    session = session_manager.get_session(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")

    history = session_manager.get_history(request.session_id) or []

    async def event_generator():
        """
        SSE 事件生成器。

        处理用户消息并生成 SSE 事件流。
        """
        # 步骤 1: 意图检测
        intent_result = intent_detector.detect(request.content)

        # 将用户消息添加到历史
        session_manager.add_message(request.session_id, "user", request.content)

        action_type = intent_result.get("action", {}).get("type")

        if action_type == "api_call":
            # 返回意图结果，由前端处理 API 调用
            yield {
                "event": "message",
                "data": json.dumps(intent_result),
            }
        elif action_type == "key_return":
            # 直接返回 key 给前端
            yield {
                "event": "message",
                "data": json.dumps(intent_result),
            }
        else:
            # LLM 兜底 - 流式生成响应
            context = history[-10:] if len(history) > 10 else history

            # 处理多模态输入
            has_multimedia = request.multi_media and len(request.multi_media) > 0

            if has_multimedia:
                # 获取第一个图片（如果存在）
                image_item = next((m for m in request.multi_media if m.type == "image"), None)
                if image_item:
                    result = await llm_orchestrator.generate_with_image(
                        request.content, image_item.url
                    )
                    yield {
                        "event": "message",
                        "data": json.dumps({"type": "llm", "data": {"content": result}}),
                    }
            else:
                # 流式生成文本响应
                stream = llm_orchestrator.chat_stream(request.content, context)
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "llm",
                                "data": {"content": chunk.choices[0].delta.content}
                            }),
                        }

        yield {"event": "close", "data": json.dumps({"type": "close"})}

    return EventSourceResponse(event_generator())


@router.post("/api/v1/session", response_model=SessionResponse)
async def create_session(request: SessionCreate):
    """
    创建新会话。

    生成新的会话 ID 并初始化空的历史记录。

    Args:
        request (SessionCreate): 创建会话请求（当前无参数）。

    Returns:
        SessionResponse: 新创建的会话信息，包含 session_id、时间戳和空历史。

    Example:
        请求：POST /api/v1/session
        响应：
        ```json
        {
            "session_id": "550e8400-e29b-41d4-a716-446655440000",
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z",
            "history": []
        }
        ```
    """
    session = session_manager.create_session()
    return SessionResponse(
        session_id=session.session_id,
        created_at=session.created_at,
        updated_at=session.updated_at,
        history=session.history,
    )


@router.get("/api/v1/session/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """
    获取会话及历史记录。

    根据会话 ID 查询会话详情和完整对话历史。

    Args:
        session_id (str): 会话唯一标识符（UUID）。

    Returns:
        SessionResponse: 会话信息，包含完整历史记录。

    Raises:
        HTTPException: 404 - 会话不存在。

    Example:
        请求：GET /api/v1/session/550e8400-...
        响应：
        ```json
        {
            "session_id": "550e8400-...",
            "history": [
                {"role": "user", "content": "你好", "timestamp": "..."},
                {"role": "assistant", "content": "你好！", "timestamp": "..."}
            ]
        }
        ```
    """
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    return SessionResponse(
        session_id=session.session_id,
        created_at=session.created_at,
        updated_at=session.updated_at,
        history=session.history,
    )


@router.delete("/api/v1/session/{session_id}")
async def delete_session(session_id: str):
    """
    删除会话。

    关闭并删除指定会话，释放资源。

    Args:
        session_id (str): 会话唯一标识符（UUID）。

    Returns:
        dict: 删除成功消息。

    Raises:
        HTTPException: 404 - 会话不存在。

    Example:
        请求：DELETE /api/v1/session/550e8400-...
        响应：{"message": "session deleted"}
    """
    deleted = session_manager.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="session not found")
    return {"message": "session deleted"}


@router.get("/health")
async def health_check():
    """
    健康检查接口。

    用于负载均衡器和监控系统检测服务状态。

    Returns:
        dict: 服务健康状态。

    Example:
        请求：GET /health
        响应：{"status": "healthy"}
    """
    return {"status": "healthy"}
