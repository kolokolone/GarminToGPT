import json
import os
import subprocess
import threading
from os import environ
from pathlib import Path

from app.core.config import Settings
from app.models.common import ProcessStatus, ServiceActionResult
from app.utils.ports import is_port_open
from app.utils.redact import redact_text
from app.utils.time import utc_now_iso


class ProcessManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._processes: dict[str, subprocess.Popen[str]] = {}

    def pid_file(self, name: str) -> Path:
        return self.settings.runtime.pid_path / f"{name}.json"

    def log_file(self, name: str) -> Path:
        return self.settings.logs.path / f"{name}.log"

    def status(self, name: str) -> ProcessStatus:
        process = self._processes.get(name)
        if process and process.poll() is None:
            return ProcessStatus(status="running", pid=process.pid, message="Processus actif.")
        if process and process.poll() is not None:
            self._processes.pop(name, None)
            self.pid_file(name).unlink(missing_ok=True)
        if self.pid_file(name).exists():
            metadata = self._read_metadata(name)
            raw_pid = metadata.get("pid")
            pid = raw_pid if isinstance(raw_pid, int) else None
            return ProcessStatus(
                status="stopped",
                pid=pid,
                message="PID hérité détecté mais non contrôlé par cette instance backend.",
            )
        return ProcessStatus(status="stopped", pid=None, message="Processus arrêté.")

    def start(self, name: str, command: list[str], port: int | None = None) -> ServiceActionResult:
        current = self.status(name)
        if current.status == "running":
            return ServiceActionResult(
                ok=True,
                status="running",
                message="Service déjà actif.",
                pid=current.pid,
            )
        if port and is_port_open("127.0.0.1", port):
            message = (
                f"Le port {port} est déjà utilisé. Change la configuration "
                "ou arrête le service existant."
            )
            return ServiceActionResult(
                ok=False,
                status="error",
                message=message,
            )

        log_path = self.log_file(name)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        child_env = environ.copy()
        child_env.setdefault("PYTHONIOENCODING", "utf-8")
        child_env.setdefault("PYTHONUTF8", "1")
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=child_env,
                shell=False,
            )
        except FileNotFoundError as exc:
            return ServiceActionResult(
                ok=False,
                status="error",
                message=redact_text(f"Commande introuvable: {exc}"),
            )

        self._processes[name] = process
        self._write_metadata(name, process.pid, command)
        self._stream_output(name, process, log_path)
        return ServiceActionResult(
            ok=True,
            status="starting",
            message="Service lancé, healthcheck en cours.",
            pid=process.pid,
        )

    def stop(self, name: str) -> ServiceActionResult:
        process = self._processes.get(name)
        if not process or process.poll() is not None:
            self._processes.pop(name, None)
            self.pid_file(name).unlink(missing_ok=True)
            return ServiceActionResult(
                ok=True,
                status="stopped",
                message="Service déjà arrêté.",
            )

        self._stop_process_tree(process)
        self._processes.pop(name, None)
        self.pid_file(name).unlink(missing_ok=True)
        return ServiceActionResult(
            ok=True,
            status="stopped",
            message="Service arrêté proprement.",
        )

    def _stop_process_tree(self, process: subprocess.Popen[str]) -> None:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                check=False,
                capture_output=True,
                text=True,
            )
            try:
                process.wait(timeout=self.settings.timeouts.process_stop_seconds)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            return

        process.terminate()
        try:
            process.wait(timeout=self.settings.timeouts.process_stop_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    def _stream_output(self, name: str, process: subprocess.Popen[str], log_path: Path) -> None:
        def reader() -> None:
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(f"{utc_now_iso()} INFO service={name} event=start pid={process.pid}\n")
                handle.flush()
                if process.stdout:
                    for line in process.stdout:
                        handle.write(redact_text(line))
                        handle.flush()
                return_code = process.wait()
                handle.write(
                    f"{utc_now_iso()} INFO service={name} event=exit returncode={return_code}\n"
                )

        thread = threading.Thread(target=reader, name=f"{name}-log-reader", daemon=True)
        thread.start()

    def _write_metadata(self, name: str, pid: int, command: list[str]) -> None:
        self.pid_file(name).write_text(
            json.dumps(
                {"name": name, "pid": pid, "command": command, "started_at": utc_now_iso()},
                indent=2,
            ),
            encoding="utf-8",
        )

    def _read_metadata(self, name: str) -> dict[str, object]:
        try:
            return json.loads(self.pid_file(name).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
