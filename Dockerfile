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
    && apt-get install -y --no-install-recommends ca-certificates curl unzip gosu \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
RUN curl -fsSL -o /tmp/tunnel-client.zip \
      "https://github.com/openai/tunnel-client/releases/download/v0.0.18/tunnel-client-v0.0.18-linux-amd64.zip" \
    && echo "3c82307316acd93c88a384b62af1d81d3f4cb0efa975f9c0bfaef922866a04c4  /tmp/tunnel-client.zip" | sha256sum -c - \
    && unzip -j /tmp/tunnel-client.zip tunnel-client -d /usr/local/bin \
    && chmod +x /usr/local/bin/tunnel-client \
    && rm /tmp/tunnel-client.zip

COPY pyproject.toml ./
RUN uv pip install --system .
COPY backend ./backend
COPY config ./config
COPY --from=frontend-build /src/frontend/out ./frontend/out

RUN useradd --create-home --shell /usr/sbin/nologin app

COPY docker/entrypoint.sh /usr/local/bin/garmintogpt-entrypoint
RUN chmod +x /usr/local/bin/garmintogpt-entrypoint

ENV PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["gosu", "app", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/status', timeout=5)"]

ENTRYPOINT ["/usr/local/bin/garmintogpt-entrypoint"]
CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
