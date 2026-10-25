from fastapi import APIRouter, HTTPException

from app.models.tunnel import (
    RemoveTunnelConfigRequest,
    TunnelActionResult,
    TunnelBinaryResult,
    TunnelConfigRequest,
    TunnelConfigResult,
    TunnelConfigStatus,
    TunnelStatus,
)
from app.openai_tunnel import TunnelConfigError
from app.services.container import ServiceContainer, get_container

router = APIRouter(prefix="/api/tunnel", tags=["tunnel"])


@router.get("/status", response_model=TunnelStatus)
def status() -> TunnelStatus:
    return get_container().tunnel.get_tunnel_status()


@router.get("/config", response_model=TunnelConfigStatus)
def get_config() -> TunnelConfigStatus:
    return get_container().tunnel.get_config_status()


@router.post("/config", response_model=TunnelConfigResult)
def configure(payload: TunnelConfigRequest) -> TunnelConfigResult:
    container = get_container()
    try:
        return container.tunnel.configure(payload.tunnel_id, payload.api_key)
    except TunnelConfigError as exc:
        raise HTTPException(
            status_code=getattr(exc, "http_status", 400),
            detail=str(exc),
        ) from exc


@router.delete("/config", response_model=TunnelConfigResult)
def remove_config(payload: RemoveTunnelConfigRequest) -> TunnelConfigResult:
    if not payload.confirm:
        raise HTTPException(
            status_code=400,
            detail="Confirmation requise pour supprimer la configuration du tunnel.",
        )
    return get_container().tunnel.remove_config()


@router.post("/install", response_model=TunnelBinaryResult)
def install_binary() -> TunnelBinaryResult:
    return get_container().tunnel.install_binary()


@router.post("/start", response_model=TunnelActionResult)
def start() -> TunnelActionResult:
    container = get_container()
    mcp_error = _ensure_mcp(container)
    if mcp_error is not None:
        return mcp_error
    return container.tunnel.start_tunnel()


@router.post("/stop", response_model=TunnelActionResult)
def stop() -> TunnelActionResult:
    return get_container().tunnel.stop_tunnel()


@router.post("/restart", response_model=TunnelActionResult)
def restart() -> TunnelActionResult:
    container = get_container()
    mcp_error = _ensure_mcp(container)
    if mcp_error is not None:
        return mcp_error
    return container.tunnel.restart_tunnel()


def _ensure_mcp(container: ServiceContainer) -> TunnelActionResult | None:
    mcp_status = container.mcp.get_mcp_status()
    if mcp_status.state in {"running", "unhealthy"}:
        return None
    mcp_result = container.mcp.start_mcp_service()
    if mcp_result.ok:
        return None
    return TunnelActionResult(
        ok=False,
        status="error",
        state="error",
        message=f"Tunnel non lancé: MCP local indisponible. {mcp_result.message}",
        pid=mcp_result.pid,
    )
