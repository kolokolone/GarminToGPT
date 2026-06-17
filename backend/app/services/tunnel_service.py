import logging
import re
from datetime import datetime, timezone

from app.core.config import Settings
from app.models.tunnel import TunnelActionResult, TunnelStatus, TunnelUrlResult
from app.services.process_manager import ProcessManager
from app.services.state_store import StateStore

logger = logging.getLogger("GarminToGPT.tunnel")

URL_PATTERN = re.compile(r"https://[a-zA-Z0-9.-]+\.trycloudflare\.com")
_START_TS_KEY = "tunnel_start_ts"


class TunnelService:
    def __init__(
        self, settings: Settings, process_manager: ProcessManager, state: StateStore
    ) -> None:
        self.settings = settings
        self.process_manager = process_manager
        self.state = state
        self._current_url: str | None = None
        self._session_start_pos: int = 0

    # ------------------------------------------------------------------
    # Public actions
    # ------------------------------------------------------------------

    def ensure_tunnel(self) -> TunnelActionResult:
        """Idempotent: démarre le tunnel seulement s'il n'est ni running ni starting.

        Si le tunnel est déjà actif ou en cours de démarrage, ne fait rien
        et retourne le statut existant sans muter l'URL.
        """
        status = self.get_tunnel_status()
        if status.state in ("running", "starting"):
            logger.info(
                "Cloudflare tunnel already %s; reusing existing tunnel (URL: %s)",
                status.state,
                status.chatgpt_mcp_url or "not yet available",
            )
            return TunnelActionResult(
                ok=True,
                status=status.state,
                message=f"Tunnel déjà {status.state}.",
                pid=status.pid,
                public_url=status.public_url,
                chatgpt_mcp_url=status.chatgpt_mcp_url,
            )

        logger.info("Cloudflare tunnel missing/stopped; starting tunnel")
        return self.start_tunnel()

    def start_tunnel(self) -> TunnelActionResult:
        self._clear_current_url()

        if self.settings.cloudflare.mode == "named":
            command = [
                self.settings.cloudflare.command,
                "tunnel",
                "run",
                self.settings.cloudflare.tunnel_name,
            ]
        else:
            command = [
                self.settings.cloudflare.command,
                "tunnel",
                "--url",
                self.settings.cloudflare.local_url,
            ]
        result = self.process_manager.start("cloudflared", command, reset_log=True)

        # Enregistrer la position du fichier de log APRÈS start() →
        # toutes les lignes antérieures (anciennes sessions) sont ignorées
        self._session_start_pos = self._current_log_size()

        return TunnelActionResult(
            ok=result.ok,
            status=result.status,
            message=result.message,
            pid=result.pid,
            public_url=None,
            chatgpt_mcp_url=None,
        )

    def stop_tunnel(self) -> TunnelActionResult:
        result = self.process_manager.stop("cloudflared")
        self.state.set_value("tunnel_paused", False)
        self._current_url = None
        return TunnelActionResult(
            ok=result.ok,
            status="stopped",
            message=result.message,
            pid=result.pid,
            public_url=None,
            chatgpt_mcp_url=None,
        )

    def pause_tunnel(self) -> TunnelActionResult:
        result = self.process_manager.stop("cloudflared")
        self.state.set_value("tunnel_paused", True)
        return TunnelActionResult(
            ok=result.ok,
            status="paused",
            message="Tunnel mis en pause. L'URL publique n'est plus active.",
            public_url=None,
            chatgpt_mcp_url=None,
        )

    def resume_tunnel(self) -> TunnelActionResult:
        self.state.set_value("tunnel_paused", False)
        return self.start_tunnel()

    def regenerate_tunnel(self) -> TunnelActionResult:
        self.stop_tunnel()
        return self.start_tunnel()

    # ------------------------------------------------------------------
    # Status / URL readout
    # ------------------------------------------------------------------

    def get_tunnel_status(self) -> TunnelStatus:
        process = self.process_manager.status("cloudflared")
        paused = bool(self.state.read().get("tunnel_paused"))
        public_url = self._get_public_url()
        state = "paused" if paused else process.status
        if state == "unhealthy":
            state = "error"
        if state == "running" and not public_url and self.settings.cloudflare.mode == "quick":
            state = "starting"
        return TunnelStatus(
            state=state,
            mode=self.settings.cloudflare.mode,
            public_url=public_url,
            chatgpt_mcp_url=self._get_chatgpt_mcp_url(),
            pid=process.pid,
            last_event=self._detect_cloudflare_error() or process.message,
            process=process,
        )

    def get_url_result(self) -> TunnelUrlResult:
        public_url = self._get_public_url()
        return TunnelUrlResult(
            public_url=public_url,
            chatgpt_mcp_url=self._get_chatgpt_mcp_url(),
            message="URL Cloudflare active." if public_url else "Aucune URL Cloudflare détectée.",
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _clear_current_url(self) -> None:
        """Reset cached URL and mark a new session start in state."""
        self._current_url = None
        self._session_start_pos = 0
        state_data = self.state.read()
        state_data.pop("cloudflare_public_url", None)
        state_data[_START_TS_KEY] = datetime.now(timezone.utc).isoformat()  # noqa: UP017 – Python <3.11
        self.state.write(state_data)

    def _get_public_url(self) -> str | None:
        # Cache chaud : déjà trouvée dans cette session
        if self._current_url:
            return self._current_url

        # Mode nommé : toujours utiliser le hostname configuré
        if self.settings.cloudflare.mode == "named" and self.settings.cloudflare.hostname:
            url = f"https://{self.settings.cloudflare.hostname}".rstrip("/")
            self._current_url = url
            return url

        # Mode quick : ne retourner une URL que si cloudflared tourne
        proc = self.process_manager.status("cloudflared")
        if proc.status != "running":
            return None

        url = self._parse_cloudflared_logs_for_url()
        if url:
            self._current_url = url
            self.state.set_value("cloudflare_public_url", url)
        return url

    def _get_chatgpt_mcp_url(self) -> str | None:
        public_url = self._get_public_url()
        if not public_url:
            return None
        return f"{public_url.rstrip('/')}{self.settings.mcp.endpoint}"

    def _current_log_size(self) -> int:
        log_path = self.settings.logs.path / "cloudflared.log"
        if log_path.exists():
            return log_path.stat().st_size
        return 0

    def _parse_cloudflared_logs_for_url(self) -> str | None:
        """Parcourt le log cloudflared à partir de _session_start_pos
        et retourne la dernière URL trycloudflare trouvée."""
        log_path = self.settings.logs.path / "cloudflared.log"
        if not log_path.exists():
            return None

        with log_path.open("r", encoding="utf-8", errors="replace") as f:
            f.seek(self._session_start_pos)
            text = f.read()

        matches = URL_PATTERN.findall(text)
        return matches[-1].rstrip("/") if matches else None

    def _detect_cloudflare_error(self) -> str | None:
        log_path = self.settings.logs.path / "cloudflared.log"
        if not log_path.exists():
            return None
        tail = "\n".join(log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-200:])
        for marker in (
            "1033",
            "530",
            "connection refused",
            "origin service unavailable",
            "tunnel expired",
        ):
            if marker.lower() in tail.lower():
                return f"Erreur Cloudflare détectée: {marker}"
        return None
