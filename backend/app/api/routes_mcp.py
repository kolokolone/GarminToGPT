from typing import Any

from fastapi import APIRouter

from app.models.mcp import McpLocalStatus, McpStatus, McpToolsResult
from app.services.container import get_container

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


@router.get("/status", response_model=McpLocalStatus)
def status() -> McpLocalStatus:
    """Retourne l'état actuel du service MCP local (running/stopped/error)."""
    return get_container().mcp.get_local_status()


@router.post("/start", response_model=McpLocalStatus)
def start() -> McpLocalStatus:
    """Démarre le service MCP local (mcp-proxy). Idempotent."""
    get_container().mcp.start_mcp_service()
    return get_container().mcp.get_local_status()


@router.post("/stop", response_model=McpLocalStatus)
def stop() -> McpLocalStatus:
    """Arrête le service MCP local. Idempotent. Ne touche ni à Cloudflare ni aux tokens Garmin."""
    get_container().mcp.stop_mcp_service()
    return get_container().mcp.get_local_status()


@router.post("/restart", response_model=McpLocalStatus)
def restart() -> McpLocalStatus:
    """Redémarre le service MCP local."""
    get_container().mcp.restart_mcp_service()
    return get_container().mcp.get_local_status()


@router.get("/tools", response_model=McpToolsResult)
def tools() -> McpToolsResult:
    return get_container().mcp.list_mcp_tools()


@router.get("/raw-tools")
def raw_tools() -> list[dict[str, Any]]:
    """Retourne la liste brute des outils MCP (nom, description, input_schema)."""
    return get_container().mcp.get_raw_tools()


# Conserver l'ancienne route /api/mcp/status détaillée sous /api/mcp/verbose-status
@router.get("/verbose-status", response_model=McpStatus)
def verbose_status() -> McpStatus:
    """Retourne l'état détaillé du MCP (avec healthcheck et infos de probe)."""
    return get_container().mcp.get_mcp_status()
