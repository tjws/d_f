FROM python:3.13-slim

WORKDIR /app

# 使用锁文件安装固定依赖；项目源码通过 PYTHONPATH 直接加载，避免在镜像内写入开发虚拟环境。
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev --no-install-project

COPY alembic.ini ./
COPY backend ./backend

ENV PATH="/app/.venv/bin:${PATH}"
ENV PYTHONPATH=/app/backend
WORKDIR /app/backend

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
