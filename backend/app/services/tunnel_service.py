"""Orchestration for the OpenAI Secure MCP Tunnel client.

The client is an outbound-only long-poll daemon: it forwards MCP requests from
OpenAI to the local ``mcp-proxy``. There is no public URL. ChatGPT selects the
tunnel in ``Settings → Connectors → Connection: Tunnel`` using the tunnel ID.

Health is read from the client's local ``/readyz`` endpoint; no URL log
parsing or public endpoint is involved.
"""

from __future__ import annotations

import hmac
import logging
from pathlib import Path

import httpx

from app.core.config import Settings
from app.models.tunnel import (
    TunnelActionResult,
    TunnelBinaryResult,
    TunnelConfigResult,
    TunnelConfigStatus,
    TunnelState,
    TunnelStatus,
)
from app.openai_tunnel import (
    OpenAITunnelConfigStore,
    TunnelBinaryError,
    TunnelBinaryManager,
    TunnelClientValidator,
    TunnelValidationError,
)
from app.services.process_manager import ProcessManager

logger = logging.getLogger("GarminToGPT.tunnel")

_PROCESS_NAME = "tunnel"


class TunnelService:
    def __init__(
        self,
        settings: Settings,
        process_manager: ProcessManager,
        *,
        store: OpenAITunnelConfigStore | None = None,
        binary: TunnelBinaryManager | None = None,
        validator: TunnelClientValidator | None = None,
    ) -> None:
        self.settings = settings
        self.process_manager = process_manager
        self.store = store or OpenAITunnelConfigStore()
        self.binary = binary or TunnelBinaryManager(settings)
        self.validator = validator or TunnelClientValidator(self.binary)

    # -- configuration -----------------------------------------------------

    def get_config_status(self) -> TunnelConfigStatus:
        config = self.store.load()
        binary = self.binary.status()
        if config.configured and not config.editable:
            message = "Tunnel OpenAI configuré par l'environnement."
        elif config.configured:
            message = "Tunnel OpenAI configuré."
        else:
            message = "Tunnel OpenAI non configuré. Renseigne le tunnel ID et la runtime API key."
        return TunnelConfigStatus(
            configured=config.configured,
            tunnel_id=config.tunnel_id,
            key_hint=self.store.hint(config.api_key),
            source=config.source,
            key_source=config.key_source,
            tunnel_id_source=config.tunnel_id_source,
            editable=config.editable,
            binary_installed=binary.installed,
            binary_version=binary.version,
            message=message,
        )

    def configure(self, tunnel_id: str, api_key: str) -> TunnelConfigResult:
        normalized_id = self.store.validate_tunnel_id(tunnel_id)
        normalized_key = self.store.validate_api_key(api_key)
        previous = self.store.load()
        same = (
            previous.tunnel_id == normalized_id
            and previous.api_key is not None
            and hmac.compare_digest(previous.api_key, normalized_key)
        )

        validation = self.validator.validate(normalized_id, normalized_key)
        if not validation.ok:
            raise TunnelValidationError(
                validation.message,
                http_status=validation.http_status,
            )

        self.store.save(normalized_id, normalized_key)
        if not same and self.get_tunnel_status().state in {"running", "starting"}:
            self.restart_tunnel()

        name = f" ({validation.name})" if validation.name else ""
        return TunnelConfigResult(
            ok=True,
            changed=not same,
            message=f"Tunnel OpenAI validé et enregistré{name}.",
            config=self.get_config_status(),
            status=self.get_tunnel_status(),
        )

    def remove_config(self) -> TunnelConfigResult:
        self.stop_tunnel()
        deleted = self.store.clear()
        config = self.get_config_status()
        if config.configured:
            message = (
                "Fichiers locaux supprimés, mais l'environnement OpenAI reste "
                "prioritaire. Retire CONTROL_PLANE_TUNNEL_ID / CONTROL_PLANE_API_KEY."
            )
        else:
            message = "Configuration du tunnel OpenAI supprimée."
        return TunnelConfigResult(
            ok=True,
            changed=deleted,
            message=message,
            config=config,
            status=self.get_tunnel_status(),
        )

    def install_binary(self) -> TunnelBinaryResult:
        try:
            binary = self.binary.ensure()
        except TunnelBinaryError as exc:
            logger.error("Tunnel client installation failed: %s", exc)
            return TunnelBinaryResult(ok=False, installed=False, message=str(exc))
        return TunnelBinaryResult(
            ok=True,
            installed=True,
            version=binary.version,
            path=str(binary.path),
            message="Client tunnel OpenAI installé.",
        )

    # -- actions -----------------------------------------------------------

    def ensure_tunnel(self) -> TunnelActionResult:
        status = self.get_tunnel_status()
        if status.state in {"running", "starting"}:
            logger.info("OpenAI tunnel already %s; reusing it", status.state)
            return self._action(
                ok=True,
                message=f"Tunnel OpenAI déjà {status.state}.",
                state=status.state,
                pid=status.pid,
            )
        if not status.configured:
            return self._action(
                ok=False,
                message=(
                    "Tunnel OpenAI non configuré. Ouvre /tunnel pour renseigner "
                    "le tunnel ID et la runtime API key."
                ),
                state="error",
            )
        return self.start_tunnel()

    def start_tunnel(self) -> TunnelActionResult:
        config = self.store.load()
        if not config.configured or not config.tunnel_id or not config.api_key:
            return self._action(
                ok=False,
                message=(
                    "Tunnel OpenAI non configuré. Ouvre /tunnel pour renseigner "
                    "le tunnel ID et la runtime API key."
                ),
                state="error",
            )

        try:
            binary = self.binary.ensure()
        except TunnelBinaryError as exc:
            logger.error("Tunnel client unavailable: %s", exc)
            return self._action(ok=False, message=str(exc), state="error")

        command = [
            str(binary.path),
            "run",
            "--control-plane.tunnel-id",
            config.tunnel_id,
            "--control-plane.api-key",
            "env:CONTROL_PLANE_API_KEY",
            "--mcp.server-url",
            f"url={self.mcp_server_url},channel=main",
            "--mcp.startup-wait-timeout",
            f"{self.settings.tunnel.mcp_startup_timeout_seconds}s",
            "--health.listen-addr",
            f"{self.settings.tunnel.health_host}:{self.settings.tunnel.health_port}",
            "--log.format",
            "struct-text",
            "--log.level",
            "warn",
        ]
        result = self.process_manager.start(
            _PROCESS_NAME,
            command,
            port=self.settings.tunnel.health_port,
            reset_log=True,
            env={
                "CONTROL_PLANE_API_KEY": config.api_key,
                "CONTROL_PLANE_TUNNEL_ID": config.tunnel_id,
            },
        )
        if result.ok:
            logger.info("OpenAI tunnel starting (PID %s)", result.pid)
        else:
            logger.error("OpenAI tunnel failed to start: %s", result.message)
        return self._action(
            ok=result.ok,
            message=(
                "Tunnel OpenAI en cours de démarrage. En attente de /readyz."
                if result.ok
                else result.message
            ),
            state="starting" if result.ok else "error",
            pid=result.pid,
        )

    def stop_tunnel(self) -> TunnelActionResult:
        result = self.process_manager.stop(_PROCESS_NAME)
        logger.info("OpenAI tunnel stopped")
        return self._action(
            ok=result.ok,
            message="Tunnel OpenAI arrêté.",
            state="stopped",
            pid=result.pid,
        )

    def restart_tunnel(self) -> TunnelActionResult:
        self.stop_tunnel()
        return self.start_tunnel()

    # -- status ------------------------------------------------------------

    def get_tunnel_status(self) -> TunnelStatus:
        config = self.store.load()
        binary = self.binary.status()
        process = self.process_manager.status(_PROCESS_NAME)
        ready = False
        health_status: int | None = None
        health_message = process.message

        if process.status == "running":
            ready, health_status, health_message = self._check_ready()

        if process.status == "running":
            state = "running" if ready else "starting"
        elif process.status == "error":
            state = "error"
        else:
            state = "stopped"

        if not config.configured:
            health_message = (
                "Tunnel OpenAI non configuré. Ouvre /tunnel pour renseigner "
                "le tunnel ID et la runtime API key."
            )

        base_url = self.health_base_url
        return TunnelStatus(
            state=state,
            provider="openai",
            configured=config.configured,
            tunnel_id=config.tunnel_id,
            api_key_configured=bool(config.api_key),
            binary_installed=binary.installed,
            binary_version=binary.version,
            ready=ready,
            health_status=health_status,
            health_url=f"{base_url}/readyz",
            ui_url=f"{base_url}/ui",
            connector_url=self.settings.tunnel.connector_url,
            pid=process.pid,
            last_event=health_message,
            process=process,
        )

    # -- properties --------------------------------------------------------

    @property
    def mcp_server_url(self) -> str:
        return self.settings.tunnel.mcp_server_url or (
            f"http://{self.settings.mcp.host}:{self.settings.mcp.port}"
            f"{self.settings.mcp.endpoint}"
        )

    @property
    def health_base_url(self) -> str:
        return (
            f"http://{self.settings.tunnel.health_host}:"
            f"{self.settings.tunnel.health_port}"
        )

    @property
    def connector_url(self) -> str:
        return self.settings.tunnel.connector_url

    # -- helpers -----------------------------------------------------------

    def _check_ready(self) -> tuple[bool, int | None, str]:
        try:
            response = httpx.get(
                f"{self.health_base_url}/readyz",
                timeout=min(3, self.settings.timeouts.healthcheck_seconds),
            )
        except httpx.RequestError as exc:
            return False, None, f"En attente de /readyz: {exc}"

        if response.status_code == 200:
            return True, 200, "Tunnel OpenAI prêt."
        detail = " ".join(response.text.split())[:200]
        return (
            False,
            response.status_code,
            f"/readyz HTTP {response.status_code}" + (f": {detail}" if detail else ""),
        )

    @staticmethod
    def _action(
        *,
        ok: bool,
        message: str,
        state: TunnelState,
        pid: int | None = None,
    ) -> TunnelActionResult:
        return TunnelActionResult(
            ok=ok,
            status=state,
            message=message,
            pid=pid,
            state=state,
        )

    @property
    def key_path(self) -> Path:
        return self.store.key_file

    @property
    def config_path(self) -> Path:
        return self.store.config_file
