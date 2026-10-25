"""Unit tests for the reusable Garmin Personal API auth core.

No network access: the official client boundary is replaced by FakeTransport.
"""

import base64
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.garmin_auth import (
    EnvKeyConflictError,
    GarminAuthCore,
    InMemoryMetadataStore,
    KeyFormatError,
    KeyStore,
    KeyValidationError,
    TokenInfo,
)
from app.garmin_auth.token_cache import cache_fingerprint
from garmin_personal_api import HttpError

BASE_URL = "https://personal.connectapi.garmin.com"
FIXED_NOW = datetime(2026, 10, 25, 12, 0, tzinfo=UTC)
KEY_A = "GCDC_" + "a" * 120
KEY_B = "GCDC_" + "b" * 120


class FakeTransport:
    def __init__(
        self,
        *,
        issued_at: float | None = None,
        expires_at: float | None = None,
        profile: dict | None = None,
        error: Exception | None = None,
    ) -> None:
        self.issued_at = issued_at if issued_at is not None else FIXED_NOW.timestamp()
        self.expires_at = (
            expires_at if expires_at is not None else self.issued_at + 24 * 60 * 60
        )
        self.profile_data = profile or {"displayName": "Test Runner"}
        self.error = error
        self.exchange_calls: list[tuple[str, bool]] = []
        self.profile_calls: list[str] = []

    def exchange(self, api_key: str, *, force_refresh: bool = False) -> TokenInfo:
        self.exchange_calls.append((api_key, force_refresh))
        if self.error is not None:
            raise self.error
        return TokenInfo(
            access_token=_make_jwt(self.issued_at, self.expires_at),
            expires_at=self.expires_at,
            issued_at=self.issued_at,
            scopes=("CONNECT_READ", "PERSONAL_API_WELLNESS_READ"),
        )

    def profile(self, access_token: str) -> dict:
        self.profile_calls.append(access_token)
        return dict(self.profile_data)


def _b64(value: object) -> str:
    raw = json.dumps(value).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _make_jwt(issued_at: float, expires_at: float, scope: list[str] | None = None) -> str:
    header = _b64({"alg": "none", "typ": "JWT"})
    payload = _b64(
        {
            "iat": int(issued_at),
            "exp": int(expires_at),
            "scope": scope or ["CONNECT_READ", "PERSONAL_API_WELLNESS_READ"],
        }
    )
    return f"{header}.{payload}.signature"


@pytest.fixture(autouse=True)
def _clear_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TEST_GARMIN_KEY", raising=False)


def _core(
    tmp_path: Path,
    transport: FakeTransport,
    *,
    metadata: InMemoryMetadataStore | None = None,
) -> tuple[GarminAuthCore, KeyStore, InMemoryMetadataStore, Path]:
    key_store = KeyStore(tmp_path / "api-key", env_var="TEST_GARMIN_KEY")
    store = metadata or InMemoryMetadataStore()
    cache_path = tmp_path / "token-cache.json"
    core = GarminAuthCore(
        key_store=key_store,
        transport=transport,
        metadata=store,
        token_cache_path=cache_path,
        base_url=BASE_URL,
        rotation_warning_days=7,
        now=lambda: FIXED_NOW,
    )
    return core, key_store, store, cache_path


def _write_cache(path: Path, key: str, expires_at: float) -> str:
    token = _make_jwt(FIXED_NOW.timestamp(), expires_at)
    path.write_text(
        json.dumps(
            {
                "fingerprint": cache_fingerprint(key, BASE_URL),
                "access_token": token,
                "expires_at": expires_at,
            }
        ),
        encoding="utf-8",
    )
    return token


def test_status_without_key_is_not_configured(tmp_path: Path) -> None:
    core, _, _, _ = _core(tmp_path, FakeTransport())
    status = core.status()

    assert status.state == "not_configured"
    assert status.configured is False
    assert status.key.source is None
    assert "Aucune clé API" in status.message


