from pathlib import Path

from app.core.config import Settings
from app.utils.redact import redact_text


def test_settings_rejects_non_local_hosts() -> None:
    raw = _settings_dict()
    raw["mcp"]["host"] = "0.0.0.0"

    try:
        Settings.model_validate(raw)
    except ValueError as exc:
        assert "127.0.0.1" in str(exc)
    else:
        raise AssertionError("mcp.host must reject non-local binds")


def test_redact_text_masks_sensitive_values() -> None:
    text = "email=user@example.com password=hunter2 token=abc Authorization: Bearer xyz"

    redacted = redact_text(text)

    assert "user@example.com" not in redacted
    assert "hunter2" not in redacted
    assert "abc" not in redacted
    assert "xyz" not in redacted
    assert "[REDACTED]" in redacted


def _settings_dict() -> dict[str, object]:
    return {
        "app": {"name": "GarminToGPT", "version": "0.3.2", "environment": "test"},
        "server": {"host": "127.0.0.1", "backend_port": 8000, "frontend_port": 3000},
        "mcp": {
            "host": "127.0.0.1",
            "port": 8080,
            "endpoint": "/mcp",
            "sse_endpoint": "/sse",
            "command": ["uvx", "garmin-mcp"],
            "proxy_command": ["uvx", "mcp-proxy"],
        },
        "garmin": {
            "auth_command": ["uvx", "garmin-mcp-auth"],
            "verify_command": ["uvx", "garmin-mcp-auth", "--verify"],
            "token_dir": str(Path("missing-token-dir")),
        },
        "cloudflare": {
            "mode": "quick",
            "local_url": "http://127.0.0.1:8080",
            "tunnel_name": "",
            "hostname": "",
            "command": "cloudflared",
        },
        "runtime": {
            "dir": "runtime",
            "pid_dir": "runtime/pids",
            "state_file": "runtime/state.json",
        },
        "logs": {"dir": "logs", "max_size_mb": 10, "retain_files": 5},
        "security": {
            "bind_local_only": True,
            "redact_sensitive_logs": True,
            "allow_write_tools": False,
        },
        "timeouts": {
            "process_start_seconds": 45,
            "process_stop_seconds": 15,
            "healthcheck_seconds": 1,
        },
    }
