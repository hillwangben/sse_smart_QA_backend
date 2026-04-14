# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个**智能问答后端**，支持 SSE（Server-Sent Events）流式响应。核心功能包括：

1. **SSE 流式响应** - 通过 Server-Sent Events 实时推送 AI 回答给前端
2. **多会话支持** - 支持并发会话管理，可恢复历史对话
3. **意图理解** - NLU 模块对用户输入进行分类，返回结构化意图 key 或触发 API 调用
4. **大模型问答** - 非意图内容直接调用大语言模型处理
5. **多模态支持** - 支持图片、视频、音频输入的多模态大模型调用

## 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                         API 层                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │  SSE 流式   │  │  REST API   │  │  WebSocket（可选）       │ │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘ │
└─────────┼────────────────┼─────────────────────┼───────────────┘
          │                │                     │
┌─────────▼────────────────▼─────────────────────▼───────────────┐
│                      Session Manager（会话管理器）               │
│  - 会话生命周期管理（创建/更新/关闭）                             │
│  - 历史记录存储与检索                                             │
│  - 上下文窗口管理                                                 │
└─────────┬────────────────────────────────────────────────────────┘
          │
┌─────────▼────────────────────────────────────────────────────────┐
│                    Intent Detection Layer（意图检测层）          │
│  - 输入分类                                                       │
│  - Key 提取（返回给前端或调用 API）                               │
│  - 未分类内容回退到大模型                                         │
└─────────┬───────────────────────────┬────────────────────────────┘
          │                           │
┌─────────▼───────────┐  ┌───────────▼────────────────────────────┐
│   Intent Actions    │  │              LLM Orchestrator（LLM 编排）│
│  - API 调用         │  │  ┌──────────┐ ┌──────────┐ ┌─────────┐ │
│  - Key 响应         │  │  │  文本模型 │ │  图片模型 │ │ 视频模型 │ │
│                     │  │  └──────────┘ └──────────┘ └─────────┘ │
└─────────────────────┘  └──────────────────────────────────────────┘
```

## 大模型配置

大模型支持通过配置文件管理，配置文件位于 `config/llm_config.yaml`，支持多种 provider：

### 支持的 Provider 类型

| Provider | 说明 | 配置示例 |
|----------|------|----------|
| `openai` | OpenAI GPT-4/4o 系列 | 需要 `OPENAI_API_KEY` |
| `anthropic` | Anthropic Claude 系列 | 需要 `ANTHROPIC_API_KEY` |
| `ollama` | 本地 Ollama 模型 | 无需 API key |
| `custom_api` | 自定义 OpenAI 兼容 API | 需要相应的 API key |

### 配置文件格式

```yaml
default_provider: "openai"  # 默认 provider

providers:
  openai:
    enabled: true
    api_type: "openai"
    model: "gpt-4o"
    api_key: "${OPENAI_API_KEY}"      # 环境变量引用
    base_url: "https://api.openai.com/v1"
    max_tokens: 1000
    temperature: 0.7
    timeout: 60

  anthropic:
    enabled: false
    api_type: "anthropic"
    model: "claude-3-sonnet-20240229"
    api_key: "${ANTHROPIC_API_KEY}"
    base_url: "https://api.anthropic.com/v1"

  ollama:
    enabled: false
    api_type: "ollama"
    model: "llama3"
    api_key: ""
    base_url: "http://localhost:11434/v1"

multimodal:
  vision_model: "gpt-4o"    # 图片理解模型
  image_max_tokens: 1000

context:
  max_history_messages: 20  # 上下文窗口最大消息数
  system_prompt: "You are a helpful AI assistant."
```

### Provider 切换

代码中可以通过 `llm_orchestrator.set_provider("provider_name")` 动态切换 provider，但只有 `enabled: true` 的 provider 才能被切换。

### 环境变量

配置文件中支持 `${ENV_VAR}` 格式引用环境变量：

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

## 技术栈

- **语言**: Python 3.10+
- **构建工具**: uv（高性能 Python 包管理器）
- **框架**: FastAPI - 原生支持 SSE 和异步
- **大模型**: OpenAI GPT-4V、Anthropic Claude、或本地模型
- **会话存储**: Redis（生产）/ 内存 dict（开发）
- **多模态**: GPT-4V、Claude Vision、LLaVA 等

## 常用命令

```bash
# 安装依赖（使用 uv）
uv sync

# 开发环境运行
uv run uvicorn main:app --reload --port 38047

