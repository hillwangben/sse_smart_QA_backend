# Smart Q&A Backend

智能问答后端，支持 SSE 流式响应、意图理解和多模态问答。

## 核心功能

- **SSE 流式响应** - 通过 Server-Sent Events 实时推送 AI 回答
- **多会话支持** - 支持并发会话管理，可恢复历史对话
- **意图理解** - NLU 模块对用户输入进行分类
- **大模型问答** - 支持 OpenAI、Anthropic、Ollama 等多种 LLM
- **多模态支持** - 支持图片、视频、音频输入

## 快速开始

```bash
# 安装依赖
uv sync

# 开发环境运行
uv run uvicorn main:app --reload --port 38047

# 访问 API 文档
# Swagger UI: http://localhost:38047/docs
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

### 健康检查
```
GET /health
```

## 配置

### 大模型配置 (`config/llm_config.yaml`)

支持多种 LLM Provider：

| Provider | 说明 | 配置示例 |
|----------|------|----------|
| `openai` | OpenAI GPT-4/4o 系列 | 需要 `OPENAI_API_KEY` |
| `anthropic` | Anthropic Claude 系列 | 需要 `ANTHROPIC_API_KEY` |
| `ollama` | 本地 Ollama 模型 | 无需 API key |
| `custom_api` | 自定义 OpenAI 兼容 API | 需要相应的 API key |

### 意图配置 (`config/intent_rules.yaml`)

通过 YAML 文件管理意图规则，支持正则匹配和参数提取。

## 技术栈

- Python 3.10+
- FastAPI
- uv (包管理)
- OpenAI / Anthropic / Ollama

## 测试

```bash
uv run pytest
```
