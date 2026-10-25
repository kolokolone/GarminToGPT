"""Build the global status shared by /api/status and /api/access."""

from app.models.status import GlobalStatus
from app.services.container import ServiceContainer


def build_global_status(container: ServiceContainer) -> GlobalStatus:
    settings = container.settings
    garmin = container.garmin.status()
    mcp = container.mcp.get_mcp_status()
    tunnel = container.tunnel.get_tunnel_status()

    if garmin.state == "not_configured":
        state = "needs_auth"
        message = "Clé API Garmin requise. Ouvre /connexion pour connecter ton compte."
    elif garmin.state == "expired":
        state = "needs_auth"
        message = "Clé API Garmin expirée ou invalide. Mets-la à jour dans /connexion."
    elif garmin.state == "error":
        state = "degraded"
        message = "Vérification de la clé API Garmin impossible."
    elif mcp.state == "running" and tunnel.state == "running":
        state = "ready"
        message = "Pont GarminToGPT prêt."
        if garmin.state == "expiring_soon":
            message = "Pont prêt; la clé API Garmin expire bientôt."
    else:
        state = "degraded"
        message = "Application partiellement prête: vérifie le MCP et le tunnel OpenAI."

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
