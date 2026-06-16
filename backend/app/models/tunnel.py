from typing import Literal

from pydantic import BaseModel

from app.models.common import ProcessStatus, ServiceActionResult

TunnelState = Literal["stopped", "starting", "running", "paused", "expired", "error"]


class TunnelStatus(BaseModel):
    state: TunnelState
    mode: Literal["quick", "named"]
    public_url: str | None = None
    chatgpt_mcp_url: str | None = None
    pid: int | None = None
    last_event: str | None = None
    process: ProcessStatus


class TunnelActionResult(ServiceActionResult):
    public_url: str | None = None
    chatgpt_mcp_url: str | None = None


class TunnelUrlResult(BaseModel):
    public_url: str | None
    chatgpt_mcp_url: str | None
    message: str
