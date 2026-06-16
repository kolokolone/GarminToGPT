# syntax=docker/dockerfile:1.7

FROM node:24-alpine AS frontend-build
WORKDIR /src/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend ./
RUN npm run build

FROM python:3.12-slim AS runtime
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl git \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv \
    && curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared \
    && chmod +x /usr/local/bin/cloudflared

COPY pyproject.toml ./
RUN uv pip install --system .
COPY backend ./backend
COPY config ./config
COPY --from=frontend-build /src/frontend/out ./frontend/out

RUN useradd --create-home --shell /usr/sbin/nologin app \
    && mkdir -p /app/logs /app/runtime/pids /app/data/garmin /home/app/.garminconnect \
    && chown -R app:app /app /home/app/.garminconnect

USER app
ENV GARMINTOGPT_ENV=local
ENV GARMINTOGPT_CONFIG=/app/config/app.yaml
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/status', timeout=5)"

CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
