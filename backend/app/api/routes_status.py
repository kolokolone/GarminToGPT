from fastapi import APIRouter

from app.models.status import GlobalStatus
from app.services.container import get_container

router = APIRouter(tags=["status"])


@router.get("/api/status", response_model=GlobalStatus)
def get_status() -> GlobalStatus:
    container = get_container()
    settings = container.settings
    garmin = container.garmin.verify_garmin_auth()
    mcp = container.mcp.get_mcp_status()
    tunnel = container.tunnel.get_tunnel_status()

    if garmin.state == "no_token":
        state = "needs_auth"
        message = "Authentification Garmin requise."
    elif garmin.state in {"auth_invalid", "reauth_required", "error"}:
        state = "degraded"
        message = "Authentification Garmin à corriger."
    elif mcp.state == "running" and tunnel.state == "running":
        state = "ready"
        message = "Pont GarminToGPT prêt."
    else:
        state = "degraded"
        message = "Application partiellement prête: vérifie MCP et Cloudflare."

    return GlobalStatus(
        app_name=settings.app.name,
        version=settings.app.version,
        state=state,
        message=message,
        backend_url=f"http://{settings.server.host}:{settings.server.backend_port}",
        garmin=garmin,
        mcp=mcp,
        tunnel=tunnel,
    )
