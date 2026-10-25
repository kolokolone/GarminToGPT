"""High-level Garmin Personal API authentication policy.

Responsibilities:
- resolve the key (environment, then the file shared with Garmin's client);
- validate it through the official client;
- expose a secret-free status with token/key rotation information;
- keep idempotent create/update/remove operations.

The HTTP layer is intentionally absent: another application can import
:class:`GarminAuthCore` and provide its own metadata store and transport.
"""

from __future__ import annotations

import hmac
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from garmin_personal_api import GarminPersonalApiError, HttpError

from app.garmin_auth.errors import (
    EnvKeyConflictError,
    GarminAuthError,
    GarminUnreachableError,
    GarminUpstreamError,
    KeyFormatError,
    KeyValidationError,
    NotConfiguredError,
)
from app.garmin_auth.jwt import decode_claims, token_scopes
from app.garmin_auth.key_store import KeyStore
from app.garmin_auth.metadata import MetadataStore
from app.garmin_auth.models import (
    GarminAuthState,
    GarminAuthStatus,
    GarminKeyInfo,
    GarminRotationInfo,
    RotationSource,
)
from app.garmin_auth.token_cache import (
    cache_fingerprint,
    default_token_cache_file,
    delete_token_cache,
    read_token_cache,
    resolve_base_url,
)
from app.garmin_auth.transport import GarminTransport, TokenInfo

_FULL_TOKEN_TTL_SECONDS = 24 * 60 * 60
_OBSERVATION_MARGIN_SECONDS = 5 * 60
_MAX_DECLARED_WINDOW_DAYS = 400


@dataclass(frozen=True)
class ConfigureOutcome:
    changed: bool
    status: GarminAuthStatus


