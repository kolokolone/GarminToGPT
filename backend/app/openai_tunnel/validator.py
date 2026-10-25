"""Validate a tunnel ID and runtime key against the OpenAI control plane."""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass

from app.openai_tunnel.binary import TunnelBinaryError, TunnelBinaryManager
from app.utils.redact import redact_text


@dataclass(frozen=True)
class TunnelValidation:
    ok: bool
    message: str
    name: str | None = None
    http_status: int = 400


class TunnelClientValidator:
    def __init__(
        self,
        binary: TunnelBinaryManager,
        *,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self.binary = binary
        self._runner = runner

    def validate(self, tunnel_id: str, api_key: str) -> TunnelValidation:
        try:
            binary = self.binary.ensure()
        except TunnelBinaryError as exc:
            return TunnelValidation(ok=False, message=str(exc), http_status=502)

        env = os.environ.copy()
        env.pop("OPENAI_ADMIN_KEY", None)
        env.pop("OPENAI_API_KEY", None)
        env["CONTROL_PLANE_API_KEY"] = api_key

        try:
            result = self._runner(
                [str(binary.path), "admin", "--json", "tunnels", "get", tunnel_id],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=45,
                check=False,
                env=env,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            return TunnelValidation(
                ok=False,
                message=f"Validation OpenAI impossible: {exc}",
                http_status=502,
            )

        payload = self._json(result.stdout)
        if isinstance(payload, dict) and payload.get("error"):
            error = payload["error"]
            status = error.get("status_code") if isinstance(error, dict) else None
            code = error.get("code") if isinstance(error, dict) else None
            if status in (401, 403) or code in {"invalid_api_key", "forbidden"}:
                message = (
                    "OpenAI a refusé la runtime API key ou les permissions du tunnel "
                    f"(HTTP {status or '401/403'}). La clé doit avoir Tunnels Read + Use."
                )
            elif status == 404:
                message = (
                    "Tunnel introuvable ou inaccessible avec cette clé. Vérifie le "
                    "tunnel ID et le workspace OpenAI."
                )
            else:
                detail = error.get("message") if isinstance(error, dict) else str(error)
                message = f"Validation OpenAI refusée: {detail}"
            return TunnelValidation(ok=False, message=redact_text(message)[:600], http_status=400)

        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            return TunnelValidation(
                ok=False,
                message=redact_text(
                    f"Validation OpenAI échouée (code {result.returncode})"
                    + (f": {detail[:300]}" if detail else ".")
                ),
                http_status=502,
            )

        name = None
        if isinstance(payload, dict):
            tunnel = payload.get("tunnel")
            if isinstance(tunnel, dict) and isinstance(tunnel.get("name"), str):
                name = tunnel["name"]
            elif isinstance(payload.get("name"), str):
                name = payload["name"]
        return TunnelValidation(ok=True, message="Tunnel OpenAI validé.", name=name)

    @staticmethod
    def _json(text: str) -> dict | None:
        try:
            value = json.loads(text)
        except (TypeError, ValueError):
            return None
        return value if isinstance(value, dict) else None
