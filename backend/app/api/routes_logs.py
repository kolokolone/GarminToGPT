from fastapi import APIRouter, Query

from app.models.logs import LogResult
from app.services.container import get_container

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/backend", response_model=LogResult)
def backend_logs(lines: int = Query(default=200, ge=1, le=1000)) -> LogResult:
    return get_container().logs.read_logs("backend", lines)


@router.get("/mcp", response_model=LogResult)
def mcp_logs(lines: int = Query(default=200, ge=1, le=1000)) -> LogResult:
    return get_container().logs.read_logs("mcp", lines)


@router.get("/cloudflare", response_model=LogResult)
def cloudflare_logs(lines: int = Query(default=200, ge=1, le=1000)) -> LogResult:
    return get_container().logs.read_logs("cloudflare", lines)


@router.get("/auth", response_model=LogResult)
def auth_logs(lines: int = Query(default=200, ge=1, le=1000)) -> LogResult:
    return get_container().logs.read_logs("auth", lines)


@router.get("/tests", response_model=LogResult)
def test_logs(lines: int = Query(default=200, ge=1, le=1000)) -> LogResult:
    return get_container().logs.read_logs("tests", lines)


@router.get("/{service}", response_model=LogResult)
def service_logs(service: str, lines: int = Query(default=200, ge=1, le=1000)) -> LogResult:
    return get_container().logs.read_logs(service, lines)
