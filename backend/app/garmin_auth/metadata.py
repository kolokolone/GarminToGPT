"""Small metadata contract used by the auth core.

The production implementation stores this in ``runtime/state.json``. Tests and
other applications can provide any mapping-backed store.
"""

from __future__ import annotations

from typing import Any, Protocol


class MetadataStore(Protocol):
    def read(self) -> dict[str, Any]: ...

    def write(self, data: dict[str, Any]) -> None: ...


class InMemoryMetadataStore:
    def __init__(self, initial: dict[str, Any] | None = None) -> None:
        self._data: dict[str, Any] = dict(initial or {})

    def read(self) -> dict[str, Any]:
        return dict(self._data)

    def write(self, data: dict[str, Any]) -> None:
        self._data = dict(data)
