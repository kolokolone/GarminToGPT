import sys

from app.core.config import Settings
from app.services.process_manager import ProcessManager
from app.services.state_store import StateStore
from app.services.tunnel_service import TunnelService

from .test_config_security import _settings_dict


def test_cloudflare_url_parsing_and_chatgpt_url(tmp_path) -> None:
    raw = _settings_dict()
    raw["runtime"] = {
        "dir": str(tmp_path / "runtime"),
        "pid_dir": str(tmp_path / "runtime" / "pids"),
        "state_file": str(tmp_path / "runtime" / "state.json"),
    }
    raw["logs"] = {"dir": str(tmp_path / "logs"), "max_size_mb": 10, "retain_files": 5}
    settings = Settings.model_validate(raw)
    settings.ensure_directories()
    (settings.logs.path / "cloudflared.log").write_text(
        "INF https://abc-def.trycloudflare.com ready\n",
        encoding="utf-8",
    )

    service = TunnelService(settings, ProcessManager(settings), StateStore(settings))

    assert service._parse_cloudflared_logs_for_url() == "https://abc-def.trycloudflare.com"
    assert service.get_chatgpt_mcp_url() == "https://abc-def.trycloudflare.com/mcp"


def test_process_manager_starts_and_stops_owned_process(tmp_path) -> None:
    raw = _settings_dict()
    raw["runtime"] = {
        "dir": str(tmp_path / "runtime"),
        "pid_dir": str(tmp_path / "runtime" / "pids"),
        "state_file": str(tmp_path / "runtime" / "state.json"),
    }
    raw["logs"] = {"dir": str(tmp_path / "logs"), "max_size_mb": 10, "retain_files": 5}
    settings = Settings.model_validate(raw)
    settings.ensure_directories()
    manager = ProcessManager(settings)

    result = manager.start("sleepy", [sys.executable, "-c", "import time; time.sleep(30)"])
    assert result.ok is True
    assert manager.status("sleepy").status == "running"

    stopped = manager.stop("sleepy")
    assert stopped.ok is True
    assert manager.status("sleepy").status == "stopped"