class GarminAuthCore:
    def __init__(
        self,
        *,
        key_store: KeyStore,
        transport: GarminTransport,
        metadata: MetadataStore,
        token_cache_path: str | Path | None = None,
        base_url: str | None = None,
        rotation_warning_days: int = 7,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.key_store = key_store
        self.transport = transport
        self.metadata = metadata
        self.token_cache_path = (
            Path(token_cache_path).expanduser()
            if token_cache_path is not None
            else default_token_cache_file()
        )
        self.base_url = (base_url or resolve_base_url()).rstrip("/")
        self.rotation_warning_days = rotation_warning_days
        self._now = now or (lambda: datetime.now(UTC))

    # -- public operations -------------------------------------------------

    def status(self) -> GarminAuthStatus:
        now = self._now_utc()
        try:
            stored = self.key_store.load()
        except OSError as exc:
            return self._error_status(f"Impossible de lire la clé API Garmin: {exc}")
        if stored is None:
            return self._not_configured()

        fingerprint = self.key_store.fingerprint(stored.value)
        meta = self._metadata_for(fingerprint)
        cached = read_token_cache(
            self.token_cache_path,
            cache_fingerprint(stored.value, self.base_url),
        )
        claims = decode_claims(cached.access_token) if cached is not None else {}
        token_valid = cached is not None and cached.expires_at > now.timestamp()
        scopes = list(token_scopes(claims)) if claims else list(meta.get("scopes") or [])
        rotation = self._rotation(meta, now)
        state, message = self._classify(meta, token_valid, rotation)

        return GarminAuthStatus(
            state=state,
            configured=True,
            key=GarminKeyInfo(
                source=stored.source,
                hint=self.key_store.hint(stored.value),
                fingerprint=self.key_store.display_fingerprint(stored.value),
            ),
            token_present=cached is not None,
            token_valid=token_valid,
            token_expires_at=(
                self._iso_utc(cached.expires_at)
                if cached is not None
                else self._string(meta.get("token_expires_at"))
            ),
            token_scopes=scopes,
            rotation=rotation,
            last_verified_at=self._string(meta.get("last_verified_at")),
            display_name=self._string(meta.get("display_name")),
            message=message,
            error=self._string(meta.get("last_error")),
        )

    def configure(
        self,
        api_key: str,
        expires_on: str | None = None,
    ) -> ConfigureOutcome:
        key = self.key_store.validate(api_key)
        declared_expiry = self._normalize_expires_on(expires_on)
        try:
            stored = self.key_store.load()
        except OSError as exc:
            raise GarminUpstreamError(
                f"Impossible de lire la clé API Garmin actuelle: {exc}"
            ) from exc

        if (
            stored is not None
            and stored.source == "env"
            and not hmac.compare_digest(stored.value, key)
        ):
            raise EnvKeyConflictError(
                "La variable d'environnement GARMIN_PERSONAL_API_KEY est définie et "
                "prioritaire. Retire-la (ou mets-la à jour) pour gérer la clé ici."
            )

        same_key = stored is not None and hmac.compare_digest(stored.value, key)
        old_fingerprint = self.key_store.fingerprint(stored.value) if stored else None
        new_fingerprint = self.key_store.fingerprint(key)

        token, profile = self._validate_key(key)

        if not same_key:
            if stored is not None:
                delete_token_cache(
                    self.token_cache_path,
                    cache_fingerprint(stored.value, self.base_url),
                )
            self._save_key(key)
            meta: dict[str, Any] = {}
        else:
            if stored is not None and stored.source == "file" and not stored.path.exists():
                self._save_key(key)
            meta = self._metadata_for(new_fingerprint)

        source = "env" if (stored is not None and stored.source == "env" and same_key) else "file"
        now = self._now_utc()
        meta = self._success_metadata(meta, source, new_fingerprint, token, profile, now)
        if declared_expiry is not None:
            meta["expires_on"] = declared_expiry
        elif not same_key:
            meta.pop("expires_on", None)
        self._apply_observation(meta, token)
        self.metadata.write(meta)

        changed = stored is None or old_fingerprint != new_fingerprint
        return ConfigureOutcome(changed=changed, status=self.status())

    def verify(self) -> GarminAuthStatus:
        now = self._now_utc()
        try:
            stored = self.key_store.load()
        except OSError as exc:
            return self._error_status(f"Impossible de lire la clé API Garmin: {exc}")
        if stored is None:
            return self._not_configured()

        fingerprint = self.key_store.fingerprint(stored.value)
        meta = self._metadata_for(fingerprint)
        if not meta:
            meta = {"fingerprint": fingerprint}

        try:
            token, profile = self._validate_key(stored.value)
        except GarminAuthError as exc:
            kind = self._error_kind(exc)
            meta.update(
                {
                    "fingerprint": fingerprint,
                    "last_verified_at": now.isoformat(),
                    "last_error": str(exc),
                    "last_error_kind": kind,
                }
            )
            self.metadata.write(meta)
            return self.status()

        meta = self._success_metadata(meta, stored.source, fingerprint, token, profile, now)
        self._apply_observation(meta, token)
        self.metadata.write(meta)
        return self.status()

    def update_expiration(self, expires_on: str | None) -> GarminAuthStatus:
        declared_expiry = self._normalize_expires_on(expires_on)
        try:
            stored = self.key_store.load()
        except OSError as exc:
            raise GarminUpstreamError(
                f"Impossible de lire la clé API Garmin: {exc}"
            ) from exc
        if stored is None:
            raise NotConfiguredError("Aucune clé API Garmin n'est configurée.")

        fingerprint = self.key_store.fingerprint(stored.value)
        meta = self._metadata_for(fingerprint) or {"fingerprint": fingerprint}
        if declared_expiry is None:
            meta.pop("expires_on", None)
            meta["rotation_source"] = (
                "observed" if meta.get("observed_expires_at") else "unknown"
            )
        else:
            meta["expires_on"] = declared_expiry
            meta["rotation_source"] = (
                "observed" if meta.get("observed_expires_at") else "declared"
            )
        self.metadata.write(meta)
        return self.status()

    def remove(self) -> GarminAuthStatus:
        try:
            stored = self.key_store.load()
        except OSError as exc:
            raise GarminUpstreamError(
                f"Impossible de lire la clé API Garmin: {exc}"
            ) from exc
        if stored is None:
            return self._not_configured()
        if stored.source == "env":
            raise EnvKeyConflictError(
                "La clé provient de GARMIN_PERSONAL_API_KEY. Supprime la variable "
                "d'environnement pour la retirer de l'application."
            )

        fingerprint = cache_fingerprint(stored.value, self.base_url)
        try:
            delete_token_cache(self.token_cache_path, fingerprint)
        except OSError as exc:
            raise GarminUpstreamError(
                f"Impossible de supprimer le jeton Garmin en cache: {exc}"
            ) from exc
        try:
            self.key_store.delete()
        except OSError as exc:
            raise GarminUpstreamError(
                f"Impossible de supprimer la clé API Garmin: {exc}"
            ) from exc
        self.metadata.write({})
        return self._not_configured()

    # -- validation and transport mapping ----------------------------------

    def _save_key(self, key: str) -> None:
        try:
            self.key_store.save(key)
        except OSError as exc:
            raise GarminUpstreamError(
                f"Impossible d'enregistrer la clé API Garmin: {exc}"
            ) from exc

    def _validate_key(self, key: str) -> tuple[TokenInfo, dict[str, Any]]:
        try:
            token = self.transport.exchange(key, force_refresh=True)
            profile = self.transport.profile(token.access_token)
        except Exception as exc:  # noqa: BLE001 - converted to a typed error
            raise self._translate(exc) from exc
        return token, profile

    @staticmethod
    def _translate(exc: Exception) -> GarminAuthError:
        if isinstance(exc, HttpError):
            if exc.status_code in (400, 401, 403):
                return KeyValidationError(
                    "Garmin a refusé la clé API "
                    f"(HTTP {exc.status_code}). Elle est invalide, révoquée ou expirée. "
                    "Crée une nouvelle clé dans Garmin Connect puis mets-la à jour."
                )
            return GarminUpstreamError(f"Garmin a répondu HTTP {exc.status_code}.")
        if isinstance(exc, GarminPersonalApiError):
            return GarminUpstreamError("Garmin a renvoyé une réponse inattendue.")
        if isinstance(exc, OSError):
            return GarminUnreachableError(
                "Impossible de joindre Garmin. Vérifie ta connexion réseau et réessaie."
            )
        return GarminUpstreamError("Erreur inattendue pendant la validation de la clé API.")

    @staticmethod
    def _error_kind(exc: GarminAuthError) -> str:
        if isinstance(exc, KeyValidationError):
            return "invalid"
        if isinstance(exc, GarminUnreachableError):
            return "unreachable"
        return "upstream"

    # -- metadata and rotation --------------------------------------------

    def _metadata_for(self, fingerprint: str) -> dict[str, Any]:
        raw = self.metadata.read()
        if not isinstance(raw, dict) or raw.get("fingerprint") != fingerprint:
            return {}
        return dict(raw)

    def _success_metadata(
        self,
        meta: dict[str, Any],
        source: str,
        fingerprint: str,
        token: TokenInfo,
        profile: dict[str, Any],
        now: datetime,
    ) -> dict[str, Any]:
        updated = dict(meta)
        updated.update(
            {
                "fingerprint": fingerprint,
                "source": source,
                "saved_at": self._string(updated.get("saved_at")) or now.isoformat(),
                "last_verified_at": now.isoformat(),
                "display_name": self._profile_name(profile)
                or self._string(updated.get("display_name")),
                "scopes": list(token.scopes),
                "token_expires_at": self._iso_utc(token.expires_at),
                "last_error": None,
                "last_error_kind": None,
            }
        )
        return updated

    def _apply_observation(self, meta: dict[str, Any], token: TokenInfo) -> None:
        ttl = token.expires_at - token.issued_at
        if 0 < ttl < _FULL_TOKEN_TTL_SECONDS - _OBSERVATION_MARGIN_SECONDS:
            meta["observed_expires_at"] = self._iso_utc(token.expires_at)
            meta["rotation_source"] = "observed"
        elif meta.get("expires_on"):
            meta["rotation_source"] = "declared"
        else:
            meta["rotation_source"] = "unknown"

    def _rotation(self, meta: dict[str, Any], now: datetime) -> GarminRotationInfo:
        observed = self._parse_datetime(meta.get("observed_expires_at"))
        declared_raw = meta.get("expires_on")
        expires_date: date | None = None
        source: RotationSource = "unknown"

        if observed is not None:
            expires_date = observed.astimezone().date()
            source = "observed"
        elif isinstance(declared_raw, str):
            try:
                expires_date = date.fromisoformat(declared_raw)
                source = "declared"
            except ValueError:
                expires_date = None

        if expires_date is None:
            return GarminRotationInfo()

        days = (expires_date - now.astimezone().date()).days
        return GarminRotationInfo(
            expires_on=expires_date.isoformat(),
            days_remaining=days,
            source=source,
            warning=days <= self.rotation_warning_days,
        )

    def _classify(
        self,
        meta: dict[str, Any],
        token_valid: bool,
        rotation: GarminRotationInfo,
    ) -> tuple[GarminAuthState, str]:
        error_kind = meta.get("last_error_kind")
        if error_kind == "invalid":
            return (
                "expired",
                "Clé API Garmin refusée (invalide, révoquée ou expirée). "
                "Crée une nouvelle clé dans Garmin Connect puis mets-la à jour.",
            )
        if error_kind in {"unreachable", "upstream"}:
            detail = self._string(meta.get("last_error")) or "erreur inconnue"
            return "error", f"Vérification Garmin impossible: {detail}"

        if (
            rotation.source == "observed"
            and rotation.days_remaining is not None
            and rotation.days_remaining < 0
        ):
            return (
                "expired",
                "La clé API Garmin a expiré. Crée une nouvelle clé dans Garmin Connect "
                "puis mets-la à jour.",
            )

        if token_valid:
            if rotation.warning:
                return "expiring_soon", self._rotation_message(rotation)
            return "valid", "Clé API valide; accès Garmin Connect opérationnel."

        if meta.get("last_verified_at"):
            if rotation.warning:
                return "expiring_soon", self._rotation_message(rotation)
            return "valid", "Clé API vérifiée; le jeton sera renouvelé au prochain appel."

        return "configured", "Clé API enregistrée. Lance une vérification pour confirmer l'accès."

    def _rotation_message(self, rotation: GarminRotationInfo) -> str:
        days = rotation.days_remaining
        if days is None:
            return "Clé API valide."
        if days < 0:
            return (
                "La date d'expiration déclarée est dépassée. Vérifie la clé et "
                "mets à jour sa date de rotation."
            )
        if days == 0:
            return "La clé API expire aujourd'hui. Crée une nouvelle clé et mets-la à jour."
        return (
            f"La clé API expire dans {days} jours. Crée une nouvelle clé avant "
            "cette date et mets-la à jour."
        )

    # -- small helpers -----------------------------------------------------

    def _normalize_expires_on(self, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        try:
            parsed = date.fromisoformat(value.strip())
        except ValueError as exc:
            raise KeyFormatError(
                "La date d'expiration doit être au format YYYY-MM-DD."
            ) from exc
        today = self._now_utc().astimezone().date()
        if (
            parsed < today - timedelta(days=_MAX_DECLARED_WINDOW_DAYS)
            or parsed > today + timedelta(days=_MAX_DECLARED_WINDOW_DAYS)
        ):
            raise KeyFormatError(
                "La date d'expiration doit être comprise entre "
                f"-{_MAX_DECLARED_WINDOW_DAYS} et +{_MAX_DECLARED_WINDOW_DAYS} jours."
            )
        return parsed.isoformat()

    def _not_configured(self) -> GarminAuthStatus:
        return GarminAuthStatus(
            state="not_configured",
            configured=False,
            message=(
                "Aucune clé API Garmin configurée. Ouvre /connexion pour connecter "
                "ton compte avec une clé Personal API."
            ),
        )

    def _error_status(self, message: str) -> GarminAuthStatus:
        return GarminAuthStatus(
            state="error",
            configured=False,
            message=message,
            error=message,
        )

    def _now_utc(self) -> datetime:
        value = self._now()
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _iso_utc(timestamp: float) -> str:
        return datetime.fromtimestamp(timestamp, UTC).isoformat()

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if not isinstance(value, str) or not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed

    @staticmethod
    def _string(value: Any) -> str | None:
        return value if isinstance(value, str) and value else None

    @staticmethod
    def _profile_name(profile: dict[str, Any]) -> str | None:
        name = profile.get("displayName")
        return name if isinstance(name, str) and name else None
