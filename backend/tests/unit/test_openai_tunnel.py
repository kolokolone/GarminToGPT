"""Tests for the OpenAI tunnel config, validation, binary and orchestration."""

import json
import subprocess
import sys
import zipfile
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from app.core.config import Settings
from app.models.common import ProcessStatus, ServiceActionResult
from app.openai_tunnel import (
    RELEASES,
    OpenAITunnelConfigStore,
    TunnelBinary,
    TunnelBinaryManager,
    TunnelClientValidator,
    TunnelConfigFormatError,
    TunnelEnvConflictError,
    TunnelValidation,
    TunnelValidationError,
)
from app.services.process_manager import ProcessManager
from app.services.tunnel_service import TunnelService

from .test_config_security import _settings_dict

TUNNEL_ID = "tunnel_0123456789abcdef0123456789abcdef"
OTHER_ID = "tunnel_fedcba9876543210fedcba9876543210"
API_KEY = "sk-test-runtime-key-1234567890"


class FakeBinary:
    def __init__(self, path: Path | None = None, installed: bool = True) -> None:
        self.path = path or Path(sys.executable)
        self.installed = installed

    def status(self) -> TunnelBinary:
        return TunnelBinary(
            path=self.path,
            version="0.0.18" if self.installed else None,
            installed=self.installed,
            source="runtime",
        )

    def ensure(self) -> TunnelBinary:
        return self.status()


class FakeValidator:
    def __init__(self, validation: TunnelValidation | None = None) -> None:
        self.validation = validation or TunnelValidation(True, "Tunnel OpenAI validé.")
        self.calls: list[tuple[str, str]] = []

    def validate(self, tunnel_id: str, api_key: str) -> TunnelValidation:
        self.calls.append((tunnel_id, api_key))
        return self.validation


def _settings(tmp_path: Path, *, command: str = "tunnel-client") -> Settings:
    raw = _settings_dict()
    raw["tunnel"]["command"] = command  # type: ignore[index]
    raw["runtime"] = {
        "dir": str(tmp_path / "runtime"),
        "pid_dir": str(tmp_path / "runtime" / "pids"),
        "state_file": str(tmp_path / "runtime" / "state.json"),
    }
    raw["logs"] = {"dir": str(tmp_path / "logs"), "max_size_mb": 10, "retain_files": 5}
    settings = Settings.model_validate(raw)
    settings.ensure_directories()
    return settings


def _store(tmp_path: Path, env: dict[str, str] | None = None) -> OpenAITunnelConfigStore:
    return OpenAITunnelConfigStore(
        key_file=tmp_path / "tunnel-key",
        config_file=tmp_path / "tunnel.json",
        env=env or {},
    )


def _service(
    tmp_path: Path,
    *,
    store: OpenAITunnelConfigStore | None = None,
    validator: FakeValidator | None = None,
    binary: FakeBinary | None = None,
) -> TunnelService:
    settings = _settings(tmp_path)
    return TunnelService(
        settings,
        ProcessManager(settings),
        store=store or _store(tmp_path),
        binary=binary or FakeBinary(),
        validator=validator or FakeValidator(),
    )


def test_store_round_trip_and_sources(tmp_path: Path) -> None:
    store = _store(tmp_path)
    saved = store.save(TUNNEL_ID, API_KEY)

    assert saved.configured is True
    assert saved.source == "file"
    assert saved.key_source == "file"
    assert saved.tunnel_id_source == "file"
    assert saved.editable is True
    assert store.hint(saved.api_key) == "••••7890"
    assert store.load().tunnel_id == TUNNEL_ID

    env_store = _store(
        tmp_path,
        env={"CONTROL_PLANE_TUNNEL_ID": OTHER_ID, "CONTROL_PLANE_API_KEY": "sk-env-key"},
    )
    env_config = env_store.load()
    assert env_config.tunnel_id == OTHER_ID
    assert env_config.key_source == "env"
    assert env_config.editable is False

    with pytest.raises(TunnelEnvConflictError):
        env_store.save(TUNNEL_ID, "sk-other-key")


def test_store_rejects_invalid_values(tmp_path: Path) -> None:
    store = _store(tmp_path)
    with pytest.raises(TunnelConfigFormatError):
        store.save("tunnel_bad", API_KEY)
    with pytest.raises(TunnelConfigFormatError):
        store.save(TUNNEL_ID, "short")
    with pytest.raises(TunnelConfigFormatError):
        store.save(TUNNEL_ID, "sk-key with spaces")


def test_configure_validates_then_saves(tmp_path: Path) -> None:
    validator = FakeValidator()
    service = _service(tmp_path, validator=validator)

    result = service.configure(TUNNEL_ID, API_KEY)

    assert result.ok is True
    assert result.changed is True
    assert result.config.configured is True
    assert service.key_path.read_text(encoding="utf-8").strip() == API_KEY
    assert validator.calls == [(TUNNEL_ID, API_KEY)]

    second = service.configure(TUNNEL_ID, API_KEY)
    assert second.changed is False


def test_configure_rejects_invalid_credentials(tmp_path: Path) -> None:
    validator = FakeValidator(
        TunnelValidation(False, "Clé refusée.", http_status=400)
    )
    service = _service(tmp_path, validator=validator)

    with pytest.raises(TunnelValidationError):
        service.configure(TUNNEL_ID, API_KEY)

    assert not service.key_path.exists()


def test_start_without_config_is_refused(tmp_path: Path) -> None:
    service = _service(tmp_path)
    result = service.start_tunnel()

    assert result.ok is False
    assert result.state == "error"
    assert "/tunnel" in result.message


