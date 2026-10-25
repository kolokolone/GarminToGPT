"""Minimal, non-verifying JWT claim reader.

The token comes from Garmin over TLS and Garmin's official client already
validates the response; this helper only reads ``iat``/``exp``/``scope`` so the
UI can show a rotation countdown. It must never be used as an authorization
check.
"""

from __future__ import annotations

import base64
import json
from typing import Any


def decode_claims(token: str) -> dict[str, Any]:
    """Return the JWT payload, or an empty mapping if it is not a JWT."""
    try:
        encoded = token.split(".")[1]
        padding = "=" * (-len(encoded) % 4)
        payload = json.loads(base64.urlsafe_b64decode(encoded + padding))
    except (IndexError, TypeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def token_times(claims: dict[str, Any], expires_at: float) -> tuple[float, float]:
    """Return ``(issued_at, expires_at)`` using the claims when available."""
    try:
        issued_at = float(claims["iat"])
    except (KeyError, TypeError, ValueError):
        issued_at = expires_at - 24 * 60 * 60
    try:
        expiry = float(claims["exp"])
    except (KeyError, TypeError, ValueError):
        expiry = expires_at
    if expiry > 1e12:  # tolerate a millisecond timestamp
        expiry /= 1000
    if issued_at > 1e12:
        issued_at /= 1000
    return issued_at, expiry


def token_scopes(claims: dict[str, Any]) -> tuple[str, ...]:
    raw = claims.get("scope")
    if isinstance(raw, str):
        return tuple(part for part in raw.split() if part)
    if isinstance(raw, list):
        return tuple(str(part) for part in raw if part)
    return ()
