"""Tests for McpService local control (start/stop/restart/status)."""

import sys

from app.core.config import Settings
from app.services.healthcheck_service import HealthcheckService
from app.services.mcp_service import McpService
from app.services.process_manager import ProcessManager

from .test_config_security import _settings_dict


def test_mcp_local_status_initially_stopped(tmp_path) -> None:
    raw = _settings_dict()
    raw["runtime"] = {
        "dir": str(tmp_path / "runtime"),
        "pid_dir": str(tmp_path / "runtime" / "pids"),
        "state_file": str(tmp_path / "runtime" / "state.json"),
    }
    raw["logs"] = {"dir": str(tmp_path / "logs"), "max_size_mb": 10, "retain_files": 5}
    settings = Settings.model_validate(raw)
    settings.ensure_directories()

    service = McpService(settings, ProcessManager(settings), HealthcheckService(settings))
    status = service.get_local_status()

    assert status.running is False
    assert status.status == "stopped"
    assert status.pid is None
    assert status.port == 8080
    assert status.last_started_at is None
    assert status.last_stopped_at is None
    assert status.last_error is None


def test_mcp_local_start_and_stop(tmp_path) -> None:
    raw = _settings_dict()
    raw["runtime"] = {
        "dir": str(tmp_path / "runtime"),
        "pid_dir": str(tmp_path / "runtime" / "pids"),
        "state_file": str(tmp_path / "runtime" / "state.json"),
    }
    raw["logs"] = {"dir": str(tmp_path / "logs"), "max_size_mb": 10, "retain_files": 5}
    settings = Settings.model_validate(raw)
    settings.ensure_directories()

    service = McpService(settings, ProcessManager(settings), HealthcheckService(settings))

    # start
    result = service.start_mcp_service()
    assert result.ok is True

    status = service.get_local_status()
    assert status.last_started_at is not None
    assert status.last_error is None

    # stop
    stop_result = service.stop_mcp_service()
    assert stop_result.ok is True

    status = service.get_local_status()
    assert status.running is False
    assert status.status == "stopped"
    assert status.last_stopped_at is not None


def test_mcp_local_start_is_idempotent(tmp_path) -> None:
    raw = _settings_dict()
    raw["runtime"] = {
        "dir": str(tmp_path / "runtime"),
        "pid_dir": str(tmp_path / "runtime" / "pids"),
        "state_file": str(tmp_path / "runtime" / "state.json"),
    }
    raw["logs"] = {"dir": str(tmp_path / "logs"), "max_size_mb": 10, "retain_files": 5}
    settings = Settings.model_validate(raw)
    settings.ensure_directories()

    service = McpService(settings, ProcessManager(settings), HealthcheckService(settings))

    # Premier démarrage
    r1 = service.start_mcp_service()
    assert r1.ok is True

    # Second démarrage = idempotent
    r2 = service.start_mcp_service()
    assert r2.ok is True
    assert r2.status == "running"  # déjà actif


def test_mcp_local_stop_is_idempotent(tmp_path) -> None:
    raw = _settings_dict()
    raw["runtime"] = {
        "dir": str(tmp_path / "runtime"),
        "pid_dir": str(tmp_path / "runtime" / "pids"),
        "state_file": str(tmp_path / "runtime" / "state.json"),
    }
    raw["logs"] = {"dir": str(tmp_path / "logs"), "max_size_mb": 10, "retain_files": 5}
    settings = Settings.model_validate(raw)
    settings.ensure_directories()

    service = McpService(settings, ProcessManager(settings), HealthcheckService(settings))

    # Arrêter alors que rien ne tourne
    r1 = service.stop_mcp_service()
    assert r1.ok is True
    assert r1.status == "stopped"

    # Démarrer puis arrêter proprement
    service.start_mcp_service()
    r2 = service.stop_mcp_service()
    assert r2.ok is True
    assert r2.status == "stopped"

    status = service.get_local_status()
    assert status.last_stopped_at is not None


def test_mcp_local_restart(tmp_path) -> None:
    raw = _settings_dict()
    raw["runtime"] = {
        "dir": str(tmp_path / "runtime"),
        "pid_dir": str(tmp_path / "runtime" / "pids"),
        "state_file": str(tmp_path / "runtime" / "state.json"),
    }
    raw["logs"] = {"dir": str(tmp_path / "logs"), "max_size_mb": 10, "retain_files": 5}
    settings = Settings.model_validate(raw)
    settings.ensure_directories()

    service = McpService(settings, ProcessManager(settings), HealthcheckService(settings))

    # Premier démarrage
    service.start_mcp_service()
    status_before = service.get_local_status()
    assert status_before.running is True

    # Restart
    result = service.restart_mcp_service()
    assert result.ok is True

    status = service.get_local_status()
    assert status.last_started_at is not None


MCP_COMMAND_NOT_FOUND = [sys.executable, "-c", "import sys; sys.exit(99)"]


def test_mcp_local_start_with_invalid_command(tmp_path) -> None:
    raw = _settings_dict()
    raw["runtime"] = {
        "dir": str(tmp_path / "runtime"),
        "pid_dir": str(tmp_path / "runtime" / "pids"),
        "state_file": str(tmp_path / "runtime" / "state.json"),
    }
    raw["logs"] = {"dir": str(tmp_path / "logs"), "max_size_mb": 10, "retain_files": 5}
    raw["mcp"]["proxy_command"] = ["commande-inexistante"]
    settings = Settings.model_validate(raw)
    settings.ensure_directories()

    service = McpService(settings, ProcessManager(settings), HealthcheckService(settings))

    result = service.start_mcp_service()
    assert result.ok is False

    status = service.get_local_status()
    assert status.running is False
    assert status.last_error is not None
