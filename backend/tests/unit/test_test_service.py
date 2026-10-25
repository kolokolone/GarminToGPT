"""Diagnostics definitions and MCP tool check behavior."""

from pathlib import Path

from app.core.config import Settings
from app.models.mcp import McpTool, McpToolClassification, McpToolsResult
from app.services.test_service import TestService as DiagnosticsService

from .test_config_security import _settings_dict


class FakeMcp:
    def __init__(self, *, ok: bool = True) -> None:
        self.ok = ok

    def list_mcp_tools(self) -> McpToolsResult:
        return McpToolsResult(
            ok=self.ok,
            message="MCP indisponible." if not self.ok else "MCP disponible.",
            tools=[McpTool(name="get_sleep", risk="read", reason="lecture")],
        )

    def classify_mcp_tools(self) -> McpToolClassification:
        return McpToolClassification(
            read_tools=["get_sleep"],
            write_tools=[],
            unknown_tools=[],
        )


def _settings(tmp_path: Path) -> Settings:
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


def test_current_diagnostic_ids(tmp_path: Path) -> None:
    service = DiagnosticsService(_settings(tmp_path), object(), FakeMcp(), object())
    ids = {definition.id for definition in service.list_tests().tests}

    assert "check_garmin_api_key" in ids
    assert "check_tunnel_ready" in ids
    assert "check_tunnel_configured" in ids
    assert "check_chatgpt_connector" in ids
    assert "check_tunnel_public_url" not in ids
    assert "check_remote_mcp_endpoint" not in ids
    assert "check_chatgpt_url_format" not in ids
    assert "full_smoke_test" in ids
    assert len(ids) == 14


def test_mcp_tools_check_fails_when_probe_fails(tmp_path: Path) -> None:
    service = DiagnosticsService(_settings(tmp_path), object(), FakeMcp(ok=False), object())

    ok, message, suggestion = service._check_mcp_tools()

    assert ok is False
    assert "indisponible" in message
    assert suggestion is not None
