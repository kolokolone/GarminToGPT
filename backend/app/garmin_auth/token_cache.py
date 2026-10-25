"""Read and clean Garmin's official bearer-token cache.

The cache is shared with Garmin's own client and any other application using
it. A cached token is only returned when it belongs to the current key and
Garmin endpoint (the official client binds the cache with this fingerprint).
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from garmin_personal_api.constants import (
    BASE_URL_ENV_VAR,
    DEFAULT_BASE_URL,
    DEFAULT_BEARER_TOKEN_CACHE_FILE,
    DEFAULT_TIMEOUT_SECONDS,
)


def resolve_base_url() -> str:
    return (os.environ.get(BASE_URL_ENV_VAR) or DEFAULT_BASE_URL).rstrip("/")


def default_api_key_file() -> Path:
    from garmin_personal_api.constants import DEFAULT_API_KEY_FILE

    return DEFAULT_API_KEY_FILE.expanduser()


def default_token_cache_file() -> Path:
    return DEFAULT_BEARER_TOKEN_CACHE_FILE.expanduser()


def default_timeout() -> float:
    return DEFAULT_TIMEOUT_SECONDS


def cache_fingerprint(api_key: str, base_url: str | None = None) -> str:
    endpoint = (base_url or resolve_base_url()).rstrip("/")
    return hashlib.sha256(f"{endpoint}\0{api_key}".encode()).hexdigest()


@dataclass(frozen=True)
class CachedToken:
    access_token: str = field(repr=False)
    expires_at: float


def read_token_cache(path: str | Path, fingerprint: str) -> CachedToken | None:
    try:
        payload = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, ValueError, TypeError):
        return None
    if not isinstance(payload, dict) or payload.get("fingerprint") != fingerprint:
        return None
    token = payload.get("access_token")
    expires_at = payload.get("expires_at")
    if not isinstance(token, str) or not token:
        return None
    try:
        expires = float(expires_at)
    except (TypeError, ValueError):
        return None
    return CachedToken(access_token=token, expires_at=expires)


def delete_token_cache(path: str | Path, fingerprint: str) -> bool:
    """Delete the cache only when it belongs to the given key fingerprint."""
    cache_path = Path(path).expanduser()
    if read_token_cache(cache_path, fingerprint) is None:
        return False
    try:
        cache_path.unlink()
    except FileNotFoundError:
        return False
    return True
