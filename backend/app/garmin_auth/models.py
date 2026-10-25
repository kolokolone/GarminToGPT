"""Public status contract for the Garmin Personal API authentication block.

These models are safe to serialize to a browser: they never contain the API
key or the bearer token.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

GarminAuthState = Literal[
    "not_configured",
    "configured",
    "valid",
    "expiring_soon",
    "expired",
    "error",
]
KeySource = Literal["file", "env"]
RotationSource = Literal["declared", "observed", "unknown"]


class GarminKeyInfo(BaseModel):
    source: KeySource | None = None
    hint: str | None = None
    fingerprint: str | None = None


class GarminRotationInfo(BaseModel):
    expires_on: str | None = None
    days_remaining: int | None = None
    source: RotationSource = "unknown"
    warning: bool = False


class GarminAuthStatus(BaseModel):
    state: GarminAuthState
    configured: bool
    key: GarminKeyInfo = Field(default_factory=GarminKeyInfo)
    token_present: bool = False
    token_valid: bool = False
    token_expires_at: str | None = None
    token_scopes: list[str] = Field(default_factory=list)
    rotation: GarminRotationInfo = Field(default_factory=GarminRotationInfo)
    last_verified_at: str | None = None
    display_name: str | None = None
    message: str
    error: str | None = None


class ConfigureKeyRequest(BaseModel):
    api_key: str = Field(min_length=1, max_length=4096)
    expires_on: str | None = None


class UpdateKeyExpirationRequest(BaseModel):
    expires_on: str | None = None


class RemoveKeyRequest(BaseModel):
    confirm: bool = False


class GarminAuthResult(BaseModel):
    ok: bool
    changed: bool = False
    message: str
    status: GarminAuthStatus
