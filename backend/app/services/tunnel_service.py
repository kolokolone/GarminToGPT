import re

from app.core.config import Settings
from app.models.tunnel import TunnelActionResult, TunnelStatus, TunnelUrlResult
from app.services.process_manager import ProcessManager
from app.services.state_store import StateStore

URL_PATTERN = re.compile(r"https://[a-zA-Z0-9.-]+\.trycloudflare\.com")


class TunnelService:
    def __init__(
        self, settings: Settings, process_manager: ProcessManager, state: StateStore
    ) -> None:
        self.settings = settings
        self.process_manager = process_manager
        self.state = state

    def start_tunnel(self) -> TunnelActionResult:
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
        result = self.process_manager.start("cloudflared", command)
        url = self.get_public_url()
        return TunnelActionResult(
            ok=result.ok,
            status=result.status,
            message=result.message,
            pid=result.pid,
            public_url=url,
            chatgpt_mcp_url=self.get_chatgpt_mcp_url(),
        )

    def stop_tunnel(self) -> TunnelActionResult:
        result = self.process_manager.stop("cloudflared")
        self.state.set_value("tunnel_paused", False)
        return TunnelActionResult(
            ok=result.ok,
            status="stopped",
            message=result.message,
            pid=result.pid,
            public_url=self.get_public_url(),
            chatgpt_mcp_url=self.get_chatgpt_mcp_url(),
        )

    def pause_tunnel(self) -> TunnelActionResult:
        result = self.process_manager.stop("cloudflared")
        self.state.set_value("tunnel_paused", True)
        return TunnelActionResult(
            ok=result.ok,
            status="paused",
            message="Tunnel mis en pause. L'URL publique n'est plus active.",
            public_url=self.get_public_url(),
            chatgpt_mcp_url=self.get_chatgpt_mcp_url(),
        )

    def resume_tunnel(self) -> TunnelActionResult:
        self.state.set_value("tunnel_paused", False)
        return self.start_tunnel()

    def regenerate_tunnel(self) -> TunnelActionResult:
        self.stop_tunnel()
        return self.start_tunnel()

    def get_tunnel_status(self) -> TunnelStatus:
        process = self.process_manager.status("cloudflared")
        paused = bool(self.state.read().get("tunnel_paused"))
        public_url = self.get_public_url()
        state = "paused" if paused else process.status
        if state == "unhealthy":
            state = "error"
        if state == "running" and not public_url and self.settings.cloudflare.mode == "quick":
            state = "starting"
        return TunnelStatus(
            state=state,
            mode=self.settings.cloudflare.mode,
            public_url=public_url,
            chatgpt_mcp_url=self.get_chatgpt_mcp_url(),
            pid=process.pid,
            last_event=self.detect_cloudflare_error() or process.message,
            process=process,
        )

    def get_public_url(self) -> str | None:
        if self.settings.cloudflare.mode == "named" and self.settings.cloudflare.hostname:
            return f"https://{self.settings.cloudflare.hostname}".rstrip("/")
        url = self.parse_cloudflared_logs_for_url()
        if url:
            self.state.set_value("cloudflare_public_url", url)
            return url
        value = self.state.read().get("cloudflare_public_url")
        return str(value) if value else None

    def get_chatgpt_mcp_url(self) -> str | None:
        public_url = self.get_public_url()
        if not public_url:
            return None
        return f"{public_url.rstrip('/')}{self.settings.mcp.endpoint}"

    def parse_cloudflared_logs_for_url(self) -> str | None:
        log_path = self.settings.logs.path / "cloudflared.log"
        if not log_path.exists():
            return None
        matches = URL_PATTERN.findall(log_path.read_text(encoding="utf-8", errors="replace"))
        return matches[-1].rstrip("/") if matches else None

    def get_url_result(self) -> TunnelUrlResult:
        public_url = self.get_public_url()
        return TunnelUrlResult(
            public_url=public_url,
            chatgpt_mcp_url=self.get_chatgpt_mcp_url(),
            message="URL Cloudflare active." if public_url else "Aucune URL Cloudflare détectée.",
        )

    def detect_cloudflare_error(self) -> str | None:
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
