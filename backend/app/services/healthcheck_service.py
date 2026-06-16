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
        if response.status_code < 200 or response.status_code >= 300:
            return HealthcheckResult(
                ok=False,
                target=url,
                status_code=response.status_code,
                message=f"Endpoint a retourné HTTP {response.status_code} – attendu 2xx.",
            )
        return HealthcheckResult(
            ok=True,
            target=url,
            status_code=response.status_code,
            message="Endpoint accessible.",
        )
