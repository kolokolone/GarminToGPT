"""Process manager and environment-overlay tests."""

import sys
import time
from pathlib import Path

from app.core.config import Settings
from app.services.process_manager import ProcessManager

from .test_config_security import _settings_dict


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


def test_process_manager_starts_and_stops_owned_process(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    manager = ProcessManager(settings)

    result = manager.start("sleepy", [sys.executable, "-c", "import time; time.sleep(30)"])
    assert result.ok is True
    assert manager.status("sleepy").status == "running"

    stopped = manager.stop("sleepy")
    assert stopped.ok is True
    assert manager.status("sleepy").status == "stopped"


def test_process_manager_passes_environment_overlay(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    manager = ProcessManager(settings)
    marker = tmp_path / "env.txt"
    script = (
        "import os, pathlib, time; "
        f"pathlib.Path(r'{marker}').write_text(os.environ.get('TUNNEL_TEST_ENV', '')); "
        "time.sleep(0.2)"
    )

    result = manager.start(
        "envtest",
        [sys.executable, "-c", script],
        env={"TUNNEL_TEST_ENV": "openai"},
    )
    assert result.ok is True

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and not marker.exists():
        time.sleep(0.05)
    assert marker.read_text(encoding="utf-8") == "openai"

    manager.stop("envtest")
