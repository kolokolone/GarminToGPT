from pathlib import Path

import yaml
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
    key = "GCDC_" + "a1b2c3d4" * 10
    token = "eyJhbGciOiJub25lIn0.eyJleHAiOjE3OTMwMzMwNDF9.signature"
    openai_key = "sk-test-runtime-key-1234567890"
    text = (
        "email=user@example.com password=hunter2 token=abc "
        f"Authorization: Bearer xyz Authorization: ApiKey {key} api_key={key} {token} "
        f"OpenAI {openai_key}"
    )

    redacted = redact_text(text)

    assert "user@example.com" not in redacted
    assert "hunter2" not in redacted
    assert "abc" not in redacted
    assert "xyz" not in redacted
    assert key not in redacted
    assert token not in redacted
    assert openai_key not in redacted
    assert "[REDACTED]" in redacted


def test_local_garmin_key_file_is_gitignored() -> None:
    project_root = Path(__file__).resolve().parents[3]
    ignore = (project_root / ".gitignore").read_text(encoding="utf-8")
    assert "garmin.env" in ignore


def test_packaged_mcp_commands_use_the_official_personal_api_adapter() -> None:
    project_root = Path(__file__).resolve().parents[3]

    for config_name in ("app.yaml", "app.example.yaml"):
        with (project_root / "config" / config_name).open(encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file)

        command = config["mcp"]["command"]
        proxy_command = config["mcp"]["proxy_command"]
        inner_command = proxy_command[proxy_command.index("--") + 1 :]

        assert "garmin-personal-mcp==0.1.1" in command
        assert "garmin-personal-mcp==0.1.1" in inner_command
        assert "--pass-environment" in proxy_command
        assert "Taxuspt/garmin_mcp" not in " ".join(command)
        assert "Taxuspt/garmin_mcp" not in " ".join(proxy_command)
        assert "auth_command" not in config["garmin"]
        assert "token_dir" not in config["garmin"]

        proxy_executable_index = proxy_command.index("mcp-proxy")
        assert proxy_command[:proxy_executable_index] == [
            "uvx",
            "--python",
            "3.12",
            "--from",
            "mcp-proxy==0.12.0",
            "--with",
            "mcp>=1.28.1,<2",
        ]


def _settings_dict() -> dict[str, object]:
    return {
        "app": {"name": "GarminToGPT", "version": "1.1.0", "environment": "test"},
        "server": {"host": "127.0.0.1", "backend_port": 8000, "frontend_port": 3000},
        "mcp": {
            "host": "127.0.0.1",
            "port": 8080,
            "endpoint": "/mcp",
            "sse_endpoint": "/sse",
            "command": ["uvx", "garmin-personal-mcp"],
            "proxy_command": ["uvx", "mcp-proxy"],
        },
        "garmin": {"rotation_warning_days": 7, "timeout_seconds": 5},
        "tunnel": {
            "provider": "openai",
            "command": "tunnel-client",
            "health_host": "127.0.0.1",
            "health_port": 8091,
            "mcp_server_url": "http://127.0.0.1:8080/mcp",
            "connector_url": "https://chatgpt.com/#settings/Connectors",
            "tunnels_page_url": "https://platform.openai.com/settings/organization/tunnels",
            "api_keys_page_url": "https://platform.openai.com/settings/organization/api-keys",
            "ready_timeout_seconds": 30,
            "binary_version": "0.0.18",
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
