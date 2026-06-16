import json
import os
import re
import subprocess
import threading
from os import environ
from pathlib import Path

from app.core.config import Settings
from app.models.common import ProcessStatus, ServiceActionResult
from app.utils.ports import is_port_open
from app.utils.redact import redact_text
from app.utils.time import utc_now_iso

_MCP_PROXY_WANTED = re.compile(r"mcp-proxy.*Taxuspt/garmin_mcp", re.IGNORECASE)


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
            # V1-style detection: vérifier si le processus occupant le port est
            # un mcp-proxy compatible avec Taxuspt/garmin_mcp
            if name == "mcp" and self._is_compatible_mcp_proxy(port):
                return ServiceActionResult(
                    ok=True,
                    status="running",
                    message=(
                        f"Le port {port} est déjà utilisé par un mcp-proxy compatible. "
                        "Réutilisation du processus existant."
                    ),
                )
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

    def _is_compatible_mcp_proxy(self, port: int) -> bool:
        """V1-style detection: vérifie si le processus sur le port est
        un mcp-proxy compatible avec Taxuspt/garmin_mcp."""
        import logging
        logger = logging.getLogger("garmintogpt.process_manager")

        if os.name != "nt":
            # Sur Linux/macOS, on tente de lire /proc/<pid>/cmdline
            return self._is_compatible_mcp_proxy_posix(port)

        try:
            # Étape 1: Get-NetTCPConnection pour trouver l'OwningProcess
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    f"Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort {port} -State Listen | "
                    "Select-Object -First 1 | Format-List OwningProcess",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode != 0:
                return False
            pid_match = re.search(r"OwningProcess\s*:\s*(\d+)", result.stdout)
            if not pid_match:
                return False
            pid = int(pid_match.group(1))

            # Étape 2: Get-CimInstance Win32_Process pour récupérer la ligne de commande
            result2 = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    f"Get-CimInstance Win32_Process -Filter 'ProcessId={pid}' | "
                    "Format-List CommandLine",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result2.returncode != 0:
                return False
            cmdline = result2.stdout
            logger.info("Port %d occupé par PID %d – cmdline: %s", port, pid, cmdline[:300])

            # Vérification: mcp-proxy et Taxuspt/garmin_mcp
            if _MCP_PROXY_WANTED.search(cmdline):
                logger.info(
                    "Port %d – mcp-proxy compatible détecté (PID %d), réutilisation.",
                    port,
                    pid,
                )
                return True
            logger.warning("Port %d occupé par un processus incompatible (PID %d)", port, pid)
            return False

        except subprocess.TimeoutExpired:
            logger.warning("Détection de processus sur le port %d a expiré", port)
            return False
        except Exception as exc:
            logger.error("Erreur lors de la détection de processus sur le port %d: %s", port, exc)
            return False

    @staticmethod
    def _is_compatible_mcp_proxy_posix(port: int) -> bool:
        """Fallback POSIX: utilise ss/lsof + /proc/pid/cmdline."""
        import logging
        logger = logging.getLogger("garmintogpt.process_manager")
        try:
            # Trouver le PID via ss
            result = subprocess.run(
                ["ss", "-tlnp", f"sport = :{port}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            pid_match = re.search(r"pid=(\d+)", result.stdout)
            if not pid_match:
                return False
            pid = pid_match.group(1)
            try:
                cmdline = Path(f"/proc/{pid}/cmdline").read_text(encoding="utf-8", errors="replace")
            except OSError:
                # fallback: ps
                result2 = subprocess.run(
                    ["ps", "-p", pid, "-o", "args="],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                cmdline = result2.stdout or ""
            if _MCP_PROXY_WANTED.search(cmdline):
                logger.info("Port %d – mcp-proxy compatible détecté (PID %s), réutilisation.", port, pid)
                return True
            return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
        except Exception as exc:
            logger.warning("Erreur detection POSIX port %d: %s", port, exc)
            return False

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
