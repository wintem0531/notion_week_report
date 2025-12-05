# Notion 自动周报生成工具 Docker 镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# 复制项目文件
COPY pyproject.toml uv.lock ./
COPY src ./src

# 安装依赖
RUN uv sync --frozen --no-dev

# 创建配置目录
RUN mkdir -p /app/config

# 设置入口点
ENTRYPOINT ["uv", "run", "python", "-m", "notion_week_report.main"]

# 默认参数：启动定时调度器
CMD ["--schedule", "--config", "/app/config/config.yaml"]

