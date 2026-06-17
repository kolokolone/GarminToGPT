import os
from pathlib import Path

from fastapi.testclient import TestClient


def _create_token_file(config_path: Path, token_dir: Path) -> Path:
    """Crée un fichier factice pour simuler la présence d'un token Garmin."""
    token_dir.mkdir(parents=True, exist_ok=True)
    token_file = token_dir / "garmin_token.txt"
    token_file.write_text("dummy-token", encoding="utf-8")
    return token_file


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

    # ── Access: sans token Garmin, le démarrage est bloqué ──

    access = client.post("/api/access/start")
    assert access.status_code == 200
    data = access.json()
    assert data["state"] == "needs_auth", (
        f"Sans token, start_access doit retourner needs_auth, got {data['state']}"
    )
    assert data["garmin"]["state"] == "no_token"

    # Vérifier que ni MCP ni tunnel n'ont été lancés
    status2 = client.get("/api/status")
    assert status2.json()["state"] == "needs_auth"
    assert status2.json()["mcp"]["state"] == "stopped"
    assert status2.json()["tunnel"]["state"] == "stopped"


def test_access_start_with_invalid_garmin_token(tmp_path, monkeypatch) -> None:
    """Avec un token Garmin invalide, start_access ne lance ni MCP ni tunnel."""
    config = _write_config(tmp_path)
    monkeypatch.setenv("GARMINTOGPT_CONFIG", str(config))

    from app.core.config import get_settings
    from app.models.auth import GarminAuthStatus
    from app.services.container import get_container

    get_settings.cache_clear()
    get_container.cache_clear()

    # Créer un fichier token pour que has_garmin_token() retourne True
    token_dir = tmp_path / "tokens"
    token_dir.mkdir(parents=True, exist_ok=True)
    (token_dir / "token.txt").write_text("dummy", encoding="utf-8")

    # Patcher verify_garmin_auth pour simuler un token invalide
    container = get_container()
    monkeypatch.setattr(
        container.garmin,
        "verify_garmin_auth",
        lambda: GarminAuthStatus(
            state="auth_invalid",
            token_found=True,
            token_valid=False,
            message="Token invalide (test).",
        ),
    )

    from app.main import create_app

    client = TestClient(create_app())

    start = client.post("/api/access/start")
    assert start.status_code == 200
    data = start.json()
    assert data["state"] == "degraded", (
        f"Avec token invalide, start_access doit retourner degraded, got {data['state']}"
    )
    assert data["garmin"]["state"] == "auth_invalid"

    # MCP et tunnel ne doivent pas avoir été lancés
    assert data["mcp"]["state"] == "stopped"
    assert data["tunnel"]["state"] == "stopped"

    # Le stop ne doit pas être affecté
    stop = client.post("/api/access/stop")
    assert stop.status_code == 200


def test_access_stop_unchanged(tmp_path, monkeypatch) -> None:
    """Le comportement de stop_access est inchangé par le patch Garmin."""
    config = _write_config(tmp_path)
    monkeypatch.setenv("GARMINTOGPT_CONFIG", str(config))

    from app.core.config import get_settings
    from app.services.container import get_container

    get_settings.cache_clear()
    get_container.cache_clear()

    from app.main import create_app

    client = TestClient(create_app())

    stop = client.post("/api/access/stop")
    assert stop.status_code == 200
    data = stop.json()
    assert data["state"] == "needs_auth"  # toujours pas de token


def _write_config(tmp_path: Path) -> Path:
    token_dir = tmp_path / "tokens"
    runtime_dir = tmp_path / "runtime"
    logs_dir = tmp_path / "logs"
    content = f"""
app:
  name: GarminToGPT
  version: 0.4.10
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
