import logging

from fastapi import APIRouter

from app.models.status import GlobalStatus
from app.services.container import get_container
from app.services.status_service import build_global_status

logger = logging.getLogger("GarminToGPT.access")

router = APIRouter(prefix="/api/access", tags=["access"])

_READY_AUTH_STATES = {"valid", "expiring_soon"}


@router.post("/start", response_model=GlobalStatus)
def start_access() -> GlobalStatus:
    """Activate ChatGPT access after verifying the Garmin API key.

    The key is checked with a fresh token exchange and a small Garmin read.
    If it is missing, expired, or unreachable, neither MCP nor the OpenAI tunnel is
    started. The operation is idempotent.
    """
    container = get_container()
    logger.info("Starting ChatGPT access")

    garmin = container.garmin.verify()
    if garmin.state not in _READY_AUTH_STATES:
        logger.warning(
            "Garmin API key not usable (state=%s); skipping MCP and tunnel start.",
            garmin.state,
        )
        return build_global_status(container)

    mcp_local = container.mcp.get_local_status()
    if mcp_local.status in ("running", "starting"):
        logger.info("MCP local already %s; skipping MCP start", mcp_local.status)
    else:
        logger.info("MCP local is %s; starting MCP", mcp_local.status)
        container.mcp.start_mcp_service()

    container.tunnel.ensure_tunnel()

    logger.info("ChatGPT access start complete")
    return build_global_status(container)


@router.post("/stop", response_model=GlobalStatus)
def stop_access() -> GlobalStatus:
    """Stop the local MCP bridge and the OpenAI tunnel."""
    container = get_container()
    logger.info("Stopping ChatGPT access")

    mcp_local = container.mcp.get_local_status()
    if mcp_local.status == "stopped":
        logger.info("MCP local already stopped; nothing to do")
    else:
        logger.info("Stopping MCP local and OpenAI tunnel")
        container.mcp.stop_mcp_service()

    container.tunnel.stop_tunnel()

    logger.info("ChatGPT access stop complete")
    return build_global_status(container)
