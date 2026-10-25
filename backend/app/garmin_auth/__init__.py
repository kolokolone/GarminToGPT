"""Reusable Garmin Connect Personal API authentication block.

This package deliberately has no FastAPI dependency. The HTTP layer only
consumes the models and the :class:`GarminAuthCore` service, so the same code
can be dropped into another Python application (CLI, worker, another web
framework) unchanged.

The Garmin-specific HTTP work is delegated to Garmin's official
``garmin_personal_api`` client: this package adds key storage, status,
rotation metadata, and the small amount of policy the UI needs.
"""

from app.garmin_auth.errors import (
    EnvKeyConflictError,
    GarminAuthError,
    GarminUnreachableError,
    GarminUpstreamError,
    KeyFormatError,
    KeyValidationError,
    NotConfiguredError,
)
from app.garmin_auth.key_store import KeyStore, StoredKey
from app.garmin_auth.metadata import InMemoryMetadataStore, MetadataStore
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
from app.garmin_auth.service import ConfigureOutcome, GarminAuthCore
from app.garmin_auth.transport import GarminTransport, OfficialGarminTransport, TokenInfo

__all__ = [
    "ConfigureKeyRequest",
    "ConfigureOutcome",
    "EnvKeyConflictError",
    "GarminAuthCore",
    "GarminAuthError",
    "GarminAuthResult",
    "GarminAuthState",
    "GarminAuthStatus",
    "GarminKeyInfo",
    "GarminRotationInfo",
    "GarminTransport",
    "GarminUnreachableError",
    "GarminUpstreamError",
    "InMemoryMetadataStore",
    "KeyFormatError",
    "KeySource",
    "KeyStore",
    "KeyValidationError",
    "MetadataStore",
    "NotConfiguredError",
    "OfficialGarminTransport",
    "RemoveKeyRequest",
    "RotationSource",
    "StoredKey",
    "TokenInfo",
    "UpdateKeyExpirationRequest",
]