def test_start_builds_openai_command_and_passes_key_by_env(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.save(TUNNEL_ID, API_KEY)
    service = _service(tmp_path, store=store)
    fake_result = ServiceActionResult(
        ok=True,
        status="starting",
        message="Tunnel lancé.",
        pid=123,
    )

    with patch.object(service.process_manager, "start", return_value=fake_result) as start:
        result = service.start_tunnel()

    command = start.call_args.args[1]
    env = start.call_args.kwargs["env"]
    assert result.state == "starting"
    assert "--control-plane.tunnel-id" in command
    assert command[command.index("--control-plane.tunnel-id") + 1] == TUNNEL_ID
    assert command[command.index("--control-plane.api-key") + 1] == (
        "env:CONTROL_PLANE_API_KEY"
    )
    assert "url=http://127.0.0.1:8080/mcp,channel=main" in command
    assert command[command.index("--health.listen-addr") + 1] == "127.0.0.1:8091"
    assert env == {
        "CONTROL_PLANE_API_KEY": API_KEY,
        "CONTROL_PLANE_TUNNEL_ID": TUNNEL_ID,
    }
    assert API_KEY not in " ".join(command)


def test_status_uses_readyz_and_has_no_public_url(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = _store(tmp_path)
    store.save(TUNNEL_ID, API_KEY)
    service = _service(tmp_path, store=store)
    monkeypatch.setattr(
        service.process_manager,
        "status",
        lambda name: ProcessStatus(status="running", pid=55, message="Processus actif."),
    )
    monkeypatch.setattr(
        "app.services.tunnel_service.httpx.get",
        lambda url, timeout: httpx.Response(200, text="ok"),
    )

    status = service.get_tunnel_status()

    assert status.state == "running"
    assert status.ready is True
    assert status.tunnel_id == TUNNEL_ID
    assert status.configured is True
    assert status.health_url == "http://127.0.0.1:8091/readyz"
    assert status.ui_url == "http://127.0.0.1:8091/ui"
    assert not hasattr(status, "public_url")


def test_status_waits_for_readyz(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = _store(tmp_path)
    store.save(TUNNEL_ID, API_KEY)
    service = _service(tmp_path, store=store)
    monkeypatch.setattr(
        service.process_manager,
        "status",
        lambda name: ProcessStatus(status="running", pid=55, message="Processus actif."),
    )
    monkeypatch.setattr(
        "app.services.tunnel_service.httpx.get",
        lambda url, timeout: httpx.Response(503, text="waiting"),
    )

    status = service.get_tunnel_status()

    assert status.state == "starting"
    assert status.ready is False
    assert "503" in (status.last_event or "")


def test_status_without_config(tmp_path: Path) -> None:
    service = _service(tmp_path)
    status = service.get_tunnel_status()

    assert status.state == "stopped"
    assert status.configured is False
    assert "/tunnel" in (status.last_event or "")


def test_remove_config_stops_and_deletes_files(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.save(TUNNEL_ID, API_KEY)
    service = _service(tmp_path, store=store)

    with patch.object(service.process_manager, "stop", return_value=ServiceActionResult(
        ok=True, status="stopped", message="arrêté", pid=None
    )):
        result = service.remove_config()

    assert result.ok is True
    assert result.config.configured is False
    assert not service.key_path.exists()
    assert not service.config_path.exists()


def test_validator_success_and_401_payloads() -> None:
    binary = FakeBinary(path=Path("tunnel-client"))
    success = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=json.dumps({"tunnel": {"name": "Production"}}),
        stderr="",
    )
    validator = TunnelClientValidator(binary, runner=lambda *args, **kwargs: success)
    result = validator.validate(TUNNEL_ID, API_KEY)
    assert result.ok is True
    assert result.name == "Production"

    unauthorized = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout=json.dumps(
            {
                "error": {
                    "code": "invalid_api_key",
                    "message": "Incorrect API key provided",
                    "status_code": 401,
                }
            }
        ),
        stderr="",
    )
    validator = TunnelClientValidator(binary, runner=lambda *args, **kwargs: unauthorized)
    denied = validator.validate(TUNNEL_ID, API_KEY)
    assert denied.ok is False
    assert "refusé" in denied.message
    assert denied.http_status == 400


def test_release_map_contains_pinned_assets() -> None:
    assets = RELEASES["0.0.18"]
    assert {"windows-amd64", "windows-arm64", "linux-amd64", "linux-arm64"} <= set(assets)
    for asset in assets.values():
        assert asset["url"].startswith("https://github.com/openai/tunnel-client/releases/")
        assert len(asset["sha256"]) == 64


def test_binary_manager_resolves_runtime_binary(tmp_path: Path) -> None:
    settings = _settings(tmp_path, command="definitely-not-installed-tunnel-client")
    manager = TunnelBinaryManager(settings)
    manager.auto_path.parent.mkdir(parents=True, exist_ok=True)
    manager.auto_path.write_bytes(b"fake")
    try:
        assert manager.resolve() == manager.auto_path
        status = manager.status()
        assert status.installed is True
        assert status.source == "runtime"
    finally:
        manager.auto_path.unlink(missing_ok=True)


def test_binary_extract_creates_runtime_directory(tmp_path: Path) -> None:
    settings = _settings(tmp_path, command="definitely-not-installed-tunnel-client")
    manager = TunnelBinaryManager(settings)
    archive = tmp_path / "release.zip"
    member = "tunnel-client.exe" if sys.platform == "win32" else "tunnel-client"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr(member, b"fake-binary")

    manager._extract(archive)

    assert manager.auto_path.exists()
    assert manager.auto_path.read_bytes() == b"fake-binary"
