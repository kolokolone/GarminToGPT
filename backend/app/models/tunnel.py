from typing import Literal

from pydantic import BaseModel, Field

from app.models.common import ProcessStatus, ServiceActionResult

TunnelState = Literal["stopped", "starting", "running", "error"]
TunnelProvider = Literal["openai"]
TunnelConfigSource = Literal["env", "file", "mixed", "none"]


class TunnelStatus(BaseModel):
    state: TunnelState
    provider: TunnelProvider = "openai"
    configured: bool = False
    tunnel_id: str | None = None
    api_key_configured: bool = False
    binary_installed: bool = False
    binary_version: str | None = None
    ready: bool = False
    health_status: int | None = None
    health_url: str | None = None
    ui_url: str | None = None
    connector_url: str
    pid: int | None = None
    last_event: str | None = None
    process: ProcessStatus


class TunnelActionResult(ServiceActionResult):
    state: TunnelState | None = None


class TunnelConfigStatus(BaseModel):
    configured: bool
    tunnel_id: str | None = None
    key_hint: str | None = None
    source: TunnelConfigSource = "none"
    key_source: Literal["env", "file"] | None = None
    tunnel_id_source: Literal["env", "file"] | None = None
    editable: bool = True
    binary_installed: bool = False
    binary_version: str | None = None
    message: str


class TunnelConfigRequest(BaseModel):
    tunnel_id: str = Field(min_length=1, max_length=128)
    api_key: str = Field(min_length=1, max_length=512)


class RemoveTunnelConfigRequest(BaseModel):
    confirm: bool = False


class TunnelConfigResult(BaseModel):
    ok: bool
    changed: bool = False
    message: str
    config: TunnelConfigStatus
    status: TunnelStatus


class TunnelBinaryResult(BaseModel):
    ok: bool
    installed: bool
    version: str | None = None
    path: str | None = None
    message: str