def test_configure_saves_key_and_returns_secret_free_status(tmp_path: Path) -> None:
    core, key_store, metadata, _ = _core(tmp_path, FakeTransport())

    outcome = core.configure(KEY_A, expires_on="2026-10-30")

    assert outcome.changed is True
    assert key_store.path.read_text(encoding="utf-8").strip() == KEY_A
    assert metadata.read()["fingerprint"] == KeyStore.fingerprint(KEY_A)
    assert metadata.read()["display_name"] == "Test Runner"
    assert outcome.status.state == "expiring_soon"
    assert outcome.status.configured is True
    assert outcome.status.key.source == "file"
    assert outcome.status.key.hint == "••••" + KEY_A[-4:]
    assert outcome.status.display_name == "Test Runner"
    assert outcome.status.token_scopes == ["CONNECT_READ", "PERSONAL_API_WELLNESS_READ"]
    assert outcome.status.rotation.source == "declared"
    assert KEY_A not in outcome.status.model_dump_json()


def test_configure_is_idempotent(tmp_path: Path) -> None:
    metadata = InMemoryMetadataStore()
    core, key_store, _, _ = _core(tmp_path, FakeTransport(), metadata=metadata)

    first = core.configure(KEY_A)
    saved_at = metadata.read()["saved_at"]
    second = core.configure(KEY_A)

    assert first.changed is True
    assert second.changed is False
    assert metadata.read()["saved_at"] == saved_at
    assert key_store.path.read_text(encoding="utf-8").strip() == KEY_A


def test_configure_rejects_invalid_key_without_replacing_current_key(tmp_path: Path) -> None:
    transport = FakeTransport()
    core, key_store, _, _ = _core(tmp_path, transport)
    core.configure(KEY_A)
    old_content = key_store.path.read_text(encoding="utf-8")

    transport.error = HttpError(
        status_code=401,
        method="POST",
        url=f"{BASE_URL}/personalapitoken-service/...",
        response_text="",
    )

    with pytest.raises(KeyValidationError):
        core.configure(KEY_B)

    assert key_store.path.read_text(encoding="utf-8") == old_content


def test_configure_refuses_to_override_environment_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TEST_GARMIN_KEY", KEY_A)
    core, _, _, _ = _core(tmp_path, FakeTransport())

    with pytest.raises(EnvKeyConflictError):
        core.configure(KEY_B)
    with pytest.raises(EnvKeyConflictError):
        core.remove()


def test_verify_invalid_key_marks_expired(tmp_path: Path) -> None:
    transport = FakeTransport()
    core, _, metadata, _ = _core(tmp_path, transport)
    core.configure(KEY_A)

    transport.error = HttpError(
        status_code=403,
        method="POST",
        url=f"{BASE_URL}/personalapitoken-service/...",
        response_text="",
    )
    status = core.verify()

    assert status.state == "expired"
    assert "refusée" in status.message
    assert metadata.read()["last_error_kind"] == "invalid"


def test_verify_unreachable_marks_error(tmp_path: Path) -> None:
    transport = FakeTransport()
    core, _, metadata, _ = _core(tmp_path, transport)
    core.configure(KEY_A)

    transport.error = OSError("network down")
    status = core.verify()

    assert status.state == "error"
    assert "Impossible de joindre Garmin" in status.message
    assert metadata.read()["last_error_kind"] == "unreachable"


def test_rotation_is_observed_when_token_is_shorter_than_24h(tmp_path: Path) -> None:
    issued = FIXED_NOW.timestamp()
    transport = FakeTransport(issued_at=issued, expires_at=issued + 12 * 60 * 60)
    core, _, metadata, _ = _core(tmp_path, transport)

    outcome = core.configure(KEY_A)

    assert outcome.status.rotation.source == "observed"
    assert outcome.status.rotation.days_remaining in {0, 1}
    assert outcome.status.rotation.warning is True
    assert "observed_expires_at" in metadata.read()


def test_declared_rotation_can_be_updated_and_cleared(tmp_path: Path) -> None:
    core, _, _, _ = _core(tmp_path, FakeTransport())
    core.configure(KEY_A)

    updated = core.update_expiration("2026-12-01")
    assert updated.rotation.source == "declared"
    assert updated.rotation.expires_on == "2026-12-01"

    cleared = core.update_expiration(None)
    assert cleared.rotation.source == "unknown"
    assert cleared.rotation.expires_on is None


