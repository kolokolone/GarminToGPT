"""Pinned tunnel-client binary download and resolution.

The app downloads the official OpenAI release only when the binary is not
already available in the configured command, PATH, or ``runtime/bin``. The ZIP
is verified against the published SHA-256 before a single executable is
extracted; the bundled ``cloudflared`` companion is deliberately ignored.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal

from app.core.config import Settings

# Full client assets published in openai/tunnel-client v0.0.18.
# The SHA-256 values come from the release's expanded assets listing.
RELEASES: dict[str, dict[str, dict[str, str]]] = {
    "0.0.18": {
        "windows-amd64": {
            "url": (
                "https://github.com/openai/tunnel-client/releases/download/"
                "v0.0.18/tunnel-client-v0.0.18-windows-amd64.zip"
            ),
            "sha256": "8d0da1ce79532d44ccc5ed5d8bd36cdfffba37dfd287c602d69635c8bb5db2b2",
        },
        "windows-arm64": {
            "url": (
                "https://github.com/openai/tunnel-client/releases/download/"
                "v0.0.18/tunnel-client-v0.0.18-windows-arm64.zip"
            ),
            "sha256": "b73237513d50bf7acbeb960d80d9cbb6513879292f80ec1bd04b886fac1fe1c8",
        },
        "linux-amd64": {
            "url": (
                "https://github.com/openai/tunnel-client/releases/download/"
                "v0.0.18/tunnel-client-v0.0.18-linux-amd64.zip"
            ),
            "sha256": "3c82307316acd93c88a384b62af1d81d3f4cb0efa975f9c0bfaef922866a04c4",
        },
        "linux-arm64": {
            "url": (
                "https://github.com/openai/tunnel-client/releases/download/"
                "v0.0.18/tunnel-client-v0.0.18-linux-arm64.zip"
            ),
            "sha256": "a5f3d70efc75f5e66ab5c67c44d272aa80b2736f93f875f165140517750ec035",
        },
    }
}

_VERSION_PATTERN = re.compile(r"\b(\d+\.\d+\.\d+)\b")


class TunnelBinaryError(RuntimeError):
    pass


@dataclass(frozen=True)
class TunnelBinary:
    path: Path
    version: str | None
    installed: bool
    source: Literal["path", "runtime"]


class TunnelBinaryManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.runtime_bin = settings.runtime.runtime_path / "bin"
        self._lock = threading.Lock()
        self._version_cache: dict[tuple[str, int], str | None] = {}

    @property
    def auto_path(self) -> Path:
        name = "tunnel-client.exe" if sys.platform == "win32" else "tunnel-client"
        return self.runtime_bin / name

    def resolve(self) -> Path | None:
        command = self.settings.tunnel.command
        configured = Path(command).expanduser()
        if (
            configured.is_absolute()
            or "/" in command
            or "\\" in command
        ) and configured.exists():
            return configured
        located = shutil.which(command)
        if located:
            return Path(located)
        if self.auto_path.exists():
            return self.auto_path
        return None

    def status(self) -> TunnelBinary:
        path = self.resolve() or self.auto_path
        installed = path.exists()
        return TunnelBinary(
            path=path,
            version=self._version(path) if installed else None,
            installed=installed,
            source="path" if installed and path != self.auto_path else "runtime",
        )

    def ensure(self) -> TunnelBinary:
        with self._lock:
            current = self.status()
            if current.installed:
                return current

            version = self.settings.tunnel.binary_version
            platform_key = self.platform_key()
            release = RELEASES.get(version, {}).get(platform_key)
            if release is None:
                raise TunnelBinaryError(
                    f"Aucun binaire tunnel-client {version} pour {platform_key}. "
                    "Installe-le manuellement depuis la page Platform Tunnels."
                )

            self.runtime_bin.mkdir(parents=True, exist_ok=True)
            archive = self.runtime_bin / f"tunnel-client-{version}-{platform_key}.zip"
            try:
                self._download(release["url"], archive, release["sha256"])
                self._extract(archive)
            finally:
                archive.unlink(missing_ok=True)

            downloaded = self.status()
            if not downloaded.installed:
                raise TunnelBinaryError(
                    "Le binaire tunnel-client a été téléchargé mais n'est pas exécutable."
                )
            return downloaded

    @staticmethod
    def platform_key() -> str:
        if sys.platform == "win32":
            system = "windows"
        elif sys.platform.startswith("linux"):
            system = "linux"
        else:
            system = sys.platform
        machine = platform.machine().lower()
        arch = {
            "x86_64": "amd64",
            "amd64": "amd64",
            "aarch64": "arm64",
            "arm64": "arm64",
        }.get(machine, machine)
        return f"{system}-{arch}"

    def _download(self, url: str, destination: Path, expected_sha256: str) -> None:
        temporary = destination.with_suffix(destination.suffix + ".part")
        digest = hashlib.sha256()
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "GarminToGPT", "Accept": "application/octet-stream"},
        )
        try:
            with (
                urllib.request.urlopen(request, timeout=180) as response,
                temporary.open("wb") as handle,
            ):
                while chunk := response.read(1024 * 1024):
                    digest.update(chunk)
                    handle.write(chunk)
            if digest.hexdigest().lower() != expected_sha256.lower():
                raise TunnelBinaryError(
                    "La somme SHA-256 du binaire tunnel-client ne correspond pas "
                    "à la release officielle. Téléchargement refusé."
                )
            os.replace(temporary, destination)
        except Exception as exc:
            temporary.unlink(missing_ok=True)
            if isinstance(exc, TunnelBinaryError):
                raise
            raise TunnelBinaryError(
                f"Téléchargement de tunnel-client impossible: {exc}. "
                "Installe-le manuellement depuis la page Platform Tunnels."
            ) from exc

    def _extract(self, archive: Path) -> None:
        self.auto_path.parent.mkdir(parents=True, exist_ok=True)
        member_name = "tunnel-client.exe" if sys.platform == "win32" else "tunnel-client"
        with zipfile.ZipFile(archive) as bundle:
            members = [
                name
                for name in bundle.namelist()
                if PurePosixPath(name).name == member_name
            ]
            if not members:
                raise TunnelBinaryError(
                    f"L'archive tunnel-client ne contient pas {member_name}."
                )
            payload = bundle.read(members[0])

        temporary = self.auto_path.with_suffix(self.auto_path.suffix + ".part")
        try:
            temporary.write_bytes(payload)
            with contextlib.suppress(OSError):
                os.chmod(temporary, 0o755)
            os.replace(temporary, self.auto_path)
        finally:
            temporary.unlink(missing_ok=True)

    def _version(self, path: Path) -> str | None:
        try:
            stat = path.stat()
        except OSError:
            return None
        key = (str(path), stat.st_mtime_ns)
        if key in self._version_cache:
            return self._version_cache[key]
        try:
            result = subprocess.run(
                [str(path), "--version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            self._version_cache[key] = None
            return None
        match = _VERSION_PATTERN.search(result.stdout or result.stderr)
        version = match.group(1) if match else None
        self._version_cache[key] = version
        return version
