import logging

from fastapi import APIRouter

from app.models.status import GlobalStatus
from app.services.container import get_container

logger = logging.getLogger("GarminToGPT.access")

router = APIRouter(prefix="/api/access", tags=["access"])


def _build_global_status() -> GlobalStatus:
    """Reconstruit le statut global exactement comme /api/status."""
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


@router.post("/start", response_model=GlobalStatus)
def start_access() -> GlobalStatus:
    """Active l'accès ChatGPT aux outils Garmin.

    Orchestration métier :
      0. Vérifie que l'authentification Garmin est valide avant toute action.
      1. Si Garmin n'est pas authentifié → retourne immédiatement sans
         démarrer MCP ni Cloudflare.
      2. Démarre le MCP local s'il n'est pas déjà running/starting.
      3. Garantit que le tunnel Cloudflare est actif (sans le régénérer
         s'il existe déjà).
      4. Retourne le statut global.

    Idempotent : peut être appelé plusieurs fois sans effet de bord.
    """
    container = get_container()
    logger.info("Starting ChatGPT access")

    # 0. Vérification Garmin avant toute chose
    garmin = container.garmin.verify_garmin_auth()
    if garmin.state == "no_token":
        logger.warning(
            "Garmin auth required — no token found. "
            "Skipping MCP and tunnel start."
        )
        return _build_global_status()
    if garmin.state in {"auth_invalid", "reauth_required", "error"}:
        logger.warning(
            "Garmin auth required — state=%s. "
            "Skipping MCP and tunnel start.",
            garmin.state,
        )
        return _build_global_status()

    # 1. MCP local
    mcp_local = container.mcp.get_local_status()
    if mcp_local.status in ("running", "starting"):
        logger.info("MCP local already %s; skipping MCP start", mcp_local.status)
    else:
        logger.info("MCP local is %s; starting MCP", mcp_local.status)
        container.mcp.start_mcp_service()

    # 2. Tunnel Cloudflare (idempotent)
    container.tunnel.ensure_tunnel()

    logger.info("ChatGPT access start complete")
    return _build_global_status()


@router.post("/stop", response_model=GlobalStatus)
def stop_access() -> GlobalStatus:
    """Coupe l'accès ChatGPT aux outils Garmin.

    Arrête uniquement le MCP local.
    Le tunnel Cloudflare reste intact — son URL est conservée.
    """
    container = get_container()
    logger.info("Stopping ChatGPT access")

    mcp_local = container.mcp.get_local_status()
    if mcp_local.status in ("stopped",):
        logger.info("MCP local already stopped; nothing to do")
    else:
        logger.info("Stopping MCP local only; tunnel left untouched")
        container.mcp.stop_mcp_service()

    logger.info("ChatGPT access stop complete")
    return _build_global_status()
