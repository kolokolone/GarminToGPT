from app.core.config import Settings
from app.models.logs import LogResult
from app.utils.redact import redact_lines


class LogService:
    ALLOWED = {"backend", "mcp", "cloudflare", "cloudflared", "auth", "tests"}

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def read_logs(self, service: str, lines: int = 200) -> LogResult:
        normalized = "cloudflared" if service == "cloudflare" else service
        if normalized not in self.ALLOWED:
            return LogResult(service=service, lines=["Service de log inconnu."], truncated=False)
        path = self.settings.logs.path / f"{normalized}.log"
        if not path.exists():
            return LogResult(service=service, lines=["Aucun log disponible."], truncated=False)
        all_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        safe_lines = redact_lines(all_lines[-lines:])
        return LogResult(service=service, lines=safe_lines, truncated=len(all_lines) > lines)
