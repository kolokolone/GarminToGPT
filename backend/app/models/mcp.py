from typing import Literal

from pydantic import BaseModel

from app.models.common import HealthcheckResult, ProcessStatus, ServiceActionResult

McpState = Literal["stopped", "starting", "running", "unhealthy", "error"]


class McpStatus(BaseModel):
    state: McpState
    host: str
    port: int
    endpoint: str
    local_url: str
    process: ProcessStatus
    healthcheck: HealthcheckResult | None = None


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
