"""
Smart Q&A Backend 应用主模块。

本模块是智能问答后端的核心入口，提供以下功能：
- SSE 流式响应：通过 Server-Sent Events 实时推送 AI 回答
- 多会话支持：支持并发会话管理，可恢复历史对话
- 意图理解：NLU 模块对用户输入进行分类
- 大模型问答：支持 OpenAI、Anthropic、Ollama 等多种 LLM
- 多模态支持：支持图片、视频、音频输入

Example:
    启动服务：
    ```bash
    uv run uvicorn main:app --reload --port 38047
    ```
"""
