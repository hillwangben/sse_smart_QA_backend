"""
FastAPI 应用入口模块。

初始化 FastAPI 应用实例，配置中间件、路由和静态文件服务。
提供聊天测试界面和 API 文档。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from app.api.routes import router
from app.api.intents import router as intents_router


app = FastAPI(
    title="Smart Q&A Backend",
    description="智能问答后端，支持 SSE 流式响应、意图理解和多模态问答",
    version="0.1.0",
)

# CORS 中间件配置
# 允许所有来源、方法和请求头，适用于开发环境
# 生产环境应限制 allow_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(router)
app.include_router(intents_router)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """
    根路径 - 返回聊天测试界面。

    提供可视化的聊天测试页面，方便测试 SSE 流式响应和意图检测。

    Returns:
        HTMLResponse: 聊天测试界面的 HTML 内容。
    """
    with open("app/templates/chat.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/chat", response_class=HTMLResponse)
async def chat_page():
    """
    聊天页面 - 返回聊天测试界面。

    与根路径功能相同，提供额外的访问入口。

    Returns:
        HTMLResponse: 聊天测试界面的 HTML 内容。
    """
    with open("app/templates/chat.html", "r", encoding="utf-8") as f:
        return f.read()


if __name__ == "__main__":
    """
    直接运行入口。

    使用 uvicorn 启动开发服务器，监听 0.0.0.0:38047。

    Example:
        ```bash
        python main.py
        # 或
        uv run python main.py
        ```
    """
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=38047)