# 生产环境运行
uv run uvicorn main:app --host 0.0.0.0 --port 38047 --workers 4

# 运行测试
uv run pytest

# 运行单个测试文件
uv run pytest tests/test_session.py -v

# 带覆盖率测试
uv run pytest --cov=app --cov-report=term-missing
```

## API 接口

### SSE 流式接口
```
POST /api/v1/chat/stream
```
- **请求**: `{"session_id": "uuid", "content": "用户消息", "multi_media": [...]}`
- **响应**: SSE 流，格式 `{"type": "intent|llm|error", "data": {...}}`

### 会话管理
```
POST   /api/v1/session          - 创建新会话
GET    /api/v1/session/{id}     - 获取会话及历史
DELETE /api/v1/session/{id}     - 关闭会话
```

### 健康检查
```
GET /health
```

### 意图文档查询
```
GET    /api/v1/intents/           - 获取所有意图列表
GET    /api/v1/intents/schema     - 获取意图配置 JSON Schema
GET    /api/v1/intents/fallback   - 获取兜底意图配置
GET    /api/v1/intents/{key}      - 获取指定意图详情
POST   /api/v1/intents/query      - 测试文本会匹配到哪个意图
```

**意图查询示例：**
```bash
# 测试文本匹配
curl -X POST http://localhost:38047/api/v1/intents/query \
  -H "Content-Type: application/json" \
  -d '{"text": "北京天气怎么样"}'

# 返回
{
  "matched": true,
  "intent_key": "weather_query",
  "params": {"city": "北京"},
  "action": {"type": "api_call", "api_endpoint": "/internal/weather"},
  "confidence": "high"
}
```

## 测试界面

启动服务后，通过浏览器访问：

- **Chat 测试界面**: `http://localhost:38047/` 或 `http://localhost:38047/chat` - 实时问答测试界面
- **Swagger UI**: `http://localhost:38047/docs` - API 文档与测试
- **ReDoc**: `http://localhost:38047/redoc` - 备选文档界面
- **OpenAPI JSON**: `http://localhost:38047/openapi.json`

## 会话数据结构

```python
{
    "session_id": "uuid",
    "created_at": "ISO 时间戳",
    "updated_at": "ISO 时间戳",
    "history": [
        {"role": "user", "content": "...", "timestamp": "..."},
        {"role": "assistant", "content": "...", "timestamp": "..."}
    ]
}
```

## 意图理解配置

意图理解通过 `config/intent_rules.yaml` 配置文件进行管理，支持灵活的意图定义和匹配规则。

### 配置文件格式

```yaml
intents:
  - key: "weather_query"
    patterns:                     # 匹配模式（任一匹配即触发）
      - "天气怎么样"
      - "今天下雨吗"
      - "weather"
    params_extract:               # 参数提取规则
      - pattern: "(.+)天气"
        group: 1
        param_name: "city"
    action:
      type: "api_call"           # api_call | key_return | llm_fallback
      api_endpoint: "/internal/weather"
      method: "GET"

  - key: "news_query"
    patterns:
      - "最新新闻"
      - "有什么消息"
    action:
      type: "key_return"         # 直接返回 key 给前端，不调用 API

  - key: "general_chat"
    patterns: []                 # 空数组表示兜底意图
    action:
      type: "llm_fallback"       # 未匹配时回退到大模型
```

### 意图匹配流程

1. 用户输入 → 按配置的正则/关键词匹配
2. 匹配成功 → 根据 `action.type` 执行对应操作
3. 匹配失败 → 触发 `llm_fallback` 回退到大模型

### 意图响应格式

意图分类后的响应返回：
```json
{
    "type": "intent",
    "intent_key": "weather_query",
    "params": {"city": "北京"},
    "action": "api_call",
    "api_endpoint": "/internal/weather"
}
```

## 多模态输入格式

```json
{
    "content": "这张图片里有什么？",
    "multi_media": [
        {"type": "image", "url": "data:image/jpeg;base64,..."},
        {"type": "audio", "url": "data:audio/mp3;base64,..."},
        {"type": "video", "url": "https://..."}
    ]
}
```

## 开发规范

- 所有 I/O 操作使用 `async/await`
- 会话历史限制为最近 N 条消息（可配置的上下文窗口）
- 错误处理需返回有意义的错误码
- 时间戳统一使用 ISO 8601 格式
- 使用依赖注入管理会话存储（便于测试）
