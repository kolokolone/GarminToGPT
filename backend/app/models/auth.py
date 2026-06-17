from typing import Literal

from pydantic import BaseModel

GarminState = Literal[
    "unknown", "no_token", "token_found", "connected", "auth_invalid", "reauth_required", "error"
]


class GarminAuthStatus(BaseModel):
    state: GarminState
    token_found: bool
    token_valid: bool
    last_successful_auth: str | None = None
    message: str


class GarminLoginRequest(BaseModel):
    email: str | None = None
    password: str | None = None
    otp: str | None = None


class GarminAuthResult(BaseModel):
    ok: bool
    assisted: bool = False
    needs_otp: bool = False
    message: str
    command: list[str] | None = None
    status: GarminAuthStatus


class DisconnectRequest(BaseModel):
    confirm: bool = False


class DisconnectResult(BaseModel):
    ok: bool
    message: str
