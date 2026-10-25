"""Storage for the OpenAI tunnel ID and runtime API key.

The tunnel ID is not secret; the runtime API key is. Both are stored outside the
repository (``~/.config/garmintogpt`` by default), and the key file is written
atomically with owner-only permissions where the platform supports it.

``CONTROL_PLANE_TUNNEL_ID`` and ``CONTROL_PLANE_API_KEY`` (or
``OPENAI_API_KEY``) take precedence over the files, matching tunnel-client.
"""

from __future__ import annotations

import contextlib
import hmac
import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

_TUNNEL_ID = re.compile(r"^tunnel_(?:[a-z0-9]{4}_)?[a-z0-9]{32}$")
_API_KEY = re.compile(r"\S{8,512}")

TunnelSource = Literal["env", "file", "mixed", "none"]


class TunnelConfigError(RuntimeError):
    http_status = 400


class TunnelValidationError(TunnelConfigError):
    def __init__(self, message: str, *, http_status: int = 400) -> None:
        super().__init__(message)
        self.http_status = http_status


class TunnelConfigFormatError(TunnelConfigError):
    pass


class TunnelEnvConflictError(TunnelConfigError):
    http_status = 409


@dataclass(frozen=True)
class StoredTunnelConfig:
    tunnel_id: str | None
    api_key: str | None = field(repr=False)
    tunnel_id_source: Literal["env", "file"] | None = None
    key_source: Literal["env", "file"] | None = None

    @property
    def configured(self) -> bool:
        return bool(self.tunnel_id and self.api_key)

    @property
    def editable(self) -> bool:
        return self.tunnel_id_source != "env" and self.key_source != "env"

    @property
    def source(self) -> TunnelSource:
        sources = {source for source in (self.tunnel_id_source, self.key_source) if source}
        if not sources:
            return "none"
        if len(sources) == 1:
            return sources.pop()  # type: ignore[return-value]
        return "mixed"


class OpenAITunnelConfigStore:
    def __init__(
        self,
        *,
        key_file: str | Path | None = None,
        config_file: str | Path | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        base = Path.home() / ".config" / "garmintogpt"
        self.key_file = Path(
            key_file
            or os.environ.get("GARMINTOGPT_TUNNEL_KEY_FILE")
            or base / "openai-tunnel-key"
        ).expanduser()
        self.config_file = Path(
            config_file
            or os.environ.get("GARMINTOGPT_TUNNEL_CONFIG_FILE")
            or base / "openai-tunnel.json"
        ).expanduser()
        self.env = os.environ if env is None else env

    def load(self) -> StoredTunnelConfig:
        env_tunnel = (self.env.get("CONTROL_PLANE_TUNNEL_ID") or "").strip()
        env_key = (
            self.env.get("CONTROL_PLANE_API_KEY")
            or self.env.get("OPENAI_API_KEY")
            or ""
        ).strip()

        file_tunnel, file_key = self._read_files()

        tunnel_id = env_tunnel or file_tunnel
        api_key = env_key or file_key
        tunnel_source = "env" if env_tunnel else ("file" if file_tunnel else None)
        key_source = "env" if env_key else ("file" if file_key else None)

        return StoredTunnelConfig(
            tunnel_id=tunnel_id or None,
            api_key=api_key or None,
            tunnel_id_source=tunnel_source,  # type: ignore[arg-type]
            key_source=key_source,  # type: ignore[arg-type]
        )

    def save(self, tunnel_id: str, api_key: str) -> StoredTunnelConfig:
        tunnel_id = self.validate_tunnel_id(tunnel_id)
        api_key = self.validate_api_key(api_key)
        current = self.load()

        if current.tunnel_id_source == "env" and current.tunnel_id != tunnel_id:
            raise TunnelEnvConflictError(
                "CONTROL_PLANE_TUNNEL_ID est défini dans l'environnement et prioritaire. "
                "Retire-le pour gérer le tunnel depuis cette page."
            )
        if current.key_source == "env" and not hmac.compare_digest(
            current.api_key or "", api_key
        ):
            raise TunnelEnvConflictError(
                "CONTROL_PLANE_API_KEY est défini dans l'environnement et prioritaire. "
                "Retire-le pour gérer la clé depuis cette page."
            )

        self._write(self.key_file, api_key)
        self._write(
            self.config_file,
            json.dumps({"tunnel_id": tunnel_id}, indent=2) + "\n",
        )
        return self.load()

    def clear(self) -> bool:
        deleted = False
        for path in (self.key_file, self.config_file):
            try:
                path.unlink()
            except FileNotFoundError:
                continue
            deleted = True
        return deleted

    @staticmethod
    def validate_tunnel_id(value: str) -> str:
        normalized = (value or "").strip()
        if not _TUNNEL_ID.fullmatch(normalized):
            raise TunnelConfigFormatError(
                "Le tunnel ID doit ressembler à tunnel_<32 caractères minuscules> "
                "(ou tunnel_<namespace de 4>_<32 caractères>)."
            )
        return normalized

    @staticmethod
    def validate_api_key(value: str) -> str:
        normalized = (value or "").strip()
        if not normalized or not normalized.isprintable() or not _API_KEY.fullmatch(normalized):
            raise TunnelConfigFormatError(
                "La runtime API key OpenAI doit être une chaîne non vide, "
                "sans espace ni caractère de contrôle."
            )
        return normalized

    @staticmethod
    def hint(value: str | None) -> str | None:
        if not value:
            return None
        return f"••••{value[-4:]}" if len(value) >= 4 else "••••"

    @staticmethod
    def _write(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(
            prefix=f".{path.name}-",
            dir=path.parent,
            text=True,
        )
        temporary_path = Path(temporary)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(content)
            with contextlib.suppress(OSError):
                os.chmod(temporary_path, 0o600)
            os.replace(temporary_path, path)
            with contextlib.suppress(OSError):
                os.chmod(path, 0o600)
        except BaseException:
            temporary_path.unlink(missing_ok=True)
            raise

    def _read_files(self) -> tuple[str | None, str | None]:
        tunnel_id, api_key = None, None
        try:
            payload = json.loads(self.config_file.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and isinstance(payload.get("tunnel_id"), str):
                tunnel_id = payload["tunnel_id"].strip() or None
        except (FileNotFoundError, OSError, ValueError, TypeError):
            pass
        with contextlib.suppress(FileNotFoundError, OSError):
            api_key = self.key_file.read_text(encoding="utf-8").strip() or None
        return tunnel_id, api_key
