from fastapi import APIRouter

from app.models.tunnel import TunnelActionResult, TunnelStatus, TunnelUrlResult
from app.services.container import get_container

router = APIRouter(prefix="/api/tunnel", tags=["tunnel"])


@router.get("/status", response_model=TunnelStatus)
def status() -> TunnelStatus:
    return get_container().tunnel.get_tunnel_status()


@router.post("/start", response_model=TunnelActionResult)
def start() -> TunnelActionResult:
    container = get_container()
    mcp_status = container.mcp.get_mcp_status()
    if mcp_status.state not in {"running", "unhealthy"}:
        mcp_result = container.mcp.start_mcp_service()
        if not mcp_result.ok:
            return TunnelActionResult(
                ok=False,
                status="error",
                message=f"Tunnel non lancé: MCP local indisponible. {mcp_result.message}",
                pid=mcp_result.pid,
            )
    return container.tunnel.start_tunnel()


@router.post("/stop", response_model=TunnelActionResult)
def stop() -> TunnelActionResult:
    return get_container().tunnel.stop_tunnel()


@router.post("/pause", response_model=TunnelActionResult)
def pause() -> TunnelActionResult:
    return get_container().tunnel.pause_tunnel()


@router.post("/resume", response_model=TunnelActionResult)
def resume() -> TunnelActionResult:
    return get_container().tunnel.resume_tunnel()


@router.post("/regenerate", response_model=TunnelActionResult)
def regenerate() -> TunnelActionResult:
    container = get_container()
    mcp_status = container.mcp.get_mcp_status()
    if mcp_status.state not in {"running", "unhealthy"}:
        mcp_result = container.mcp.start_mcp_service()
        if not mcp_result.ok:
            return TunnelActionResult(
                ok=False,
                status="error",
                message=f"Tunnel non régénéré: MCP local indisponible. {mcp_result.message}",
                pid=mcp_result.pid,
            )
    return container.tunnel.regenerate_tunnel()


@router.get("/url", response_model=TunnelUrlResult)
def url() -> TunnelUrlResult:
    return get_container().tunnel.get_url_result()
