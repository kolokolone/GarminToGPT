from typing import Literal

from pydantic import BaseModel

from app.models.common import HealthcheckResult, ProcessStatus, ServiceActionResult

McpState = Literal["stopped", "starting", "running", "unhealthy", "error"]
McpLocalState = Literal["running", "stopped", "starting", "stopping", "error"]


class McpStatus(BaseModel):
    state: McpState
    host: str
    port: int
    endpoint: str
    local_url: str
    process: ProcessStatus
    healthcheck: HealthcheckResult | None = None


class McpLocalStatus(BaseModel):
    """Statut simplifié du MCP local pour les contrôles UI."""

    running: bool
    status: McpLocalState
    pid: int | None = None
    port: int
    last_started_at: str | None = None
    last_stopped_at: str | None = None
    last_error: str | None = None


class McpTool(BaseModel):
    name: str
    risk: Literal["read", "write", "unknown"]
    reason: str


class McpToolsResult(BaseModel):
    ok: bool
    message: str
    tools: list[McpTool]


class McpToolClassification(BaseModel):
    read_tools: list[str]
    write_tools: list[str]
    unknown_tools: list[str]


class McpActionResult(ServiceActionResult):
    pass


class McpProbeStep(BaseModel):
    method: str
    status_code: int | None = None
    ok: bool
    duration_ms: int
    detail: str


class McpProbeResult(BaseModel):
    ok: bool
    status: str  # "ok" | "error"
    server_name: str | None = None
    server_version: str | None = None
    protocol_version: str | None = None
    error: str | None = None
    tools_count: int = 0
    tools: list[dict] = []
    session_id: str | None = None
    steps: list[McpProbeStep] = []
    final_url: str | None = None
