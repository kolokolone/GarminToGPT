"""Application adapter for the reusable Garmin Personal API auth block."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app.core.config import Settings
from app.garmin_auth import (
    ConfigureOutcome,
    GarminAuthCore,
    GarminAuthStatus,
    KeyStore,
    MetadataStore,
    OfficialGarminTransport,
)
from app.garmin_auth.token_cache import default_api_key_file, default_token_cache_file
from app.services.state_store import StateStore

_METADATA_KEY = "garmin_auth"
_KEY_FILE_ENV = "GARMINTOGPT_GARMIN_KEY_FILE"
_TOKEN_CACHE_ENV = "GARMINTOGPT_GARMIN_TOKEN_CACHE"


class StateMetadataStore(MetadataStore):
    """Persist non-secret auth metadata in ``runtime/state.json``."""

    def __init__(self, state: StateStore) -> None:
        self.state = state

    def read(self) -> dict[str, Any]:
        raw = self.state.read().get(_METADATA_KEY)
        return dict(raw) if isinstance(raw, dict) else {}

    def write(self, data: dict[str, Any]) -> None:
        self.state.set_value(_METADATA_KEY, dict(data))


def _resolve_path(env_name: str, default: Path) -> Path:
    raw = os.environ.get(env_name)
    return Path(raw).expanduser() if raw else default


class GarminAuthService:
    """Thin, app-specific wrapper around :class:`GarminAuthCore`."""

    def __init__(self, settings: Settings, state: StateStore) -> None:
        self.settings = settings
        self.state = state
        self.key_path = _resolve_path(_KEY_FILE_ENV, default_api_key_file())
        self.cache_path = _resolve_path(_TOKEN_CACHE_ENV, default_token_cache_file())
        self._core = GarminAuthCore(
            key_store=KeyStore(self.key_path),
            transport=OfficialGarminTransport(
                cache_file=self.cache_path,
                timeout=float(settings.garmin.timeout_seconds),
            ),
            metadata=StateMetadataStore(state),
            token_cache_path=self.cache_path,
            rotation_warning_days=settings.garmin.rotation_warning_days,
        )

    def status(self) -> GarminAuthStatus:
        return self._core.status()

    def configure(self, api_key: str, expires_on: str | None = None) -> ConfigureOutcome:
        return self._core.configure(api_key, expires_on)

    def verify(self) -> GarminAuthStatus:
        return self._core.verify()

    def update_expiration(self, expires_on: str | None) -> GarminAuthStatus:
        return self._core.update_expiration(expires_on)

    def remove(self) -> GarminAuthStatus:
        return self._core.remove()
