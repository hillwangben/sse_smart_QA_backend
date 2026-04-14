# 构建阶段
FROM python:3.12-slim as builder

# 安装 uv
RUN pip install uv

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY pyproject.toml uv.lock ./

# 安装依赖
RUN uv sync --frozen --no-dev

# 运行阶段
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 复制依赖和源码
COPY --from=builder /app/.venv /app/.venv
COPY pyproject.toml ./
COPY app/ ./app/
COPY config/ ./config/
COPY main.py ./

# 设置虚拟环境
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app"

# 暴露端口
EXPOSE 38047

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "38047"]