from fastapi import APIRouter

from app.models.common import ServiceActionResult
from app.models.mcp import McpStatus, McpToolsResult
from app.services.container import get_container

router = APIRouter(prefix="/api/mcp", tags=["mcp"])


@router.get("/status", response_model=McpStatus)
def status() -> McpStatus:
    return get_container().mcp.get_mcp_status()


@router.post("/start", response_model=ServiceActionResult)
def start() -> ServiceActionResult:
    return get_container().mcp.start_mcp_service()


@router.post("/stop", response_model=ServiceActionResult)
def stop() -> ServiceActionResult:
    return get_container().mcp.stop_mcp_service()


@router.post("/restart", response_model=ServiceActionResult)
def restart() -> ServiceActionResult:
    return get_container().mcp.restart_mcp_service()


@router.get("/tools", response_model=McpToolsResult)
def tools() -> McpToolsResult:
    return get_container().mcp.list_mcp_tools()
