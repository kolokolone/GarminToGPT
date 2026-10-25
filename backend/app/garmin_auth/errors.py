"""Error taxonomy shared by the auth core and the HTTP layer."""

from __future__ import annotations


class GarminAuthError(RuntimeError):
    """Base class for errors the UI can turn into an actionable message."""

    http_status = 400

    def __init__(self, message: str, *, http_status: int | None = None) -> None:
        super().__init__(message)
        if http_status is not None:
            self.http_status = http_status


class KeyFormatError(GarminAuthError):
    """The pasted value is not a plausible Garmin Personal API key."""

    http_status = 400


class EnvKeyConflictError(GarminAuthError):
    """The key is managed by GARMIN_PERSONAL_API_KEY and cannot be edited here."""

    http_status = 409


class KeyValidationError(GarminAuthError):
    """Garmin rejected the key (invalid, revoked, or expired)."""

    http_status = 400


class GarminUnreachableError(GarminAuthError):
    """Garmin could not be reached (network, timeout, proxy)."""

    http_status = 502


class GarminUpstreamError(GarminAuthError):
    """Garmin answered with an unexpected failure."""

    http_status = 502


class NotConfiguredError(GarminAuthError):
    """An operation requiring a key was attempted without one."""

    http_status = 409
