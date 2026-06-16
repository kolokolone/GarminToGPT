from typing import Literal

from pydantic import BaseModel


class ServiceActionResult(BaseModel):
    ok: bool
    status: str
    message: str
    pid: int | None = None


class HealthcheckResult(BaseModel):
    ok: bool
    target: str
    message: str
    status_code: int | None = None


class ProcessStatus(BaseModel):
    status: Literal["stopped", "starting", "running", "unhealthy", "error"]
    pid: int | None = None
    message: str
