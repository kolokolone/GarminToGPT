import json
from pathlib import Path
from typing import Any

from app.core.config import Settings


class StateStore:
    def __init__(self, settings: Settings) -> None:
        self.path: Path = settings.runtime.state_path

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def set_value(self, key: str, value: Any) -> None:
        data = self.read()
        data[key] = value
        self.write(data)
