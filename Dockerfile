# syntax=docker/dockerfile:1.7

FROM node:24-alpine AS frontend-build
ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /src/frontend
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend ./
RUN npm run build

FROM python:3.12-slim AS runtime
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates gosu \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "uv==0.11.17"

# Download the pinned tunnel-client without keeping curl/unzip or the archive.
RUN python -c "import hashlib, pathlib, urllib.request, zipfile; url='https://github.com/openai/tunnel-client/releases/download/v0.0.18/tunnel-client-v0.0.18-linux-amd64.zip'; expected='3c82307316acd93c88a384b62af1d81d3f4cb0efa975f9c0bfaef922866a04c4'; data=urllib.request.urlopen(url, timeout=180).read(); actual=hashlib.sha256(data).hexdigest(); assert actual == expected, actual; archive=pathlib.Path('/tmp/tunnel-client.zip'); archive.write_bytes(data); bundle=zipfile.ZipFile(archive); names=[name for name in bundle.namelist() if pathlib.PurePosixPath(name).name == 'tunnel-client']; assert names, 'tunnel-client missing'; target=pathlib.Path('/usr/local/bin/tunnel-client'); target.write_bytes(bundle.read(names[0])); target.chmod(0o755); bundle.close(); archive.unlink()"

# Install only the locked runtime dependencies (no dev group, no project package).
COPY pyproject.toml uv.lock ./
RUN uv export --frozen --no-dev --no-emit-project --format requirements-txt -o /tmp/requirements.txt \
    && uv pip install --system -r /tmp/requirements.txt \
    && rm -rf /tmp/requirements.txt /root/.cache

COPY backend/app ./backend/app
COPY config/app.yaml ./config/app.yaml
COPY --from=frontend-build /src/frontend/out ./frontend/out

RUN useradd --create-home --shell /usr/sbin/nologin app

COPY docker/entrypoint.sh /usr/local/bin/garmintogpt-entrypoint
RUN chmod +x /usr/local/bin/garmintogpt-entrypoint

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["gosu", "app", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/status', timeout=5)"]

ENTRYPOINT ["/usr/local/bin/garmintogpt-entrypoint"]
CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
