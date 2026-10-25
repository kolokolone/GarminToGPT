"""HTTP contract tests for status, access gating, and key management.

The Garmin client boundary is faked: these tests never touch the network or the
real key file. The auth core's own behavior is covered by unit tests.
"""

import os
from pathlib import Path

import pytest
from app.garmin_auth import (
    ConfigureOutcome,
    EnvKeyConflictError,
    GarminAuthStatus,
    GarminKeyInfo,
    GarminRotationInfo,
)
from fastapi.testclient import TestClient

KEY = "GCDC_" + "a" * 120


def _status(
    state: str = "not_configured",
    *,
    configured: bool = False,
    message: str | None = None,
) -> GarminAuthStatus:
    ready = configured and state in {"valid", "expiring_soon"}
    return GarminAuthStatus(
        state=state,  # type: ignore[arg-type]
        configured=configured,
        key=GarminKeyInfo(
            source="file" if configured else None,
            hint="••••abcd" if configured else None,
            fingerprint="0123456789ab" if configured else None,
        ),
        token_present=configured,
        token_valid=ready,
        token_expires_at="2026-10-26T12:00:00+00:00" if configured else None,
        token_scopes=["CONNECT_READ"] if configured else [],
        rotation=(
            GarminRotationInfo(
                expires_on="2026-11-24",
                days_remaining=30,
                source="declared",
                warning=False,
            )
            if configured
            else GarminRotationInfo()
        ),
        last_verified_at="2026-10-25T12:00:00+00:00" if configured else None,
        display_name="Test Runner" if configured else None,
        message=message
        or ("Clé API valide." if configured else "Aucune clé API Garmin configurée."),
    )


class FakeGarminAuth:
    def __init__(self) -> None:
        self.current = _status()
        self.error: Exception | None = None
        self.configure_calls: list[tuple[str, str | None]] = []
        self.verify_calls = 0
        self.remove_calls = 0
        self.update_calls: list[str | None] = []

    def status(self) -> GarminAuthStatus:
        return self.current

    def verify(self) -> GarminAuthStatus:
        self.verify_calls += 1
        return self.current

    def configure(self, api_key: str, expires_on: str | None = None) -> ConfigureOutcome:
        if self.error is not None:
            raise self.error
        self.configure_calls.append((api_key, expires_on))
        self.current = _status("valid", configured=True)
        return ConfigureOutcome(changed=True, status=self.current)

    def update_expiration(self, expires_on: str | None) -> GarminAuthStatus:
        self.update_calls.append(expires_on)
        rotation = (
            GarminRotationInfo(
                expires_on=expires_on,
                days_remaining=37 if expires_on else None,
                source="declared" if expires_on else "unknown",
                warning=False,
            )
            if expires_on
            else GarminRotationInfo()
        )
        self.current = self.current.model_copy(update={"rotation": rotation})
        return self.current

    def remove(self) -> GarminAuthStatus:
        self.remove_calls += 1
        self.current = _status()
        return self.current


@pytest.fixture
def client(tmp_path, monkeypatch):
    config = _write_config(tmp_path)
    monkeypatch.setenv("GARMINTOGPT_CONFIG", str(config))
    monkeypatch.setenv("GARMINTOGPT_GARMIN_KEY_FILE", str(tmp_path / "api-key"))
    monkeypatch.setenv("GARMINTOGPT_GARMIN_TOKEN_CACHE", str(tmp_path / "cache.json"))
    monkeypatch.delenv("GARMIN_PERSONAL_API_KEY", raising=False)

    from app.core.config import get_settings
    from app.services.container import get_container

    get_settings.cache_clear()
    get_container.cache_clear()

    from app.main import create_app

    app = create_app()
    container = get_container()
    fake = FakeGarminAuth()
    container.garmin = fake  # type: ignore[assignment]
    container.tests.garmin = fake  # type: ignore[assignment]

    with TestClient(app) as test_client:
        yield test_client, fake, container

    get_settings.cache_clear()
    get_container.cache_clear()


