"""Tests for OpenAI tunnel orchestration helpers.

The FastAPI access routes are covered by the integration suite; these tests
exercise the tunnel service behavior without contacting OpenAI.
"""

import sys
from pathlib import Path
from unittest.mock import patch

from app.core.config import Settings
from app.models.common import ProcessStatus, ServiceActionResult
from app.models.tunnel import TunnelStatus
from app.openai_tunnel import OpenAITunnelConfigStore
from app.services.healthcheck_service import HealthcheckService
from app.services.mcp_service import McpService
from app.services.process_manager import ProcessManager
from app.services.tunnel_service import TunnelService

from .test_config_security import _settings_dict

TUNNEL_ID = "tunnel_0123456789abcdef0123456789abcdef"
API_KEY = "sk-test-runtime-key-1234567890"


class FakeBinary:
    def __init__(self) -> None:
        self.path = Path(sys.executable)

    def status(self):
        from app.openai_tunnel import TunnelBinary

        return TunnelBinary(self.path, "0.0.18", True, "runtime")

    def ensure(self):
        return self.status()


class FakeValidator:
    def validate(self, tunnel_id: str, api_key: str):
        from app.openai_tunnel import TunnelValidation

        return TunnelValidation(True, "validé")


def _make_settings(tmp_path: Path) -> Settings:
    raw = _settings_dict()
    raw["runtime"] = {
        "dir": str(tmp_path / "runtime"),
        "pid_dir": str(tmp_path / "runtime" / "pids"),
        "state_file": str(tmp_path / "runtime" / "state.json"),
    }
    raw["logs"] = {"dir": str(tmp_path / "logs"), "max_size_mb": 10, "retain_files": 5}
    settings = Settings.model_validate(raw)
    settings.ensure_directories()
    return settings


def _make_store(tmp_path: Path) -> OpenAITunnelConfigStore:
    return OpenAITunnelConfigStore(
        key_file=tmp_path / "tunnel-key",
        config_file=tmp_path / "tunnel.json",
        env={},
    )


def _make_tunnel_service(tmp_path: Path) -> TunnelService:
    settings = _make_settings(tmp_path)
    return TunnelService(
        settings,
        ProcessManager(settings),
        store=_make_store(tmp_path),
        binary=FakeBinary(),
        validator=FakeValidator(),
    )


def _make_mcp_service(tmp_path: Path) -> McpService:
    settings = _make_settings(tmp_path)
    return McpService(settings, ProcessManager(settings), HealthcheckService(settings))


def _running_status(service: TunnelService) -> TunnelStatus:
    return TunnelStatus(
        state="running",
        configured=True,
        tunnel_id=TUNNEL_ID,
        api_key_configured=True,
        ready=True,
        connector_url=service.settings.tunnel.connector_url,
        process=ProcessStatus(status="running", pid=42, message="running"),
    )


def test_ensure_tunnel_without_config_is_refused(tmp_path: Path) -> None:
    service = _make_tunnel_service(tmp_path)

    result = service.ensure_tunnel()

    assert result.ok is False
    assert result.state == "error"
    assert "/tunnel" in result.message


def test_ensure_tunnel_stopped_starts_tunnel(tmp_path: Path) -> None:
    service = _make_tunnel_service(tmp_path)
    service.store.save(TUNNEL_ID, API_KEY)
    fake_result = ServiceActionResult(
        ok=True,
        status="starting",
        message="Tunnel lancé",
        pid=12345,
    )

    with patch.object(service.process_manager, "start", return_value=fake_result) as start:
        result = service.ensure_tunnel()

    assert start.called is True
    assert result.ok is True
    assert result.state == "starting"


def test_ensure_tunnel_running_is_noop(tmp_path: Path) -> None:
    service = _make_tunnel_service(tmp_path)
    with (
        patch.object(service, "get_tunnel_status", return_value=_running_status(service)),
        patch.object(service.process_manager, "start") as start,
    ):
        result = service.ensure_tunnel()

    assert start.called is False
    assert result.ok is True
    assert result.state == "running"
    assert "déjà running" in result.message


def test_stop_mcp_does_not_stop_tunnel(tmp_path: Path) -> None:
    tunnel_service = _make_tunnel_service(tmp_path)
    mcp_service = _make_mcp_service(tmp_path)

    result = tunnel_service.process_manager.start(
        "tunnel",
        [sys.executable, "-c", "import time; time.sleep(60)"],
    )
    assert result.ok is True
    assert tunnel_service.process_manager.status("tunnel").status == "running"

    mcp_result = mcp_service.start_mcp_service()
    assert mcp_result.ok is True
    mcp_service.stop_mcp_service()

    assert tunnel_service.process_manager.status("tunnel").status == "running"
    tunnel_service.process_manager.stop("tunnel")


def test_access_endpoints_are_registered() -> None:
    from app.api.routes_access import router

    routes = [route.path for route in router.routes]
    assert "/api/access/start" in routes
    assert "/api/access/stop" in routes
