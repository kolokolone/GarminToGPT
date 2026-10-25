"""Storage for the Garmin Personal API key.

The default file is the one Garmin's own client reads, so the backend, the MCP
server, and any other tool using the official client share the same key.

The key is never logged and never returned by the status API. Writes are
atomic and owner-only where the platform supports it.
"""

from __future__ import annotations

import contextlib
import os
import re
import tempfile
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Literal

from app.garmin_auth.errors import KeyFormatError
from app.garmin_auth.token_cache import default_api_key_file

_KEY_PATTERN = re.compile(r"\S{16,4096}")


@dataclass(frozen=True)
class StoredKey:
    value: str = field(repr=False)
    source: Literal["file", "env"]
    path: Path


class KeyStore:
    def __init__(
        self,
        path: str | Path | None = None,
        *,
        env_var: str = "GARMIN_PERSONAL_API_KEY",
    ) -> None:
        self.path = Path(path).expanduser() if path is not None else default_api_key_file()
        self.env_var = env_var

    def load(self) -> StoredKey | None:
        """Return the key with the same precedence as Garmin's official client.

        ``GARMIN_PERSONAL_API_KEY`` wins over the file. An empty environment
        variable is treated as absent rather than as a valid key.
        """
        env_value = os.environ.get(self.env_var)
        if env_value is not None and env_value.strip():
            return StoredKey(env_value.strip(), "env", self.path)

        try:
            value = self.path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return None
        if not value:
            return None
        return StoredKey(value, "file", self.path)

    @staticmethod
    def validate(value: str) -> str:
        if not isinstance(value, str):
            raise KeyFormatError("La clé API doit être une chaîne de caractères.")
        normalized = value.strip()
        if not normalized:
            raise KeyFormatError("Colle la clé API Garmin affichée par Garmin Connect.")
        if not normalized.isprintable() or not _KEY_PATTERN.fullmatch(normalized):
            raise KeyFormatError(
                "La clé API ne doit contenir aucun espace ni caractère de contrôle "
                "et doit faire entre 16 et 4096 caractères."
            )
        return normalized

    def save(self, value: str) -> None:
        normalized = self.validate(value)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            prefix=".garmin-api-key-",
            dir=self.path.parent,
            text=True,
        )
        temporary_path = Path(temporary)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(normalized + "\n")
            self._restrict(temporary_path)
            os.replace(temporary_path, self.path)
            self._restrict(self.path)
        except BaseException:
            temporary_path.unlink(missing_ok=True)
            raise

    def delete(self) -> bool:
        try:
            self.path.unlink()
        except FileNotFoundError:
            return False
        return True

    @staticmethod
    def _restrict(path: Path) -> None:
        # Windows ACLs are inherited from the user profile; chmod is a
        # best-effort hardening there and must not break the flow.
        with contextlib.suppress(OSError):
            os.chmod(path, 0o600)

    @staticmethod
    def fingerprint(value: str) -> str:
        return sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def display_fingerprint(value: str) -> str:
        return sha256(value.encode("utf-8")).hexdigest()[:12]

    @staticmethod
    def hint(value: str) -> str:
        return f"••••{value[-4:]}" if len(value) >= 4 else "••••"