def test_status_and_tests_endpoints_without_key(client) -> None:
    test_client, fake, _ = client

    status = test_client.get("/api/status")
    tests = test_client.get("/api/tests")

    assert status.status_code == 200
    assert status.json()["state"] == "needs_auth"
    assert status.json()["garmin"]["state"] == "not_configured"
    assert status.json()["garmin"]["configured"] is False
    assert tests.status_code == 200
    assert len(tests.json()["tests"]) >= 14

    access = test_client.post("/api/access/start")
    assert access.status_code == 200
    data = access.json()
    assert data["state"] == "needs_auth"
    assert data["garmin"]["state"] == "not_configured"
    assert data["mcp"]["state"] == "stopped"
    assert data["tunnel"]["state"] == "stopped"
    assert fake.verify_calls == 1


def test_access_start_with_expired_key_does_not_start_bridge(client) -> None:
    test_client, fake, _ = client
    fake.current = _status("expired", configured=True, message="Clé API expirée.")

    start = test_client.post("/api/access/start")
    assert start.status_code == 200
    data = start.json()
    assert data["state"] == "needs_auth"
    assert data["garmin"]["state"] == "expired"
    assert data["mcp"]["state"] == "stopped"
    assert data["tunnel"]["state"] == "stopped"

    stop = test_client.post("/api/access/stop")
    assert stop.status_code == 200


def test_configure_key_returns_secret_free_status(client) -> None:
    test_client, fake, _ = client

    response = test_client.post(
        "/api/auth/key",
        json={"api_key": KEY, "expires_on": "2026-11-24"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["changed"] is True
    assert payload["status"]["state"] == "valid"
    assert KEY not in response.text
    assert fake.configure_calls == [(KEY, "2026-11-24")]


def test_configure_key_maps_environment_conflict_to_409(client) -> None:
    test_client, fake, _ = client
    fake.error = EnvKeyConflictError("La variable d'environnement est prioritaire.")

    response = test_client.post("/api/auth/key", json={"api_key": KEY})

    assert response.status_code == 409
    assert "prioritaire" in response.json()["detail"]


def test_update_expiration_endpoint(client) -> None:
    test_client, fake, _ = client
    fake.current = _status("valid", configured=True)

    response = test_client.patch("/api/auth/key", json={"expires_on": "2026-12-01"})

    assert response.status_code == 200
    assert response.json()["rotation"]["expires_on"] == "2026-12-01"
    assert fake.update_calls == ["2026-12-01"]


def test_delete_key_requires_confirmation(client) -> None:
    test_client, fake, _ = client
    fake.current = _status("valid", configured=True)

    response = test_client.request(
        "DELETE",
        "/api/auth/key",
        json={"confirm": False},
    )

    assert response.status_code == 400
    assert fake.remove_calls == 0


def test_delete_key_stops_bridge(client, monkeypatch) -> None:
    test_client, fake, container = client
    fake.current = _status("valid", configured=True)

    calls: list[str] = []
    monkeypatch.setattr(container.mcp, "stop_mcp_service", lambda: calls.append("mcp"))
    monkeypatch.setattr(container.tunnel, "stop_tunnel", lambda: calls.append("tunnel"))

    response = test_client.request(
        "DELETE",
        "/api/auth/key",
        json={"confirm": True},
    )

    assert response.status_code == 200
    assert response.json()["status"]["state"] == "not_configured"
    assert fake.remove_calls == 1
    assert calls == ["mcp", "tunnel"]


def _write_config(tmp_path: Path) -> Path:
    runtime_dir = tmp_path / "runtime"
    logs_dir = tmp_path / "logs"
    content = f"""
app:
  name: GarminToGPT
  version: 1.0.0
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
  command: [uvx, garmin-personal-mcp]
  proxy_command: [uvx, mcp-proxy]
garmin:
  rotation_warning_days: 7
  timeout_seconds: 5
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
