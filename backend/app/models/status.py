from typing import Literal

from pydantic import BaseModel

from app.models.auth import GarminAuthStatus
from app.models.mcp import McpStatus
from app.models.tunnel import TunnelStatus

GlobalState = Literal["not_configured", "needs_auth", "ready", "degraded", "error"]


class GlobalStatus(BaseModel):
    app_name: str
    version: str
    state: GlobalState
    message: str
    backend_url: str
    garmin: GarminAuthStatus
    mcp: McpStatus
    tunnel: TunnelStatus
