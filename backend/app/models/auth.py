"""Auth API models.

The reusable ``app.garmin_auth`` package owns the contract so it can be used
outside this application; this module keeps the historical import path used by
the FastAPI routes.
"""

from app.garmin_auth.models import (
    ConfigureKeyRequest,
    GarminAuthResult,
    GarminAuthState,
    GarminAuthStatus,
    GarminKeyInfo,
    GarminRotationInfo,
    KeySource,
    RemoveKeyRequest,
    RotationSource,
    UpdateKeyExpirationRequest,
)

__all__ = [
    "ConfigureKeyRequest",
    "GarminAuthResult",
    "GarminAuthState",
    "GarminAuthStatus",
    "GarminKeyInfo",
    "GarminRotationInfo",
    "KeySource",
    "RemoveKeyRequest",
    "RotationSource",
    "UpdateKeyExpirationRequest",
]