def test_remove_deletes_key_token_cache_and_metadata(tmp_path: Path) -> None:
    core, key_store, metadata, cache_path = _core(tmp_path, FakeTransport())
    core.configure(KEY_A)
    token = _write_cache(cache_path, KEY_A, FIXED_NOW.timestamp() + 3600)

    assert core.status().token_present is True

    status = core.remove()

    assert status.state == "not_configured"
    assert not key_store.path.exists()
    assert not cache_path.exists()
    assert metadata.read() == {}
    assert token not in status.model_dump_json()


def test_updating_the_key_removes_the_old_token_cache(tmp_path: Path) -> None:
    core, key_store, _, cache_path = _core(tmp_path, FakeTransport())
    core.configure(KEY_A)
    _write_cache(cache_path, KEY_A, FIXED_NOW.timestamp() + 3600)

    outcome = core.configure(KEY_B)

    assert outcome.changed is True
    assert key_store.path.read_text(encoding="utf-8").strip() == KEY_B
    assert not cache_path.exists()
    assert core.status().token_present is False


def test_cache_from_another_key_is_ignored(tmp_path: Path) -> None:
    core, _, _, cache_path = _core(tmp_path, FakeTransport())
    _write_cache(cache_path, KEY_A, FIXED_NOW.timestamp() + 3600)
    core.configure(KEY_B)

    status = core.status()

    assert status.token_present is False
    assert status.token_valid is False


def test_expired_cached_token_is_not_reported_valid(tmp_path: Path) -> None:
    core, _, _, cache_path = _core(tmp_path, FakeTransport())
    core.configure(KEY_B)
    _write_cache(cache_path, KEY_B, FIXED_NOW.timestamp() - 10)

    status = core.status()

    assert status.token_present is True
    assert status.token_valid is False
    # The key was verified successfully, so it is still usable; the next call
    # will exchange a new token.
    assert status.state == "valid"


def test_key_store_rejects_whitespace_and_empty_values(tmp_path: Path) -> None:
    with pytest.raises(KeyFormatError):
        KeyStore.validate("")
    with pytest.raises(KeyFormatError):
        KeyStore.validate("GCDC_abc def")
    with pytest.raises(KeyFormatError):
        KeyStore.validate("short")
    with pytest.raises(KeyFormatError):
        KeyStore.validate("GCDC_" + "a" * 20 + "\x00")


def test_status_never_contains_the_token(tmp_path: Path) -> None:
    core, _, _, cache_path = _core(tmp_path, FakeTransport())
    core.configure(KEY_A)
    token = _write_cache(cache_path, KEY_A, FIXED_NOW.timestamp() + 3600)

    payload = core.status().model_dump_json()

    assert token not in payload
    assert KEY_A not in payload
    assert "access_token" not in payload


def test_key_store_persists_latest_value_across_instances(tmp_path: Path) -> None:
    path = tmp_path / "api-key"
    first = KeyStore(path, env_var="TEST_GARMIN_KEY")
    first.save(KEY_A)

    reopened = KeyStore(path, env_var="TEST_GARMIN_KEY")
    stored = reopened.load()
    assert stored is not None
    assert stored.value == KEY_A

    first.save(KEY_B)
    latest = KeyStore(path, env_var="TEST_GARMIN_KEY").load()
    assert latest is not None
    assert latest.value == KEY_B


def test_status_after_restart_reads_persisted_key(tmp_path: Path) -> None:
    core, _, _, cache_path = _core(tmp_path, FakeTransport())
    core.configure(KEY_A)

    restarted = GarminAuthCore(
        key_store=KeyStore(tmp_path / "api-key", env_var="TEST_GARMIN_KEY"),
        transport=FakeTransport(),
        metadata=InMemoryMetadataStore(),
        token_cache_path=cache_path,
        base_url=BASE_URL,
        rotation_warning_days=7,
        now=lambda: FIXED_NOW,
    )
    status = restarted.status()

    assert status.configured is True
    assert status.key.hint == "••••" + KEY_A[-4:]
