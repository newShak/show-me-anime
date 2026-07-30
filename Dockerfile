# --- Stage 1: 构建前端静态资源 ---
FROM node:22-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# --- Stage 2: Python 运行镜像（仅保留运行时依赖）---
FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends libjpeg62-turbo libwebp7 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements-prod.txt /app/backend/requirements-prod.txt
RUN pip install -r /app/backend/requirements-prod.txt

COPY backend/ /app/backend/
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

RUN mkdir -p /app/data/thumbs /data/gallery

ENV GALLERY_ROOT=/data/gallery \
    THUMB_DIR=/app/data/thumbs \
    DATABASE_URL=sqlite:////app/data/gallery.db \
    HOST=0.0.0.0 \
    PORT=8000

EXPOSE 8000

WORKDIR /app/backend

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
