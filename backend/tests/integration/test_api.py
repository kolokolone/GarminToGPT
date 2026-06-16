import os
from pathlib import Path

from fastapi.testclient import TestClient


def test_api_status_and_tests_endpoints(tmp_path, monkeypatch) -> None:
    config = _write_config(tmp_path)
    monkeypatch.setenv("GARMINTOGPT_CONFIG", str(config))

    from app.core.config import get_settings
    from app.services.container import get_container

    get_settings.cache_clear()
    get_container.cache_clear()

    from app.main import create_app

    client = TestClient(create_app())
    status = client.get("/api/status")
    tests = client.get("/api/tests")

    assert status.status_code == 200
    assert status.json()["state"] == "needs_auth"
    assert tests.status_code == 200
    assert len(tests.json()["tests"]) >= 14


def _write_config(tmp_path: Path) -> Path:
    token_dir = tmp_path / "tokens"
    runtime_dir = tmp_path / "runtime"
    logs_dir = tmp_path / "logs"
    content = f"""
app:
  name: GarminToGPT
  version: 0.3.3
  environment: test
server:
  host: 127.0.0.1
  backend_port: 8000
  frontend_port: 3000
mcp:
  host: 127.0.0.1
  port: 18080
  endpoint: /mcp
  sse_endpoint: /sse
  command: [uvx, garmin-mcp]
  proxy_command: [uvx, mcp-proxy]
garmin:
  auth_command: [uvx, garmin-mcp-auth]
  verify_command: [uvx, garmin-mcp-auth, --verify]
  token_dir: "{token_dir}"
cloudflare:
  mode: quick
  local_url: http://127.0.0.1:18080
  tunnel_name: ""
  hostname: ""
  command: cloudflared
runtime:
  dir: "{runtime_dir}"
  pid_dir: "{runtime_dir / "pids"}"
  state_file: "{runtime_dir / "state.json"}"
logs:
  dir: "{logs_dir}"
  max_size_mb: 10
  retain_files: 5
security:
  bind_local_only: true
  redact_sensitive_logs: true
  allow_write_tools: false
timeouts:
  process_start_seconds: 1
  process_stop_seconds: 1
  healthcheck_seconds: 1
"""
    if os.name == "nt":
        content = content.replace("\\", "\\\\")
    path = tmp_path / "app.yaml"
    path.write_text(content, encoding="utf-8")
    return path
