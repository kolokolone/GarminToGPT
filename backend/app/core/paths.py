from functools import lru_cache
from pathlib import Path


@lru_cache
def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def resolve_project_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = project_root() / path
    return path.resolve()
