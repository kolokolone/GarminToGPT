"""Boundary around Garmin's official Personal API client.

Keeping the official calls behind this small protocol makes the auth core
testable without network access and documents exactly what we depend on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from garmin_personal_api import (
    GarminPersonalApiClient,
    PersonalApiAuthenticator,
)

from app.garmin_auth.jwt import decode_claims, token_scopes, token_times
from app.garmin_auth.token_cache import default_timeout, default_token_cache_file


@dataclass(frozen=True)
class TokenInfo:
    access_token: str = field(repr=False)
    expires_at: float
    issued_at: float
    scopes: tuple[str, ...] = ()


class GarminTransport(Protocol):
    def exchange(self, api_key: str, *, force_refresh: bool = False) -> TokenInfo: ...

    def profile(self, access_token: str) -> dict[str, Any]: ...


class OfficialGarminTransport:
    """Use ``garmin-connect-personal-api-python`` for token exchange and reads."""

    def __init__(
        self,
        *,
        cache_file: str | Path | None = None,
        timeout: float | None = None,
    ) -> None:
        self.cache_file = (
            Path(cache_file).expanduser() if cache_file is not None else default_token_cache_file()
        )
        self.timeout = timeout if timeout is not None else default_timeout()

    def exchange(self, api_key: str, *, force_refresh: bool = False) -> TokenInfo:
        with PersonalApiAuthenticator(
            bearer_token_cache_file=self.cache_file,
            timeout=self.timeout,
        ) as authenticator:
            token = authenticator.obtain_token(api_key, force_refresh=force_refresh)
        claims = decode_claims(token.access_token)
        issued_at, expires_at = token_times(claims, token.expires_at)
        return TokenInfo(
            access_token=token.access_token,
            expires_at=expires_at,
            issued_at=issued_at,
            scopes=token_scopes(claims),
        )

    def profile(self, access_token: str) -> dict[str, Any]:
        with GarminPersonalApiClient(access_token, timeout=self.timeout) as client:
            payload = client.get_user_profile_settings()
        return dict(payload) if isinstance(payload, dict) else {}
