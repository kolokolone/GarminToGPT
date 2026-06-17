import asyncio
import logging

from app.core.config import Settings
from app.models.common import HealthcheckResult
from app.models.mcp import (
    McpLocalStatus,
    McpProbeResult,
    McpStatus,
    McpTool,
    McpToolClassification,
    McpToolsResult,
)
from app.services.healthcheck_service import HealthcheckService
from app.services.mcp_probe_service import probe_mcp_endpoint
from app.services.process_manager import ProcessManager
from app.utils.time import utc_now_iso

logger = logging.getLogger("GarminToGPT.mcp")

WRITE_PREFIXES = ("add_", "set_", "delete_", "remove_", "upload_", "schedule_", "unschedule_")


class McpService:
    def __init__(
        self,
        settings: Settings,
        process_manager: ProcessManager,
        healthchecks: HealthcheckService,
    ) -> None:
        self.settings = settings
        self.process_manager = process_manager
        self.healthchecks = healthchecks
        self._last_probe: McpProbeResult | None = None
        self._last_started_at: str | None = None
        self._last_stopped_at: str | None = None
        self._last_error: str | None = None

    @property
    def local_url(self) -> str:
        return (
            f"http://{self.settings.mcp.host}:{self.settings.mcp.port}{self.settings.mcp.endpoint}"
        )

    @property
    def base_mcp_url(self) -> str:
        return f"http://{self.settings.mcp.host}:{self.settings.mcp.port}"

    def start_mcp_service(self):
        command = self.settings.mcp.proxy_command or self.settings.mcp.command
        result = self.process_manager.start(
            "mcp", command, port=self.settings.mcp.port, reset_log=True
        )
        if result.ok:
            self._last_started_at = utc_now_iso()
            self._last_error = None
            logger.info("MCP proxy starting (PID %s)", result.pid)
        else:
            self._last_error = result.message
            logger.error("MCP proxy failed to start: %s", result.message)
        return result

    def stop_mcp_service(self):
        logger.info("MCP proxy stopping")
        result = self.process_manager.stop("mcp")
        if result.ok and result.status == "stopped":
            self._last_stopped_at = utc_now_iso()
            self._last_started_at = None
            logger.info("MCP proxy stopped")
        return result

    def restart_mcp_service(self):
        self.stop_mcp_service()
        return self.start_mcp_service()

    def get_local_status(self) -> McpLocalStatus:
        process = self.process_manager.status("mcp")
        status: str
        if process.status == "running":
            # Vérifier que le PID est toujours vivant
            if process.pid and not self._pid_alive(process.pid):
                self._last_error = (
                    f"Processus MCP mort (PID {process.pid}) mais port "
                    "peut-être encore occupé."
                )
                status = "error"
            else:
                status = "running"
        elif process.status == "starting":
            status = "starting"
        elif process.status == "stopped":
            status = "stopped"
        else:
            status = "error"
            if not self._last_error:
                self._last_error = process.message

        return McpLocalStatus(
            running=(status == "running"),
            status=status,  # type: ignore[arg-type]
            pid=process.pid,
            port=self.settings.mcp.port,
            last_started_at=self._last_started_at,
            last_stopped_at=self._last_stopped_at,
            last_error=self._last_error,
        )

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        """Vérifie si un PID est vivant (cross-platform)."""
        import os as _os
        import subprocess as _sp
        try:
            if _os.name == "nt":
                _sp.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, timeout=5)
                return True
            _os.kill(pid, 0)
            return True
        except (OSError, _sp.SubprocessError):
            return False

    def get_mcp_status(self) -> McpStatus:
        process = self.process_manager.status("mcp")
        healthcheck: HealthcheckResult | None = None
        state = process.status
        if process.status == "running":
            healthcheck = self.healthcheck_mcp()
            state = "running" if healthcheck.ok else "unhealthy"
        return McpStatus(
            state=state,
            host=self.settings.mcp.host,
            port=self.settings.mcp.port,
            endpoint=self.settings.mcp.endpoint,
            local_url=self.local_url,
            process=process,
            healthcheck=healthcheck,
        )

    def healthcheck_mcp(self) -> HealthcheckResult:
        """Vrai healthcheck MCP via probe JSON-RPC (plus de simple GET)."""
        probe = self._run_probe()
        self._last_probe = probe
        if probe.error:
            return HealthcheckResult(
                ok=False,
                target=self.local_url,
                message=probe.error,
            )
        return HealthcheckResult(
            ok=True,
            target=self.local_url,
            message=(
                f"MCP OK – {probe.tools_count} outil(s), "
                f"serveur {probe.server_name or 'inconnu'}"
            ),
        )

    def list_mcp_tools(self) -> McpToolsResult:
        """Interroge le vrai serveur MCP via JSON-RPC tools/list."""
        probe = self._run_probe()
        if not probe.ok:
            return McpToolsResult(
                ok=False,
                message=probe.error or "Impossible d'interroger le serveur MCP.",
                tools=[],
            )
        classified = [self._classify_tool(t.get("name", "?")) for t in probe.tools]
        return McpToolsResult(
            ok=True,
            message=f"{probe.tools_count} outil(s) réel(s) exposé(s) par le serveur.",
            tools=classified,
        )

    def classify_mcp_tools(self) -> McpToolClassification:
        tools = self.list_mcp_tools().tools
        return McpToolClassification(
            read_tools=[tool.name for tool in tools if tool.risk == "read"],
            write_tools=[tool.name for tool in tools if tool.risk == "write"],
            unknown_tools=[tool.name for tool in tools if tool.risk == "unknown"],
        )

    def get_raw_tools(self) -> list[dict]:
        """Retourne les outils bruts (nom + description + input_schema) pour l'UI."""
        probe = self._run_probe()
        if not probe.ok:
            return []
        return probe.tools

    def _run_probe(self) -> McpProbeResult:
        """Exécute le probe MCP (synchrone mais appelant du code async).

        Gère trois cas de figure événementiel :
        - Thread avec une boucle qui tourne (uvicorn main thread)
          → ``run_coroutine_threadsafe``
        - Thread avec une boucle mais qui ne tourne pas (tests unitaires)
          → ``asyncio.run``
        - Thread AnyIO / worker sans boucle du tout
          → ``asyncio.run`` (lève la sienne)
        """
        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # Aucune boucle dans ce thread (AnyIO worker thread p. ex.)
                return asyncio.run(
                    probe_mcp_endpoint(
                        self.base_mcp_url,
                        timeout_seconds=self.settings.timeouts.healthcheck_seconds,
                    ),
                )

            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    probe_mcp_endpoint(
                        self.base_mcp_url,
                        timeout_seconds=self.settings.timeouts.healthcheck_seconds,
                    ),
                    loop,
                )
                return future.result(timeout=self.settings.timeouts.healthcheck_seconds + 5)

            return asyncio.run(
                probe_mcp_endpoint(
                    self.base_mcp_url,
                    timeout_seconds=self.settings.timeouts.healthcheck_seconds,
                ),
            )
        except Exception as exc:
            logger.error("MCP probe failed: %s", exc)
            return McpProbeResult(
                ok=False,
                status="error",
                error=str(exc),
                final_url=self.base_mcp_url,
            )

    @staticmethod
    def _classify_tool(name: str) -> McpTool:
        if name.startswith(WRITE_PREFIXES):
            return McpTool(name=name, risk="write", reason="Préfixe d'action modifiante détecté.")
        if name.startswith("get_") or name.startswith("count_"):
            return McpTool(name=name, risk="read", reason="Préfixe de lecture détecté.")
        return McpTool(name=name, risk="unknown", reason="Risque non déterminé automatiquement.")
