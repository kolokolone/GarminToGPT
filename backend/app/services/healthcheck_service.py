import httpx

from app.core.config import Settings
from app.models.common import HealthcheckResult


class HealthcheckService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def check_http_endpoint(self, url: str) -> HealthcheckResult:
        try:
            response = httpx.get(url, timeout=self.settings.timeouts.healthcheck_seconds)
        except httpx.RequestError as exc:
            return HealthcheckResult(ok=False, target=url, message=f"Endpoint inaccessible: {exc}")
        ok = response.status_code < 500
        return HealthcheckResult(
            ok=ok,
            target=url,
            status_code=response.status_code,
            message="Endpoint accessible." if ok else "Endpoint en erreur serveur.",
        )
